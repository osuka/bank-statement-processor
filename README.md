
# Setup

Estos scripts utilizan pdf2txt.py que se incluye con la distribucion de pdfmine.py. Concretamente usamos el fork para python3 del producto.

```bash
# virtualenv --python=python3 venv
# source venv/bin/activate
# pip install -r requirements.txt
```


# Deutsche Bank

Bajar extractos como "correspondencia\*pdf" (el nombre que tienen por defecto).

Ejecutar el script `./clasificador-pdf-db.sh` donde estan los ficheros.

Los que procese correctamente se renombraran a "\<NOMBRE\>.processed"

Si hay errores se muestran por pantalla y los ficheros quedan sin renombrar

Posibles errors:

- Fichero no pertenece a ninguna pattern conocida
- Fichero usa encriptacion (como el extracto integrado)
- El script no ha sido capaz de detectar multiples hojas, y el 2 documento intenta escribir con el mismo nombre y falla

En esos casos, modificar el script si tiene sentido - o simplemente editar a mano
