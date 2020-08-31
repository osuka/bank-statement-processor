"""
Classification of financial documents
"""
from datetime import datetime
from typing import List
from enum import Enum
from dataclasses import dataclass


class Bank(Enum):
    """ Known bank providers """

    UNKNOWN = "UNKNOWN"
    DEUTSCHE_BANK = "db"
    SANTANDER_UK = "santanderuk"
    MONZON = "monzo"
    FIRST_DIRECT = "firstdirect"
    OPENBANK = "openbank"


class DocType(Enum):
    """ Known document subjects """

    UNKNOWN = "UNKNOWN"
    NOTE = "aviso"
    FISCAL = "fiscal"
    STATEMENT = "statement"
    RECEIPT = "recibo"
    INVESTMENT = "inversio"
    FUND = "fons"
    DEBIT = "debit"
    SUMMARY = "resumen"
    MOVEMENTS = "extracto"
    MORTGAGE = "hipoteca"
    TRANSFER = "transferencia"
    INSURANCE = "seguros"


@dataclass
class DocumentMetadata:
    """ Metadata for a document once classified """

    period_start_date: datetime
    bank: Bank
    classification: DocType
    entity: str  # name of entity debited, originating, etc
    extra_info: str  # eg policy id, notes, etc that should go on the name
    period_end_date: datetime = None
