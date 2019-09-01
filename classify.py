#!/usr/bin/env python3
'''Parse PDF files from bank statements into a structure that
makes them easier to classify
'''
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# python style conventions https://www.python.org/dev/peps/pep-0008/

import os
import argparse
import re
from datetime import datetime


# PDFMINER guide in
# https://www.unixuser.org/~euske/python/pdfminer/programming.html

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams, LTPage, LTComponent, \
    LTTextBoxHorizontal, LTContainer
from pdfminer.converter import PDFPageAggregator


def find_pdfs(root):
    '''finds al pdf files from a directory - accepts also file names
    '''
    if os.path.isfile(root):
        if root.endswith('.pdf'):
            yield root
        else:
            print(f'{root}: not a pdf file')
        return

    for (dirpath, _, files) in os.walk(root):
        for fileName in files:
            if fileName.endswith('.pdf'):
                yield os.path.join(dirpath, fileName)
            else:
                print(f'{fileName}: not a pdf file')


def clean_line(line):
    '''returns the given text with any excess whitespace and newlines
    removed
    '''
    line = re.sub(r'(  )+', '', line)
    line = re.sub(r'(\n\n)+', '\n', line)
    line = line.strip()
    return line


def convert_to_lines(page: LTComponent):
    '''converts a container form pdfminer into a set of lines of text
    '''
    lines = []
    for element in page:
        if isinstance(element, LTTextBoxHorizontal):
            lines.append(clean_line(element.get_text()))
        elif isinstance(element, LTContainer):
            lines += convert_to_lines(element)
    return lines


# various well known document patterns

def find_starting_with(lines, prefix):
    '''finds inside array of strings the first one that starts with the
    given prefix followed by a new line, and returns the contents after the
    newline
    '''
    for line in lines:
        if line.startswith(prefix + '\n'):
            return line.split('\n')[1]
    return None


def find_after(lines, text):
    '''finds inside an array of strings the string that immediately follows
    an entry exactly like "text"
    '''
    index = 0
    for line in lines:
        index += 1
        if line == text:
            return lines[index]
    return None


def find_date_YYYYMMDD(lines): # noqa: E0602
    '''finds the first string inside array of strings that is a valid date
    of the format YYYMMDD
    '''
    for line in lines:
        if len(line) == 8 and \
                (line.startswith('199') or line.startswith('20')):
            try:
                date = datetime.strptime(line, '%Y%m%d')
                return date
            except: # noqa: E722
                pass
    return None


def find_date_DATA(lines): # noqa: E0602
    '''finds the first string that matches the pattern "DATA \n02.01.18"
    and returns a date object with the given date
    '''
    for line in lines:
        if line.startswith('DATA \n'):
            try:
                date = datetime.strptime(line.split('\n')[1], '%d.%m.%y')
                return date
            except: # noqa: E722
                pass
    return None


def find_date_PERIODE(lines): # noqa: E0602
    '''Finds the first string like "Període de l'1 al 31 Desembre de 2017"
    and returns a date object with the given end date parsed
    '''
    translate = {
        'Gener':     1,
        'Febrer':    2,
        'Març':      3,
        'Abril':     4,
        'Maig':      5,
        'Juny':      6,
        'Juliol':    7,
        'Agost':     8,
        'Setembre':  9,
        'Octubre':  10,
        'Novembre': 11,
        'Desembre': 12
    }

    for line in lines:
        if line.startswith('Període de '):
            try:
                matches = re.match(r'.*(?P<diaStart>[\d]+) al '
                                   r'(?P<diaEnd>[\d]+) '
                                   r'(?P<mes>[GFMAJSOND][a-z]*) '
                                   r'de (?P<any>[\d]+)', line)
                month_str = matches.group('mes')
                month = translate[month_str]
                if not month:
                    raise Exception(f'Unknown month {month_str}')
                year_str = matches.group('any')
                year = int(year_str)
                if year < 1990 or year > 2100:
                    raise Exception(f'Unknown year {year_str}')
                start_str = matches.group('diaStart')
                start = int(start_str)
                if start < 1 or start > 31:
                    raise Exception(f'Unknown year {start_str}')
                end_str = matches.group('diaEnd')
                end = int(end_str)
                if end < 1 or end > 31:
                    raise Exception(f'Unknown year {end_str}')
                date = datetime.strptime(f'{year}.{month}.{end}', '%Y.%m.%d')
                return date
            except: # noqa: E722
                pass
    return None

# parsing of specific pdf documents


