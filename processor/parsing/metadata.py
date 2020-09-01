"""
Classification of financial documents
"""
from datetime import datetime
from typing import List
from enum import Enum
from dataclasses import dataclass
from parsing.common import contains_all, find_containing


class Bank(Enum):
    """ Known bank providers """

    UNKNOWN = "UNKNOWN"
    DEUTSCHE_BANK = "db"
    SANTANDER_UK = "santanderuk"
    MONZON = "monzo"
    FIRST_DIRECT = "firstdirect"
    OPENBANK = "openbank"
    CITIBANK_UK = "citibank"


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
