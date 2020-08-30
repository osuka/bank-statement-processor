# Custom bank statement processor

Scripts to parse and classify in folders the various horribly formatted bank statements and other communications from a few banks I do or have done business with.

They all follow a common pattern: generate PDF with absurd names that don't have anything to do with the contents, they change the format from one set of statements to the next.

Since going 'paperless' I'm finding that classifying these documents which may be important in the future has become _more_ cumbersome than doing it with the paper versions.

## Approach

Main goal is to identify the various types and classify them by year and subject.

These script parse the PDFs into text and with simple checks output the classification action. The documents are in English, Spanish and Catalan and I don't know enough about NLP to do any deeper analysis.Initial tests show that there is not a great variation of templates in use so this seems feasible.

# Setup

Recommended: Visual Studio code

Create a new virtualenv and install requirements.txt in there

```bash
# virtualenv --python=python3 .venv
# source .venv/bin/activate
# pip install -r requirements.txt
```

Note, we are using [pdfminer.six](https://github.com/pdfminer/pdfminer.six) which is an updated version of pdfminer. This includes the script `pdf2txt.py` that we are interested in the most, and supports python 3.

## Provider notes

### Deutsche Bank Spain

Most documents are saved under a generic name that gets incremented by the browser when there's more than one, in a pattern of "correspondencia\*pdf".

Ejecutar el script `./clasificador-pdf-db.sh` donde estan los ficheros.

Los que procese correctamente se renombraran a "\<NOMBRE\>.processed"

Si hay errores se muestran por pantalla y los ficheros quedan sin renombrar

Posibles errors:

- Fichero no pertenece a ninguna pattern conocida
- Fichero usa encriptacion (como el extracto integrado)
- El script no ha sido capaz de detectar multiples hojas, y el 2 documento intenta escribir con el mismo nombre y falla

En esos casos, modificar el script si tiene sentido - o simplemente editar a mano