def debit(lines):
    '''recibo
    '''
    emisor = find_starting_with(lines, 'EMISOR - ORDENANTE')
    titular = find_starting_with(lines, 'TITULAR DOMICILIACIÓN')
    concepto = find_starting_with(lines, 'CONCEPTO DE PAGO')
    cuenta = find_after(lines, 'CUENTA CLIENTE (IBAN)')
    emisor_id = find_starting_with(lines, 'IDENTIFICACIÓN EMISOR')
    date_str = find_after(lines, 'OFICINA')
    date = datetime.strptime(date_str, '%d.%m.%Y')
    if not emisor or not titular or not concepto or not cuenta or \
            not emisor_id or not date: # noqa: E303
        raise Exception('Unknown document')

    filedate = datetime.strftime(date, '%Y.%m.%d')
    print(f'{filedate} db recibo {emisor}.pdf')


def perfil_inversor(lines):
    '''carta informant de perfil inversor de productes contractats
    ['DENOMINACIÓ PRODUCTE', 'ISIN', "PERFIL DE COMPLEXITAT\nEn ...\n...",
    'PERFIL DE RISC\nEn una escala de cinc nivells de risc:\nMolt Conserv...',
    'DWS AHORRO F.I.', 'ES0123456789', '0', 'Molt Conservador', '',
    "Els perfils que li comuniquem...", "El present...",
    'Deutsche Bank, S.A....',
    '20190123', 'FR AX9', 'Pàgina', '02', 'de', '02']
    '''
    perfil_de_risc = find_starting_with(lines, 'PERFIL DE RISC')
    codi = find_after(lines, 'DWS AHORRO F.I.')
    date = find_date_YYYYMMDD(lines)
    if not perfil_de_risc or not date or not codi:
        raise Exception('Unknown document')

    filedate = datetime.strftime(date, '%Y.%m.%d')
    print(f'{filedate} db perfiles.pdf')


def estat_inversio(lines):
    '''informe de inversio
    ['DATA \n02.01.18', 'OFICINA\nBARNA-V.AUGUSTA',
    "ESTAT DE POSICIÓ DE FONS D' INVERSIÓ.\nFULL Nº", 'TELF.',
    'REFERENCIA GESTORA\nENTITATOFICINADC NUM. DE COMPTE \n0000', '0000000000',
    '0000', '00', '0', '930000000(cid:0)',
    'TITULAR/S\nNOMBRE APELL1 APPEL2\nNOM2 APPEL1 APPEL2',
    'N.I.F./C.I .F.:\n000000001X\n000000002X',
    "POSICIÓ GLOBAL A 31/12/2017FONS D'INVERSIO: DWS AHORRO FI ISIN: ...\n..",
    'REND. MITJANA (*):...\n...:',
    '-0,111\n+0,111\n-0,111\n 1,111', '%\n%\n%',
    'PATRIMONI DE LA IIC:\n...', '0,000', '%',
    'Ent.Comercializadora: Deutsche Bank, Sociedad Anónima Española...',
    '20190123', 'FR 550']
    '''
    date = find_date_DATA(lines)
    filedate = datetime.strftime(date, '%Y.%m.%d')
    print(f'{filedate} db posicion fondo inversion.pdf')


