"""
Parsing for the documents received from the entity Citibank UK
"""

import re
from typing import List

from pdfminer.layout import LTPage

from parsing.common import find_containing, parse_date_gb
from parsing.metadata import Bank, DocType, DocumentMetadata, Filing

known_date_regexes = [
    # blahblah\01/07/2018 - 30/06/2019\nblah blabh
    # blahblah\01/07/2018 - 30/06/2019\nblah blabh
    re.compile(
        r".*\d{2}/\d{2}/\d{4} - (?P<date>\d{2}/\d{2}/\d{4}).*",
        re.MULTILINE | re.DOTALL,
    ),
    # 5 Mar 2018 - 24 Apr 2018
    re.compile(
        r".*[0-9thndst]+ (?:Jan|Feb|Mar|May|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} - (?P<date>[0-9thndst]+ (?:Jan|Feb|Mar|May|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}).*",  # pylint: disable=line-too-long
        re.MULTILINE | re.DOTALL,
    ),
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


class CitibankUKBankDocuments:
    """ Parsers for all the known PDF documents """

    simple_mappings = [
        Filing(["Relationship report for"], DocType.STATEMENT, "current", "summary"),
        Filing(
            ["SUMMARY OF YOUR CITIBANK ACCOUNT"],
            DocType.STATEMENT,
            "current",
            "summary",
        ),
    ]

    def process(
        self,
        file_name: str,  # pylint: disable=unused-argument
        pages: LTPage,  # pylint: disable=unused-argument
        lines: List[str],
    ) -> DocumentMetadata:
        """check if the document is from this entity, classify it if so
        and return metadata, else None"""

        # first try to determine if the document belongs here or not - if not, None is returned
        needs_one_of = [
            "Summary of your Citi Relationship",
            "SUMMARY OF YOUR CITIBANK ACCOUNT",
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
            bank=Bank.CITIBANK_UK,
            classification=classification,
            entity=entity,
            extra_info=extra_info,
        )
