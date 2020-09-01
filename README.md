# Custom bank statement processor

Scripts to parse and classify in folders the various horribly formatted bank statements and other communications from a few banks I do or have done business with.

They all follow a common pattern: generate PDF with absurd names that don't have anything to do with the contents, they change the format from one set of statements to the next.

Since going 'paperless' I'm finding that classifying these documents which may be important in the future has become _more_ cumbersome than doing it with the paper versions.

## Approach

Main goal is to identify the various types and classify them into folders by year and subject, so that with a quick look I can find what I'm looking for.

These script parse the PDFs into text and with simple checks output a metadata object. Currently the metadata object is used to rename the source files with enough detail to make them intelligible. Door is open to add more metadata and use file system labels or similar extensions.

The source documents are in English, Spanish and Catalan and I don't know enough about NLP to do any deeper analysis. Initial tests showed that there was not a great variation of templates in use by banks so this is good enough, although the templates change over time or have small tweaks.

# Setup

Recommended: Visual Studio code

Create a new virtualenv and install requirements.txt in there

```bash
# virtualenv --python=python3 .venv
# source .venv/bin/activate
# pip install -r requirements.txt
```

Note, we are using [pdfminer.six](https://github.com/pdfminer/pdfminer.six) which is an updated version of pdfminer. This includes the script `pdf2txt.py` that I used during a first exploratory phase to check the feasibility, and most importantly it supports python 3.

## Provider notes

Check [this folder](./processor/banks) for the currently supported banks.