def extracto_integrado(lines):
    '''extracte integrat
    ['EXTRACTE INTEGRAT DB', "Període de l'1 al 31 Desembre de 2017", '', '',
    'Pàgina 1/3', '', 'CODIFICACIÓ DE TITULARS\nNº ORDRE', 'NIF', 'NOM',
    '1\n2', '00.000.001-X\n00.000.002-X', 'Nom1 Ap1 Ap2\nNom2 Ap1 Ap2', '', '',
    'Benvolguts Clients,\nA continuació li...',
    'El seu Gestor Personal\n \n...', 'Servei Deutsche Bank Online ...',
    'RESUM DE LES SEVES POSICIONS', '',
    'COMPTES A LA VISTA I TARGETES DE CRÈDIT',
    'SALDO ANTERIOR EUR', 'SALDO ACTUAL EUR',
    'Targetes de Crèdit (*)',
    '-00,00', '-00,00',
    "PRODUCTES D'ESTALVI INVERSIÓ",
    'SALDO ANTERIOR EUR', 'SALDO ACTUAL EUR',
    "Fons d'Inversió\nTotal Estalvi Inversió en EUR",
    'PRÉSTECS', 'Préstec Hipotecari\nTotal Préstecs en EUR', '', '',
    '000,00\n001,00', # prestec
    'SALDO ANTERIOR EUR',
    '-000.000,00\n-000.000,00', # hipoteca
    '000,00\n000,00', # cuenta
    'SALDO ACTUAL EUR', '-000.000,00\n-000.000,00', # hipoteca
    '', '', '', '', '', '(*) Els imports ..',
    '00000000 00 0000000 00 20180101']
    ["Període de l'1 al 31 Desembre de 2017", '', 'Pàgina 2/3',
    'DETALL DE POSICIONS DELS SEUS CONTRACTES',
    '__ Targetes de Crèdit _________....__', '', '', '',
    'PRODUCTE / Nº CONTRACTE', 'Cod. Titular',
    'Targetes \nAssociades Límit Crèdit Saldo Impagat', 'Saldo Ajornat',
    'Moviments', 'Període', 'Saldo deutor', 'abans del càrrec',
    'Import a Carregar en', 'Compte',
    'TARJETA DE CRÉDITO', '0019.0000.00.0000000000', '1', '1', '0.000,00',
    'TOTAL', '', '', '0.000,00', '', '0,00', '0,00', '', '0,00', '0,00', '',
    '00,00', '00,00', '', '00,00', '00,00', '', '00,00', '00,00',
    "__ Fons d'Inversió ____________...__", '',
    'PRODUCTE', 'Núm. Participac.', 'Núm. Participac.', 'ANTERIOR', 'ACTUAL',
    'Rend. Mitjana', '(1)', 'Núm.Contracte', 'Cod. Titular', 'VL EUR',
    'Saldo EUR', 'DWS AHORRO FI', '', '1,2',
    '0019.0000.00.0000000000-ES0000000000', '0,00000', '000,00', '0000',
    'Inversions del', 'mes', '', '', '', 'VL EUR', 'Saldo EUR',
    'Anys inversió', '% IIC', '0,000', '0.000,005', '-0,00%', '0,000%', '00,0',
    '0,00', 'TOTAL', "(1) No inclou ...", '', '0.000,00', '0.0000,00', '', '',
    'PRODUCTE', 'Tipus Inversió', 'Data Inv', 'Núm.', 'Participac.',
    'Import subscrit Valor Liquidatiu', 'Valor efectiu',
    'Rendiment Rend. Mitjana', '(*)',
    'FI RENTA FIJA EURO CORTO PLAZO', 'DWS AHORRO FI',
    '0019.0000.00.0000000000-', '0019.0000.00.0000000000-', '', 'Suscripció',
    'TOTAL', '2011- 2016', '21.03.2017', '0,000', '0,000', '0,000', '000,00',
    '000,00', '0,000', '0,000', '0,000', '0,000', '0,000', '-0,0', '-0,0',
    '-0,0', '-0,0%', '-0,0%', '-0,0%', '(*) No incl..',
    '__ Préstecs ____________________...__', '',
    'PRODUCTE', 'Cod. Titular Capital Inicial Data Inici', 'Data Fin',
    "Tipus \nd'Interés", 'Div.', 'Pagament', 'Període', 'Capital Inici',
    'Període', 'Capital Fin', 'Període', 'Capital Fin \nPeríode EUR',
    'HIPOTECA 100 PLUS TRAMOS', '0019.0000.00.0000000000', '1,2',
    '-00,00 dd.mm.yyyy yy.mm.yyyy', '0,0% EUR', '0,0', '-000,0002', '-0,0',
    '-0,0', 'TOTAL', '', '', '', '', '', '-0,0', '',
    'INFORMACIÓ PERÍODE ACTUAL', '00000000 00 0000000 00 yyyymmdd']
    ['', '', '', '', '', '', '', '', '', '', '', '',
    "Període de l'1 al 31 Desembre de 2017", '', 'Pàgina 3/3',
    'DETALL DE MOVIMENTS DEL PERÍODE EN ELS SEUS CONTRACTES', '',
    '__ Detall de liquidacions dels seus contractes de Targetes de Crèdit _..',
    'NÚMERO DE CONTRACTE', '', '0019.0000.00.00000000', '', 'TITULAR',
    'TARGETES ASSOC.', 'DIVISA', 'COMPTE ASSOCIAT', 'LÍMIT CRÈDIT',
    'FORMA PAGAM.', 'NOM1 AP1 AP2', '1 \nEUR', '0019.0000.00.00000', '00,00',
    'EFECTIU', '', '', '',
    'MOVIMENTS PERÍODE', 'SALDO AJORNAT MES ANTERIOR', 'INTERÉS SALDO AJORNAT',
    'QUOTES MAXI-COMPRA DEL PERÍODE', 'COMISSIÓ MAXI-COMPRA',
    'SALDO MAXI-COMPRA', 'TOTAL SALDO CONTRACTE', '', '', '', '', '', '',
    '', '', '', '', '', '', '', '', '', '', '', '', '', '',
    '00,00', '0,00', '0,00', '0,00', '0,00', '0,00', '00,00',
    'Liquidació període del 20/11/17 al 20/12/17', 'DATA DE CÀRREC',
    'LA SEVA ORDRE DE PAGAMENT', 'EXCEDIT LÍMIT DE CRÈDIT',
    'QUOTES MAXI-COMPRA DEL PERÍODE', 'IMPORT A CARREGAR EN COMPTE',
    '02.01.2018', '00,00', '0,00', '0,00', '00,00',
    '', '', '', '', '',
    '__ Detall de moviments del període de les seves Targetes de Crèdit __...',
    'V. CLASSIC - 0000 00** **** 0000', 'Límit 000,00 EUR - NOM1 AP1 AP2', '',
    'Data Op.', 'Concepte', 'Població', '', 'País', 'NÚMERO DE CONTRACTE', '',
    '0019.0000.00.00000000', 'DETALL DEL MOVIMENT', 'Div.', 'Import en Div.',
    'Canvi Aplicat', 'Import EUR',
    '01.12.2017', '<descripcion blah>', '<quien es>', '<pais>', 'EUR', '',
    'TOTAL', '', '', '', '00,00', '00,00',
    'INFORMACIÓ GESTORES', 'Nom Fons', 'DWS AHORRO FI', 'Codi ISIN',
    'Entitat Gestora', 'Entitat Dipositaria', 'ES0123456789',
    'DWS INVESTMENTS (SP)', 'DEUTSCHE BANK,S.A.ESPAñOLA', 'NÚM. \nCNMV',
    '0000', 'Entitat comercialitzadora: Deutsche Bank, ....', '', '',
    "Li preguem revisi ...", "Informació Legal...\n",
    '00000000 00 0000000 00 20180101']
    '''

    date = find_date_PERIODE(lines)
    filedate = datetime.strftime(date, '%Y.%m.%d')
    print(f'{filedate} db extracto integrado.pdf')


