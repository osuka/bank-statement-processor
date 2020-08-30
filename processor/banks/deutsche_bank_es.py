"""
Parsing for the documents received from the entity Deutsche Bank ES
"""

import re
from datetime import datetime

from parsing.common import find_after, find_date_yyyymmdd, find_starting_with
from parsing.metadata import DocumentMetadata, unclassified, Classification, Bank


def find_date_as_data(lines):  # noqa: E0602
    """finds the first string that matches the pattern "DATA \n02.01.18"
    and returns a date object with the given date
    """
    for line in lines:
        if line.startswith("DATA \n"):
            try:
                date = datetime.strptime(line.split("\n")[1], "%d.%m.%y")
                return date
            except ValueError:
                pass
    return None


def find_date_as_fecha(lines):  # noqa: E0602
    """finds the first string that matches the pattern "FECHA\n02.01.2018"
    and returns a date object with the given date
    """
    for line in lines:
        if line.startswith("FECHA\n"):
            try:
                date = datetime.strptime(line.split("\n")[1], "%d.%m.%Y")
                return date
            except ValueError:
                pass
    return None


def find_date_as_periode(lines):  # noqa: E0602
    """Finds the first string like "Període de l'1 al 31 Desembre de 2017"
    and returns a date object with the given end date parsed
    """
    translate = {
        "Gener": 1,
        "Febrer": 2,
        "Març": 3,
        "Abril": 4,
        "Maig": 5,
        "Juny": 6,
        "Juliol": 7,
        "Agost": 8,
        "Setembre": 9,
        "Octubre": 10,
        "Novembre": 11,
        "Desembre": 12,
    }

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
                month = translate[month_str]
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

        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.DEBIT,
            entity=emisor,
            extra_info=concepto,
        )

    def perfil_inversor(self, lines):
        """carta informant de perfil inversor de productes contractats"""
        perfil_de_risc = find_starting_with(lines, "PERFIL DE RISC")
        codi = find_after(lines, "DWS AHORRO F.I.")
        date = find_date_yyyymmdd(lines)
        if not perfil_de_risc or not date or not codi:
            return unclassified()

        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.FUND,
            entity=codi,
            extra_info="perfil",
        )

    def estat_inversio(self, lines):
        """informe de inversio"""
        date = find_date_as_data(lines)
        perfil_de_risc = find_starting_with(lines, "ESTAT DE POSICIÓ DE FONS")
        codi = find_after(lines, "DWS AHORRO FI ISIN:")
        date = find_date_yyyymmdd(lines)
        if not perfil_de_risc or not date or not codi:
            return unclassified()

        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.FUND,
            entity=codi,
            extra_info="posicion",
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

        date = find_date_as_fecha(lines)
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=date,
            bank=Bank.DEUTSCHE_BANK,
            classification=Classification.MOVEMENTS,
            entity="cuenta_nomina",
            extra_info="",
        )
