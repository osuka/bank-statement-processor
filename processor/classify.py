#!/usr/bin/env python3
"""Parse PDF files from bank statements into a structure that
makes them easier to classify
"""
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# python style conventions https://www.python.org/dev/peps/pep-0008/

import argparse
import os
import re
from functools import reduce
from typing import List

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import (
    LAParams,
    LTAnno,
    LTChar,
    LTComponent,
    LTContainer,
    LTCurve,
    LTImage,
    LTLine,
    LTPage,
    LTRect,
    LTTextBoxHorizontal,
    LTTextBoxVertical,
)
from pdfminer.pdfdevice import PDFDevice
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from unidecode import unidecode

from banks.deutsche_bank_es import DeutscheBankDocuments
from banks.santander_uk import SantanderUKBankDocuments
from banks.citibank_uk import CitibankUKBankDocuments
from banks.first_direct_uk import FirstDirectUKBankDocuments
from parsing.metadata import DocumentMetadata

# PDFMINER guide in
# https://www.unixuser.org/~euske/python/pdfminer/programming.html


def find_pdfs(root):
    """finds al pdf files from a directory - accepts also file names"""
    if os.path.isfile(root):
        if root.endswith(".pdf"):
            yield root
        return

    for (dirpath, _, files) in os.walk(root):
        for file_name in files:
            if file_name.endswith(".pdf"):
                yield os.path.join(dirpath, file_name)


def clean_line(line):
    """returns the given text with any excess whitespace and newlines
    removed
    """
    line = re.sub(r"(  )+", "", line)
    line = re.sub(r"(\n\n)+", "\n", line)
    line = line.strip()
    return line


def convert_to_lines(page: LTComponent):
    """converts a container form pdfminer into a set of lines of text"""
    lines = []
    ignorable_elements = [LTImage, LTRect, LTLine, LTCurve]
    text_elements = [LTTextBoxHorizontal, LTChar, LTAnno, LTTextBoxVertical]
    container_elements = [LTContainer]

    for element in page:

        def is_one_of(previous, element_class):
            return previous or isinstance(
                element, element_class  # pylint: disable=cell-var-from-loop
            )

        if reduce(is_one_of, text_elements, False):
            lines.append(clean_line(element.get_text()))
        elif reduce(is_one_of, container_elements, False):
            lines += convert_to_lines(element)
        elif reduce(is_one_of, ignorable_elements, False):
            pass
        else:
            raise Exception(f"Type is {type(element)}")
    return lines


# various well known document patterns


# --------------------------------------------------------------------------------------------

# parsing of specific well known pdf document templates


def analyse(pdf_file_name: str, pages) -> DocumentMetadata:
    """Given a PDF document that has been parsed into Page entities, produce
    classification metadata"""

    bank_parsers = [
        DeutscheBankDocuments(),
        SantanderUKBankDocuments(),
        CitibankUKBankDocuments(),
        FirstDirectUKBankDocuments(),
    ]

    # join all the pages of the document
    lines = []
    for subset in [convert_to_lines(page) for page in pages]:
        for element in subset:
            lines.append(element)

    for bank_parser in bank_parsers:
        metadata = bank_parser.process(pdf_file_name, pages, lines)
        if metadata:
            return metadata

    return None


def extract_pages(pdf_file_name: str) -> List[LTPage]:
    """Opens, loads and parses a pdfile, producing a list of LTPage objects
    :param pdfFileName: File name to open and parse
    :raises: PDFTextExtractionNotAllowed if the text forbids parsing
    :return: list of PDFMiner layout objects, one per each page (yield)
    """
    with open(pdf_file_name, "rb") as pdf_file:
        parser = PDFParser(pdf_file)
        document = PDFDocument(parser)

        # Create a PDF resource manager object that stores shared resources.
        rsrcmgr = PDFResourceManager()

        device = PDFDevice(rsrcmgr)

        # we will be performing layout analysis
        # https://pdfminersix.readthedocs.io/en/latest/reference/composable.html
        laparams = LAParams(
            line_overlap=0.5,
            # char_margin=2.0,
            line_margin=1.5,
            # word_margin=0.1,
            # boxes_flow=None,
            # detect_vertical=True,
            all_texts=True,
        )

        device = PDFPageAggregator(rsrcmgr, laparams=laparams)

        interpreter = PDFPageInterpreter(rsrcmgr, device)

        # Process each page contained in the document.
        for page in PDFPage.create_pages(document):
            interpreter.process_page(page)
            # receive the LTPage object for the page.
            layout = device.get_result()
            yield layout


def get_arguments():
    """ parse provided command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files",
        nargs="+",
        help="PDF filenames and/or directories to traverse " "looking for them",
    )
    return parser.parse_args()


def main(files):
    """scan for PDF files inside the list of files or folders provided
    and rename them into a structure
    """
    errors = []
    last_folder = ""
    for file_or_folder in files:
        for pdf_file in find_pdfs(file_or_folder):
            try:
                pages = extract_pages(pdf_file)
                if last_folder != os.path.dirname(pdf_file):
                    last_folder = os.path.dirname(pdf_file)
                    print(f"\nin {last_folder}:\n")
                print(f"{os.path.basename(pdf_file)} = ", end="")
                metadata = analyse(pdf_file, pages)

                if not metadata:
                    print("--> UNKNOWN")
                    continue

                file_name = (
                    f"{metadata.period_start_date.strftime('%Y.%m.%d')} {metadata.bank.value} "
                    f"{metadata.classification.value}"
                )
                if metadata.entity:
                    file_name += f" {metadata.entity}"
                if metadata.extra_info:
                    file_name += f" {unidecode(metadata.extra_info.lower())}"
                file_name += ".pdf"
                # replace non ascii chars
                file_name = (
                    unidecode(file_name)
                    .replace("/", ".")
                    .replace(":", " ")
                    .replace("(", " ")
                    .replace(")", " ")
                    .replace(",", " ")
                    .replace("..", ".")
                    .strip()
                )
                file_name = " ".join(file_name.split())  # removes multiple spaces
                print(f"{file_name}")
            except Exception as exc:  # noqa: E0602
                errors.append(f"{pdf_file}: {exc}")
                raise exc

    print(f"===== Finished\nErrors: {errors}")


if __name__ == "__main__":
    args = get_arguments()
    main(args.files)
