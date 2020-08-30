#!/usr/bin/env python3
"""Parse PDF files from bank statements into a structure that
makes them easier to classify
"""
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# python style conventions https://www.python.org/dev/peps/pep-0008/

import os
import argparse
import re
from typing import List

from unidecode import unidecode

# PDFMINER guide in
# https://www.unixuser.org/~euske/python/pdfminer/programming.html

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import (
    LAParams,
    LTPage,
    LTComponent,
    LTTextBoxHorizontal,
    LTContainer,
    LTImage,
    LTChar,
    LTRect,
    LTLine,
    LTAnno,
)
from pdfminer.converter import PDFPageAggregator

from parsing.common import find_starting_with
from parsing.metadata import DocumentMetadata, unclassified
from banks.deutsche_bank_es import DeutscheBankDocuments


def find_pdfs(root):
    """finds al pdf files from a directory - accepts also file names"""
    if os.path.isfile(root):
        if root.endswith(".pdf"):
            yield root
        else:
            print(f"{root}: not a pdf file")
        return

    for (dirpath, _, files) in os.walk(root):
        for file_name in files:
            if file_name.endswith(".pdf"):
                yield os.path.join(dirpath, file_name)
            else:
                print(f"{file_name}: not a pdf file")


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
    for element in page:
        if (
            isinstance(element, LTTextBoxHorizontal)
            or isinstance(element, LTChar)
            or isinstance(element, LTAnno)
        ):
            lines.append(clean_line(element.get_text()))
        elif isinstance(element, LTContainer):
            lines += convert_to_lines(element)
        elif (
            isinstance(element, LTImage)
            or isinstance(element, LTRect)
            or isinstance(element, LTLine)
            or isinstance(element, LTAnno)
        ):
            pass
        else:
            raise Exception(f"Type is {type(element)}")
    return lines


# various well known document patterns


# --------------------------------------------------------------------------------------------

# parsing of specific well known pdf document templates


def analyse(pages) -> DocumentMetadata:
    """Given a PDF document that has been parsed into Page entities, produce
    classification metadata"""

    deutsche = DeutscheBankDocuments()

    page: LTPage
    for page in pages:
        lines = convert_to_lines(page)
        if find_starting_with(lines, "ADEUDO POR DOMICILIACIÓN SEPA"):
            return deutsche.debit(lines)
        if "EXTRACTE INTEGRAT DB" in lines:
            return deutsche.extracto_integrado(lines)
        if "DWS AHORRO F.I." in lines and find_starting_with(lines, "PERFIL DE RISC"):
            return deutsche.perfil_inversor(lines)
        if find_starting_with(lines, "ESTAT DE POSICIÓ DE FONS D' INVERSIÓ."):
            return deutsche.estat_inversio(lines)
        if find_starting_with(lines, "EXTRACTO CUENTA NOMINA BANCA ASOCIADA DB"):
            return deutsche.extracto_cuenta(lines)
    return unclassified(lines)


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
            char_margin=2.0,
            line_margin=1.5,
            word_margin=0.1,
            # boxes_flow=None,
            detect_vertical=True,
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
    for file_or_folder in files:
        for pdf_file in find_pdfs(file_or_folder):
            try:
                pages = extract_pages(pdf_file)
                print(f"Processing {pdf_file}")
                metadata = analyse(pages)

                folder = metadata.period_start_date.strftime("%Y")
                file_name = (
                    f"{metadata.period_start_date.strftime('%Y.%m.%d')} {metadata.bank.value} "
                    f"{metadata.classification.value}"
                )
                if metadata.entity:
                    file_name += f" {metadata.entity}"
                # if metadata.extra_info:
                #     file_name += f" {metadata.extra_info}"
                file_name += ".pdf"
                # replace non ascii chars
                file_name = unidecode(file_name)
                print(f"       --> {folder}/{file_name}")
            except Exception as exc:  # noqa: E0602
                errors.append(f"{pdf_file}: {exc}")
                raise exc

    print(f"===== Finished\nErrors: {errors}")


if __name__ == "__main__":
    args = get_arguments()
    main(args.files)
