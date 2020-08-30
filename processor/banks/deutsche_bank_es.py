"""
Parsing for the documents received from the entity Deutsche Bank ES
"""

import re
import csv
from datetime import datetime
from typing import List

from pdfminer.layout import LTPage

from parsing.common import (
    find_after,
    find_date_yyyymmdd,
    find_starting_with,
    find_containing,
)
from parsing.metadata import DocumentMetadata, unclassified, Classification, Bank

catalan_months = {
    "gener": 1,
    "febrer": 2,
    "març": 3,
    "abril": 4,
    "maig": 5,
    "juny": 6,
    "juliol": 7,
    "agost": 8,
    "setembre": 9,
    "octubre": 10,
    "novembre": 11,
    "desembre": 12,
}


def parse_date(text: str):
    """parses a string into a date, trying dd.mm.yy, dd.mm.yyyy and other combinations """
    patterns = ["%d/%m/%y", "%d/%m/%Y", "%d.%m.%y", "%d.%m.%Y"]
    text = text.split("\n")[0]
    for pattern in patterns:
        try:
            date = datetime.strptime(text, pattern)
            return date
        except ValueError:
            pass
    raise ValueError(f"not a date: {text}")


def find_date(lines):  # noqa: E0602
    """finds the first string that matches the pattern "DATA \n02.01.18"
    or "DATA,11/05/2018" or "FECHA\n11/05/2018" and returns a date object with the given date
    """
    index = 0
    for line in lines:
        if len(lines) - index > 5:
            # some documents have a series of strings separated by new lines forming a date:
            # 16     index
            # de     index+1
            # gener  index+2
            # de     index+3
            # 2018   index+4
            if lines[index + 1].strip() == "de" and lines[index + 3] == "de":
                try:
                    year = int(lines[index + 4])
                    month_str = lines[index + 2]
                    month = catalan_months[month_str.lower()]
                    day = int(lines[index])
                    date = datetime(year, month, day)
                    return date
                except ValueError:
                    pass

        if line.startswith("DATA \n") or line.startswith("FECHA\n"):
            try:
                return parse_date(line.split("\n")[1])
            except ValueError:
                pass
        elif line.startswith("DATA,") or line.startswith("DATA\n"):
            try:
                return parse_date(line[5:15])
            except ValueError:
                pass

        index += 1
    return None


def find_date_as_periode(lines):  # noqa: E0602
    """Finds the first string like "Període de l'1 al 31 Desembre de 2017"
    and returns a date object with the given end date parsed
    """

    for line in lines:
        if line.startswith("Període de "):
            try:
                matches = re.match(
                    r".*(?P<diaStart>[\d]+) al "
                    r"(?P<diaEnd>[\d]+).*"
                    r"(?P<mes>[GFMAJSOND][a-zç]*) "
                    r"de (?P<any>[\d]+)",
                    line,
                )
                if not matches:
                    continue
                month_str = matches.group("mes")
                month = catalan_months[month_str.lower()]
                if not month:
                    raise Exception(f"Unknown month {month_str}")
                year_str = matches.group("any")
                year = int(year_str)
                if year < 1990 or year > 2100:
                    raise Exception(f"Unknown year {year_str}")
                start_str = matches.group("diaStart")
                start = int(start_str)
                if start < 1 or start > 31:
                    raise Exception(f"Unknown year {start_str}")
                end_str = matches.group("diaEnd")
                end = int(end_str)
                if end < 1 or end > 31:
                    raise Exception(f"Unknown year {end_str}")
                date = datetime.strptime(f"{year}.{month}.{end}", "%Y.%m.%d")
                return date
            except ValueError:
                pass
    return None