def analyse(pages):
    page: LTPage
    for page in pages:
        lines = convert_to_lines(page)
        if lines[0] == 'ADEUDO POR DOMICILIACIÓN SEPA':
            debit(lines)
        elif lines[0] == 'EXTRACTE INTEGRAT DB':
            extracto_integrado(lines)
        elif 'DWS AHORRO F.I.' in lines and \
                find_starting_with(lines, 'PERFIL DE RISC'):
            perfil_inversor(lines)
        elif find_starting_with(lines,
                                'ESTAT DE POSICIÓ DE FONS D\' INVERSIÓ.'):
            estat_inversio(lines)
        else:
            print(lines)
        pass


def extract_pages(pdfFileName):
    """ Opens, loads and parses a pdfile, producing a list of LTPage objects
    :param pdfFileName: File name to open and parse
    :raises: PDFTextExtractionNotAllowed if the text forbids parsing
    :return: list of PDFMiner layout objects, one per each page (yield)
    """
    with open(pdfFileName, 'rb') as pdfFile:
        parser = PDFParser(pdfFile)
        document = PDFDocument(parser)

        # Create a PDF resource manager object that stores shared resources.
        rsrcmgr = PDFResourceManager()
        # Create a PDF device object.
        device = PDFDevice(rsrcmgr)
        # Create a PDF interpreter object.
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        # Process each page contained in the document.
        for page in PDFPage.create_pages(document):
            interpreter.process_page(page)

        # Performing Layout Analysis

        # Set parameters for analysis.
        laparams = LAParams(line_overlap=0.5,
                            char_margin=2.0,
                            line_margin=0.5,
                            word_margin=0.1,
                            boxes_flow=0.5,
                            detect_vertical=False,
                            all_texts=True)

        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page in PDFPage.create_pages(document):
            interpreter.process_page(page)
            # receive the LTPage object for the page.
            layout = device.get_result()
            yield layout


def get_arguments():
    '''parse provided command line arguments
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+',
                        help='PDF filenames and/or directories to traverse '
                        'looking for them')
    return parser.parse_args()


def main(files):
    '''scan for PDF files inside the list of files or folders provided
    and rename them into a structure
    '''
    errors = []
    for file_or_folder in files:
        for pdf_file in find_pdfs(file_or_folder):
            try:
                pages = extract_pages(pdf_file)
                print(f'Processing {pdf_file}')
                analyse(pages)
            except Exception as exc: # noqa: E0602
                errors.append(f'{pdf_file}: {exc}')
                raise exc

    print(f'===== Finished\nErrors: {errors}')


if __name__ == '__main__':
    args = get_arguments()
    main(args.files)
