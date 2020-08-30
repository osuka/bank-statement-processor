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


class Classification(Enum):
    """ Known document subjects """

    UNKNOWN = "UNKNOWN"
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
    classification: Classification
    entity: str  # name of entity debited, originating, etc
    extra_info: str  # eg policy id, notes, etc that should go on the name
    period_end_date: datetime = None


def unclassified(
    lines: List[str] = None,  # pylint: disable=unused-argument
) -> DocumentMetadata:
    """When a document can't be identified it will need manual revision - we
    store them under the same bogus date"""

    return DocumentMetadata(
        period_start_date=datetime(2000, 1, 1),
        period_end_date=None,
        bank=Bank.UNKNOWN,
        classification=Classification.UNKNOWN,
        entity="",
        extra_info="",
    )
