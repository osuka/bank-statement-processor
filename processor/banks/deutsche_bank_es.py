"""
Parsing for the documents received from the entity Deutsche Bank ES
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List

import dateparser
from pdfminer.layout import LTPage

from parsing.common import (
    contains_all,
    find_containing,
    find_starting_with,
    parse_date_es_ca,
)
from parsing.metadata import Bank, DocType, DocumentMetadata


def find_date(lines):  # noqa: E0602
    """finds the first string that matches the pattern "DATA \n02.01.18"
    or "DATA,11/05/2018" or "FECHA\n11/05/2018" and returns a date object with the given date
    """
    index = 0
    for line in lines:
        try:
            if line.startswith("DATA\nF1./0./11/"):
                return datetime(
                    year=2010, month=12, day=13
                )  # the f'up one day and sent this, so here we are fixing it
            elif (
                line.startswith("DATA \n")
                or line.startswith("FECHA\n")
                or line.startswith("FECHA \n")
            ):
                target = line.split("\n")[1]
                # sometimes it still contains some extra stuff at the end
                # hardcode the ones we find
                matches = re.match(r"(\d{2}.\d{2}.\d{2,4}) .*", target)
                if matches:
                    target = matches.group(1)
                return parse_date_es_ca(target)
            elif line.startswith("DATA,") or line.startswith("DATA\n"):
                return parse_date_es_ca(line[5:15])
            elif line.startswith("Període de "):
                # "Període de l'1 al 31 Desembre de 2017"
                matches = re.match(r"Període de .* al (?P<date>.*)", line)
                if matches:
                    date = dateparser.parse(matches.group("date"), languages=["ca"])
                    if date:
                        return date
                raise Exception(f"Confusing date:\n\n{line}\n\n - check and fix code!")
            elif line == "Fecha:":
                return parse_date_es_ca(lines[index + 1])
            elif (
                len(lines) - index > 5
                and lines[index + 1].strip() == "de"
                and lines[index + 3] == "de"
            ):
                # some documents have a series of strings separated by new lines forming a date:
                # 16     index
                # de     index+1
                # gener  index+2
                # de     index+3
                # 2018   index+4
                date = dateparser.parse(
                    " ".join(lines[index : index + 5]), languages=["ca", "es"]
                )
                if date:
                    return date
                raise Exception(f"Confusing date:\n\n{line}\n\n - check and fix code!")
            elif len(lines) - index > 3 and re.match(
                r"\d{1,2} \w+ \d{2,4}",
                f"{lines[index]} {lines[index+1]} {lines[index+2]}",
            ):
                # 16     index
                # gener  index+1
                # 2018   index+2
                date = dateparser.parse(
                    " ".join(lines[index : index + 3]), languages=["ca", "es"]
                )
                if date:
                    return date
                raise Exception(f"Confusing date:\n\n{line}\n\n - check and fix code!")
            elif re.match(
                r"^(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre) de \d{2,4}\n",
                line,
            ):
                date = parse_date_es_ca(line.split("\n")[0])
                if date:
                    return date
                raise Exception(f"Confusing date:\n\n{line}\n\n - check and fix code!")
            elif " de " in line:
                date = dateparser.parse(line, languages=["es", "ca"])
                if date:
                    return date

        except ValueError:
            pass

        index += 1
    return None


@dataclass
class Adjustment:
    """ Tweaks the final metadata to make it more manageable as file names """

    entity: str = None
    extra_info: str = None
    new_entity: str = None
    new_extra_info: str = None

    def adjust(self, metadata: DocumentMetadata):
        """ modifies in-place the metadata according to the rules in this adjustment """
        if self.entity and contains_all(metadata.entity, self.entity):
            if not self.extra_info or (
                self.extra_info and contains_all(metadata.extra_info, self.extra_info)
            ):
                if self.new_extra_info:
                    metadata.extra_info = self.new_extra_info
                if self.new_entity:
                    metadata.entity = self.new_entity
                return True
        return False


def adjust_names(metadata: DocumentMetadata):
    """issuer and concept can be rather long so we generate shorter aliases
    purely by convention"""

    adjustments = [
        Adjustment("CIENCIES", "CIENCIES", "graells", "ciencies"),
        Adjustment("VANGUARDIA", None, "f.vanguardia", "ciencies"),
        Adjustment("NUBIOLA", None, "piso", "borriana"),
        Adjustment("MERNUBE", None, "piso", "borriana"),
        Adjustment("DEUTSCHE BANK", "ZURICH", "deutsche", "seguro zurich unknown"),
        Adjustment("ZURICH VIDA", "300002290", "zurich", "vida 300002290"),
        Adjustment("ZURICH VIDA", "300002289", "zurich", "vida 300002289"),
        Adjustment("AQUALOGY", None, "agua", "contador"),
        Adjustment("AIGUES DE BARCELONA", None, "agua", "suministro"),
        Adjustment("AJUNTAMENT DE BARCELONA", "IBI", "ajuntament", "ibi ciencies"),
        Adjustment(
            "AJUNTAMENT DE BARCELONA",
            ["IMPOST VEHICLES", "0005CVV"],
            "ajuntament",
            "ivtm coche c3",
        ),
        Adjustment("SPORT I RELAX S.L.", None, "gym", "niña"),
    ]

    for adjustment in adjustments:
        if adjustment.adjust(metadata):
            return


@dataclass
class Filing:
    """Filing actions. Give a condition it sets class, entity and info to set values
    must_contain:
      a string: applies if the string is contained in any line in the document, in full, case sensitive
      a list: applies if all conditions in list are met, see below
        element in list is string: appies if there is one line that contains the string
        element in list is a list of strings: applies if there is a line that contains all the strings
                                              in the sublist, in full, case sensitive, order irrelevant
    """

    must_contain: List[str]
    classification: DocType
    entity: str = ""
    extra_info: str = ""

    def applies(self, lines):
        """ checks if the conditions for this filing action apply """
        if not self.must_contain:
            return False

        if isinstance(self.must_contain, list):
            # all conditions on the list must pass
            for condition in self.must_contain:
                # find containing accepts condition=str and condition=List[str]
                if not find_containing(lines, condition):
                    return False
            return True

        # a simple string check
        return find_containing(lines, self.must_contain)


class DeutscheBankDocuments:
    """ Parsers for all the PDF documents from Deutsche Bank ES known """

    simple_mappings = [
        Filing(
            ["RECLAMACIÓN ACUSE DE RECIBO CONTRATO", "CONTRATO FONDOS"],
            DocType.NOTE,
            "acuse recibo",
            "suscripcion",
        ),
        Filing(
            [
                "Li recordem que amb el Servei Credit Express db pot traspassar el saldo",
                "A partir del",
                "s’aplicarà una comissió del",
            ],
            DocType.NOTE,
            "cambio",
            "comisiones",
        ),
        Filing(
            [
                "de mediació d’assegurances i reassegurances\nprivades",
                "Deutsche Bank, Broker Correduría",
            ],
            DocType.NOTE,
            "cambio",
            "proveedor seguro",
        ),
        Filing(
            ["SISTEMA DE PREVISION db", "SEGURO DE VIDA db (CONDICIONES PARTICULARES"],
            DocType.INSURANCE,
            "deutsche",
            "seguro vida",
        ),
        Filing(
            ["RECAUDACIÓN EJECUTIVA", "DEUDOR\n"],
            DocType.NOTE,
            "recaudacion ejecutiva",
            "multa",
        ),
        Filing(
            ["RESUMEN ANUAL CUENTA NOMINA DB"],
            DocType.FISCAL,
            "cuenta",
            "resum anual",
        ),
        Filing(
            ["RESUMEN ANUAL CUENTA NOMINA BANCA ASOCIADA DB"],
            DocType.FISCAL,
            "cuenta",
            "resum anual",
        ),
        Filing(
            [
                "Estimada Sra.",
                "Nos ponemos en contacto con Usted para informarle de la siguiente modificación",
                "de la condición general 35",
            ],
            DocType.NOTE,
            "cambio",
            "comisiones",
        ),
        Filing(
            [
                "Ens adrecem a vostè per comunicar−li una modificació als seu/s contracte/s",
                "de targeta de crèdit",
            ],
            DocType.NOTE,
            "cambio",
            "comisiones",
        ),
        Filing(
            [
                "Ens adrecem a vostè per comunicar−li les modificacions que afecten el seu",
                "contracte de targeta de crèdit",
            ],
            DocType.NOTE,
            "cambio",
            "comisiones",
        ),
        Filing(
            ["EXTRACTO ANUAL INTEGRADO DE COMISIONES Y GASTOS"],
            DocType.FUND,
            "resum anual",
            "comisiones",
        ),
        Filing(
            ["RESUM ANUAL PRÉSTEC HIPOTECARI"],
            DocType.FISCAL,
            "hipoteca",
            "resum anual",
        ),
        Filing(
            ["LIQUIDACIÓN INTERESES CUENTA A LA VISTA"],
            DocType.STATEMENT,
            "liquidacio",
            "interes",
        ),
        Filing(
            ["LIQUIDACIÓN INTERESES CUENTA NOMINA BANCA ASOCIADA DB"],
            DocType.STATEMENT,
            "liquidacio",
            "interes",
        ),
        Filing(
            ["DETALL DE REEMBORSAMENTS DE FONS D'INVERSIÓ"],
            DocType.FISCAL,
            "fons",
            "resum anual detail",
        ),
        Filing(
            ["DETALL DE REEMBORSAMENTS DE FONS D’INVERSIÓ"],
            DocType.FISCAL,
            "fons",
            "resum anual detail",
        ),
        Filing(
            ["RESUM ANUAL A EFECTES DEL PATRIMONI", "FONS D'INVERSIÓ"],
            DocType.FISCAL,
            "fons",
            "resum anual",
        ),
        Filing(
            ["RESUM ANUAL A EFECTES DEL PATRIMONI: FONS D’INVERSIÓ"],
            DocType.FISCAL,
            "fons",
            "resum anual",
        ),
        Filing(["EXTRACTE INTEGRAT DB"], DocType.SUMMARY, "extracte"),
        Filing(["AVÍS D´ENTREGA DE LA SEVA TARGETA"], DocType.NOTE, "envio tarjeta"),
        Filing(["AVÍS DE RECOLLIDA DE TARGETA"], DocType.NOTE, "envio tarjeta"),
        Filing(
            ["Re: INFORMACIÓ SOBRE ELS PERFILS DELS SEUS PRODUCTES"],
            DocType.FUND,
            "perfil",
            "intro",
        ),
        Filing(["ESTAT DE POSICIÓ DE FONS D' INVERSIÓ"], DocType.FUND, "posicion"),
        Filing(["ESTAT DE POSICIÓ DE FONS D’ INVERSIÓ"], DocType.FUND, "posicion"),
        Filing(["EXTRACTE DEL FONS D’INVERSIÓ"], DocType.FUND, "posicion"),
        Filing(["ESTADO DE POSICIÓN DE FONDOS DE INVERSIÓN"], DocType.FUND, "posicion"),
        Filing(["FONDOS DE INVERSION - SUSCRIPCION"], DocType.FUND, "suscripcion"),
        Filing(
            ["EXTRACTO CUENTA NOMINA BANCA ASOCIADA DB"], DocType.MOVEMENTS, "cuenta"
        ),
        Filing(["EXTRACTO DE CUENTA CORRIENTE DB"], DocType.MOVEMENTS, "cuenta"),
        Filing(
            ["RENOVACIÓ TIPUS D'INTERÈS DEL SEU PRÉSTEC NOMINAT EN EUR"],
            DocType.MORTGAGE,
            "renovacio",
            "summary",
        ),
        Filing(
            ["REF.:RENOVACIÓ TIPUS D’INTERÈS DEL SEU PRÉSTEC"],
            DocType.MORTGAGE,
            "renovacio",
            "summary",
        ),
        Filing(
            ["EXTRACTE LIQUIDACIÓ COMPTE TARGETA DE CRÈDIT"],
            DocType.STATEMENT,
            "tarjeta",
        ),
        Filing(["CÀRREC REBUT PRÉSTEC HIPOTECARI"], DocType.MORTGAGE, "pago"),
        Filing(["LIQUIDACIÓ OPERACIONS DE"], DocType.FUND, "liquidacio"),
        Filing(
            ["NOVES CONDICIONS DE LA CUENTA MULTIRIESGO db"],
            DocType.INSURANCE,
            "zurich",
            "multiriesgo",
        ),
        Filing(
            ["EXTRACTO DEL SISTEMA DE PREVISION", "PRODUCTE\nSEGURO DE VIDA"],
            DocType.INSURANCE,
            "deutsche",
            "vida",
        ),
        Filing(["EXTRACTO FISCAL DB", "aro\nRut"], DocType.FISCAL, "extracto", "1"),
        Filing(["EXTRACTE FISCAL DB", "aro\nRut"], DocType.FISCAL, "extracto", "1"),
        Filing(["EXTRACTO FISCAL DB", "az\nOscar"], DocType.FISCAL, "extracto", "2"),
        Filing(["EXTRACTE FISCAL DB", "az\nOscar"], DocType.FISCAL, "extracto", "2"),
    ]

    def process(
        self,
        file_name: str,  # pylint: disable=unused-argument
        page: LTPage,  # pylint: disable=unused-argument
        lines: List[str],
    ) -> DocumentMetadata:
        """check if the document is from this entity, classify it if so
        and return metadata, else None"""

        # first try to determine if the document belongs here or not - if not, None is returned
        needs_one_of = [
            "DEUTSCHE BANK SOCIEDAD ANONIMA",
            "Deutsche Bank, Sociedad Anónima",
            "Servei Deutsche Bank Online",
            "Servicio Deutsche Bank Online",
            "Deutsche Bank Online: www.deutsche-bank.es",
            "Deutsche Bank, S.A. Española",
            "Deutsche Bank no será responsable",
            "DEUTSCHE ASSET MANAGEMENT",
            "A−80017403",
            "A−08000614",
            "BARNA-V.AUGUSTA",
            "BARNA−V.AUGUSTA",
            "OFICINA\nBARNA−V.AUGUSTA",
        ]
        passes = False
        for must_have in needs_one_of:
            if find_containing(lines, must_have):
                passes = True
                break
        if not passes:
            return None

        for filing in self.simple_mappings:
            if filing.applies(lines):
                return self.simple_document(
                    lines, filing.classification, filing.entity, filing.extra_info
                )

        # special cases
        if find_starting_with(lines, "ADEUDO POR DOMICILIACIÓN SEPA"):
            return self.debit(lines)

        if "DWS AHORRO F.I." in lines and find_starting_with(lines, "PERFIL DE RISC"):
            return self.perfil_inversor_detail(lines)

        if find_containing(
            lines, "CAPITAL PENDENT\nPER CÀLCUL\nD'INTERESSOS"
        ) or find_containing(lines, "CAPITAL PENDENT\nPER CÀLCUL\nD’INTERESSOS\n"):
            return self.renovacio_interes_detail(lines)

        if find_containing(lines, "ABONO TRANSFERENCIA SEPA"):
            return self.abono_transferencia(lines)

        if find_containing(
            lines, "Tipo de recibo\nImporte\nFecha de cargo\nEstado"
        ) and find_containing(lines, "RECIBO\n"):
            return self.recibo(lines)

        raise Exception("Documents seems to belong to bank but isn't recognised")

    def simple_document(self, lines, classification, entity="", extra_info=""):
        """ a lot of documents follow a basic pattern and we only need the first date we find """
        date = find_date(lines)
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=None,
            bank=Bank.DEUTSCHE_BANK,
            classification=classification,
            entity=entity,
            extra_info=extra_info,
        )

    def debit(self, lines):
        """ debit charge """
        emisor = find_starting_with(lines, "EMISOR - ORDENANTE")
        if not emisor:
            emisor = find_starting_with(lines, "EMISOR −ORDENANTE")
        titular = find_starting_with(lines, "TITULAR DOMICILIACIÓN")
        concepto = find_starting_with(lines, "CONCEPTO DE PAGO")
        cuenta = find_starting_with(lines, "CUENTA CLIENTE (IBAN)")
        emisor_id = find_starting_with(lines, "IDENTIFICACIÓN EMISOR")
        date_str = find_starting_with(lines, "FECHA")
        date = datetime.strptime(date_str, "%d.%m.%Y")
        if (
            not emisor
            or not titular
            or not concepto
            or not cuenta
            or not emisor_id
            or not date
        ):  # noqa: E303
            raise Exception("Error: document detected as 'debit' can't be parsed")

        metadata = DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=DocType.DEBIT,
            entity=emisor,
            extra_info=concepto,
        )
        adjust_names(metadata)
        return metadata

    def recibo(self, lines):
        """ debit charge """
        titular = None
        emisor = None
        concepto = None
        index = 0
        for line in lines:
            index += 1
            if line == "Titular de la domiciliación\nEmisor\nCuenta de cargo":
                [titular, emisor, _] = lines[index].split("\n")
            if line == "Concepto":
                concepto = lines[index]

        if not titular and not emisor and not concepto:
            raise Exception("Document detected as recibo can't be parsed")

        metadata = self.simple_document(
            lines, classification=DocType.DEBIT, entity=emisor, extra_info=concepto
        )
        adjust_names(metadata)
        return metadata

    def perfil_inversor_detail(self, lines):  # pylint: disable=unused-argument
        """carta informant de perfil inversor de productes contractats"""

        # TODO: complex case  - the only date in the document is a template date
        # - the key would be to find the corresponding PDF, this one is page 02
        # (it is also a pretty useless pdf)
        date = datetime(year=1900, month=1, day=1)
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=DocType.FUND,
            entity="perfil",
            extra_info="detail",
        )

    def renovacio_interes_detail(self, lines):
        """ mortgage renewal """

        header = "DATA \nVENCIMENT\nAMORTITZACIÓ\n"
        line = find_containing(lines, header)
        if not line:
            header = "DATA\nVENCIMENT\nAMORTITZACIÓ\n"
            line = find_containing(lines, header)
        date_str = line[len(header) : len(header) + 10]
        date = datetime.strptime(date_str, "%d/%m/%Y")
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=DocType.MORTGAGE,
            entity="renovacio",
            extra_info="detail",
        )

    def abono_transferencia(self, lines):
        """ incoming transfer """
        index = 0
        ordenante = ""
        for line in lines:
            index += 1
            if "ORDENANTE\nNOMBRE:\nDOMICILIO:\n" in line:
                ordenante = lines[index].split("\n")[0].strip()
                break

        return self.simple_document(
            lines, DocType.TRANSFER, "alquiler_ciencies", ordenante
        )
