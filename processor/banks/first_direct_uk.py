"""
Parsing for the documents received from the entity First Direct UK
"""

import re
from typing import List

from pdfminer.layout import LTPage

from parsing.common import find_containing, parse_date_gb
from parsing.metadata import Bank, DocType, DocumentMetadata, Filing

known_date_regexes = [
    # 'blahblahFrom 6 Apr 2018 to 5 Oct 2019blahblah
    re.compile(
        r".*[F|f]rom [0-9thndst]+ (?:Jan|Feb|Mar|May|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (?:to|-) (?P<date>[0-9thndst]+ (?:Jan|Feb|Mar|May|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}).*",  # pylint: disable=line-too-long
        re.MULTILINE | re.DOTALL,
    ),
    # 'blahblah6 April to 5 April 2019blahblah
    # 'blahblah6 April - 5 April 2019blahblah
    re.compile(
        r".*[0-9thndst]+ (?:January|February|March|May|April|June|July|August|September|October|November|December) (?:to|-) (?P<date>[0-9thndst]+ (?:January|February|March|May|April|June|July|August|September|October|November|December) \d{4}).*",  # pylint: disable=line-too-long
        re.MULTILINE | re.DOTALL,
    ),
    # blahblah6 April 2018 and 5 April 2019blahblah
    # blahblah6 April 2018 to 5 April 2019blahblah
    re.compile(
        r".*[0-9thndst]+ (?:January|February|March|May|April|June|July|August|September|October|November|December) \d{4} (?:and|to) (?P<date>[0-9thndst]+ (?:January|February|March|May|April|June|July|August|September|October|November|December) \d{4}).*",  # pylint: disable=line-too-long
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


class FirstDirectUKBankDocuments:
    """ Parsers for all the PDF documents """

    simple_mappings = [
        Filing(
            ["AccountSummary", "Your 1st Account details"], DocType.STATEMENT, "current"
        ),
        Filing(
            ["AccountSummary", "Your Bonus Savings A/C details"],
            DocType.STATEMENT,
            "bonus",
        ),
        Filing(
            ["AccountSummary", "Your Regular Saver details"],
            DocType.STATEMENT,
            "regular-saver",
        ),
        Filing(
            ["AccountSummary", "Your Savings Account details"],
            DocType.STATEMENT,
            "savings",
        ),
        # the document called 'annual summary' was later replaced with
        # the legally mandated 'statement of fees'
        Filing(
            [
                "Additional Information\nBetween",
                "your average debit balance",
                "your average \ncredit balance",
            ],
            DocType.NOTE,
            "comisiones",
            "anual",
        ),
        Filing(
            ["What is this Annual Summary", "annual summary of your account charges"],
            DocType.NOTE,
            "comisiones",
            "anual",
        ),
        Filing(
            ["Detailed statement of fees paid on the account"],
            DocType.NOTE,
            "comisiones",
            "anual",
        ),
    ]

    def process(
        self,
        file_name: str,  # pylint: disable=unused-argument
        pages: List[LTPage],  # pylint: disable=unused-argument
        lines: List[str],
    ) -> DocumentMetadata:
        """check if the document is from this entity, classify it if so
        and return metadata, else None"""

        # first try to determine if the document belongs here or not - if not, None is returned
        needs_one_of = ["firstdirect.com", "is a division of HSBC UK Bank plc"]
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
            bank=Bank.FIRST_DIRECT,
            classification=classification,
            entity=entity,
            extra_info=extra_info,
        )
