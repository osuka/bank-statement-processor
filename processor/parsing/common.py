"""
Common patterns found on the resulting array of lines of text from parsing
PDFs.
"""

from datetime import datetime
from functools import reduce
import dateparser


def parse_date_es_ca(text: str):
    """parses a string into a date, trying dd.mm.yy, dd.mm.yyyy and other combinations """
    date = dateparser.parse(text, languages=["ca", "es"])
    if date:
        return date
    raise ValueError(f"not a date: {text}")


def contains_all(text, containee):
    """Returns true if the containee value or values exist in the provided text. Containe can
    be a string or a list of strings. If it's a list, all of them have to be contained."""
    if not isinstance(containee, list):
        return containee in text
    return reduce(lambda result, value: result and (value in text), containee, True)


def find_starting_with(lines, prefix):
    """finds inside array of strings the first one that starts with the
    given prefix followed by a new line, and returns the contents after the
    newline
    """
    for line in lines:
        if line.startswith(prefix + "\n"):
            return line.split("\n")[1]
    return None


def find_containing(lines, text):
    """finds inside array of strings the first one that contains the given
    string. If text is a list of strings then it finds one that contains all of them
    """
    for line in lines:
        if contains_all(line, text):
            return line
    return None


def find_after(lines, text):
    """finds inside an array of strings the string that immediately follows
    an entry exactly like "text"
    """
    index = 0
    for line in lines:
        index += 1
        if line == text:
            return lines[index]
    return None


def find_date_yyyymmdd(lines):  # noqa: E0602
    """finds the first string inside array of strings that is a valid date
    of the format YYYMMDD
    """
    for line in lines:
        if len(line) == 8 and (line.startswith("199") or line.startswith("20")):
            try:
                date = datetime.strptime(line, "%Y%m%d")
                return date
            except ValueError:
                pass
    return None
