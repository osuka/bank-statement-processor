"""
Parsing for the documents received from the entity Santander UK
"""

import re
from typing import List

from pdfminer.layout import LTPage

from parsing.common import find_containing, parse_date_gb
from parsing.metadata import Bank, DocType, DocumentMetadata, Filing

known_date_regexes = [
    # 5th Mar 2018 to 4th Apr 2018
    # 29th Oct 2013 to 2nd May 2014
    re.compile(
        r".*[0-9thndst]+ (?:Jan|Feb|Mar|May|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} to (?P<date>[0-9thndst]+ (?:Jan|Feb|Mar|May|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}).*",  # pylint: disable=line-too-long
        re.MULTILINE | re.DOTALL,
    ),
    # 5th Mar 2018to 4th Apr 2018  (some documents actually have this)
    re.compile(
        r".*(?:Jan|Feb|Mar|May|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}to (?P<date>.* (?:Jan|Feb|Mar|May|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}).*",  # pylint: disable=line-too-long
        re.MULTILINE | re.DOTALL,
    ),
    # blahblah\nFrom 01/07/2018 to 30/06/2019\nblah blabh
    re.compile(
        r".*From \d{2}/\d{2}/\d{4} to (?P<date>\d{2}/\d{2}/\d{4}).*",
        re.MULTILINE | re.DOTALL,
    ),
    # 'blahblah6 April 2018 to 5 April 2019blahblah
    # 'blahblah6 April 2018 - 5 April 2019blahblah
    re.compile(
        r".*(?:January|February|March|May|April|June|July|August|September|October|November|December) \d{4} (?:to|-) (?P<date>.* (?:January|February|March|May|April|June|July|August|September|October|November|December) \d{4}).*",  # pylint: disable=line-too-long
        re.MULTILINE | re.DOTALL,
    ),
    # Date:\n 11-02-2014
    re.compile(r"Date:\n (?P<date>\d{2}-\d{2}-\d{4})", re.MULTILINE),
]


def find_date(lines):
    """finds the first string that matches a known pattern"""
    index = 0
    for line in lines:
        try:
            for date_regex in known_date_regexes:
                matches = date_regex.match(line)
                if matches:
                    return parse_date_gb(matches.group("date"))
        except ValueError:
            pass

        index += 1
    return None


class SantanderUKBankDocuments:
    """ Parsers for all the PDF documents from Deutsche Bank ES known """

    simple_mappings = [
        Filing(
            ["BX0084", "Individual Savings"], DocType.STATEMENT, "cash isa", "summary"
        ),
        Filing(["BX0179", "Statement of Fees"], DocType.NOTE, "comisiones", "summary"),
        Filing(
            ["BX0098", "Your account summary", "Current Account earnings"],
            DocType.STATEMENT,
            "current",
        ),
        Filing(
            ["BX0098", "Your account summary", "Your current eSaver (Issue 11)"],
            DocType.STATEMENT,
            "esaver",
        ),
        Filing(
            ["BX0098", "Your account summary", "123 Current Account"],
            DocType.STATEMENT,
            "current",
        ),
        Filing(
            [
                "Telegraphic Transfer Issued",
                "Please be advised that the following telegraphic transfer has been debited",
                "CURRENCY\nEUR",
            ],
            DocType.TRANSFER,
            "outgoing",
            "europe",
        ),
        Filing(
            [
                "BX0158",
                "Your Account Summary",
                "If you need to complete a",
                "tax return",
                "it contains the information you need",
            ],
            DocType.FISCAL,
            "cuentas",
            "summary",
        ),
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
            "BX0084",  # Individual Savings Account summary
            "BX0179",  # Statement of fees
            "BX0098",  # Account summary
            "BX0158",  # Annual tax summary
            "Santander, Cust Opers, PO Box 1109, Bradford, BD1 5XS",  # their generic address
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

        raise Exception("Documents seems to belong to bank but isn't recognised")

    def simple_document(self, lines, classification, entity="", extra_info=""):
        """ a lot of documents follow a basic pattern and we only need the first date we find """
        date = find_date(lines)
        if not date:
            raise Exception(
                f"Document {classification.value}, {entity}, {extra_info},"
                "does not contain a valid date"
            )
        return DocumentMetadata(
            period_start_date=date,
            period_end_date=None,
            bank=Bank.SANTANDER_UK,
            classification=classification,
            entity=entity,
            extra_info=extra_info,
        )