class DeutscheBankDocuments:
    """ Parsers for all the PDF documents from Deutsche Bank ES known """

    def process(
        self,
        file_name: str,  # pylint: disable=unused-argument
        page: LTPage,  # pylint: disable=unused-argument
        lines: List[str],
    ) -> DocumentMetadata:
        """check if the document is from this entity, classify it if so
        and return metadata, else None"""
        if find_starting_with(lines, "ADEUDO POR DOMICILIACIÓN SEPA"):
            return self.debit(lines)
        if "EXTRACTE INTEGRAT DB" in lines:
            return self.extracto_integrado(lines)
        if "DWS AHORRO F.I." in lines and find_starting_with(lines, "PERFIL DE RISC"):
            return self.perfil_inversor_detail(lines)
        if find_containing(
            lines, "Re: INFORMACIÓ SOBRE ELS PERFILS DELS SEUS PRODUCTES"
        ):
            return self.perfil_inversor_intro(lines)
        if find_starting_with(lines, "ESTAT DE POSICIÓ DE FONS D' INVERSIÓ."):
            return self.estat_inversio(lines)
        if find_starting_with(
            lines, "EXTRACTO CUENTA NOMINA BANCA ASOCIADA DB"
        ) or find_starting_with(lines, "EXTRACTO DE CUENTA CORRIENTE DB"):
            return self.extracto_cuenta(lines)
        if find_containing(
            lines, "RENOVACIÓ TIPUS D'INTERÈS DEL SEU PRÉSTEC NOMINAT EN EUR"
        ):
            return self.renovacio_interes_intro(lines)
        if find_containing(lines, "CAPITAL PENDENT\nPER CÀLCUL\nD'INTERESSOS"):
            return self.renovacio_interes_detail(lines)
        if find_containing(lines, "EXTRACTE LIQUIDACIÓ COMPTE TARGETA DE CRÈDIT"):
            return self.extract_targeta_credit(lines)
        if find_containing(lines, "CÀRREC REBUT PRÉSTEC HIPOTECARI"):
            return self.carrec_hipoteca(lines)
        if find_containing(lines, "ABONO TRANSFERENCIA SEPA"):
            return self.abono_transferencia(lines)
        if find_containing(lines, "LIQUIDACIÓ OPERACIONS DE"):
            return self.liquidacio_fons(lines)
        if find_containing(lines, "NOVES CONDICIONS DE LA CUENTA MULTIRIESGO db"):
            return self.noves_condicions_multiriesgo(lines)
        return None

    def debit(self, lines):
        """ debit charge """
        emisor = find_starting_with(lines, "EMISOR - ORDENANTE")
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
            return unclassified()

        # concept is quite long so we generate shorter aliases
        if "CIENCIES" in concepto and "CIENCIES" in emisor:
            emisor = "graells"
            concepto = "ciencies"
        elif "VANGUARDIA" in emisor:
            emisor = "f.vanguardia"
            concepto = "ciencies"
        elif "NUBIOLA" in emisor or "MERNUBE" in emisor:
            emisor = "piso"
            concepto = "borriana"
        elif "DEUTSCHE BANK" in emisor and "ZURICH" in concepto:
            emisor = "deutsche"
            concepto = "seguro zurich unknown"
        elif "ZURICH VIDA" in emisor and "300002290" in concepto:
            emisor = "zurich"
            concepto = "vida ruth"
        elif "ZURICH VIDA" in emisor and "300002289" in concepto:
            emisor = "zurich"
            concepto = "vida oscar"
        elif "AQUALOGY" in emisor:
            emisor = "agua"
            concepto = "alquiler medidor"
        elif "AIGUES DE BARCELONA" in emisor:
            emisor = "agua"
            concepto = "suministro"
        elif "AJUNTAMENT DE BARCELONA" in emisor:
            emisor = "ajuntament"
            if "IBI" in concepto:
                concepto = "ibi ciencies"
            elif "IMPOST VEHICLES" in concepto and "0005CVV" in concepto:
                concepto = "ivtm coche c3"

        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.DEBIT,
            entity=emisor,
            extra_info=concepto,
        )

    def perfil_inversor_detail(self, lines):
        """carta informant de perfil inversor de productes contractats"""
        date = find_date_yyyymmdd(lines)
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.FUND,
            entity="perfil",
            extra_info="detail",
        )

    def perfil_inversor_intro(self, lines):
        """carta informant de perfil inversor de productes contractats (portada)"""
        date = find_date(lines)

        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.FUND,
            entity="perfil",
            extra_info="intro",
        )

    def liquidacio_fons(self, lines):
        """adding to funds"""
        date = find_date(lines)

        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.FUND,
            entity="liquidacio",
            extra_info="",
        )

    def estat_inversio(self, lines):
        """informe de inversio"""
        date = find_date(lines)

        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.FUND,
            entity="posicion",
            extra_info="",
        )

    def extracto_integrado(self, lines):
        """ extracte integrat """

        date = find_date_as_periode(lines)
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.SUMMARY,
            entity="extracte",
            extra_info="",
        )

    def extracto_cuenta(self, lines):
        """ account movements for a period """

        date = find_date(lines)
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.MOVEMENTS,
            entity="cuenta",
            extra_info="",
        )

    def renovacio_interes_intro(self, lines):
        """ mortgage renewal """

        date = find_date(lines)
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.MORTGAGE,
            entity="renovacio",
            extra_info="summary",
        )

    def renovacio_interes_detail(self, lines):
        """ mortgage renewal """

        header = "DATA \nVENCIMENT\nAMORTITZACIÓ\n"
        line = find_containing(lines, header)
        date_str = line[len(header) : len(header) + 10]
        date = datetime.strptime(date_str, "%d/%m/%Y")
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.MORTGAGE,
            entity="renovacio",
            extra_info="detail",
        )

    def extract_targeta_credit(self, lines):
        """ credit card report """
        date = find_date(lines)
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.STATEMENT,
            entity="tarjeta",
            extra_info="",
        )

    def carrec_hipoteca(self, lines):
        """ mortgage payment """
        date = find_date(lines)
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.MORTGAGE,
            entity="pago",
            extra_info="",
        )

    def abono_transferencia(self, lines):
        """ incoming transfer """
        date = find_date(lines)
        index = 0
        ordenante = ""
        for line in lines:
            index += 1
            if "ORDENANTE\nNOMBRE:\nDOMICILIO:\n" in line:
                ordenante = lines[index].split("\n")[0].strip()
                break

        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.TRANSFER,
            entity="alquiler_ciencies",
            extra_info=ordenante,
        )

    def noves_condicions_multiriesgo(self, lines):
        """ insurance renewal """
        date = find_date(lines)
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.INSURANCE,
            entity="zurich",
            extra_info="multiriesgo",
        )
