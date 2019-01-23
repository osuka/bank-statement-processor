#!/bin/bash

# Command line:
# pdf2txt.py -Y loose -A correspondencia.pdf

# virtualenv --python=python3 venv
# source venv/bin/activate
# pip install -r requirements.txt


TMPFILE="/tmp/procesar-tmp.txt"

for DOC in *.pdf; do

  TYPE="error"
  DATE="NOTFOUND"
  EXTRA=""
  if pdf2txt.py -Y loose -A "$DOC" >${TMPFILE} 2>${TMPFILE}-err; then

    # posibles indicadores de pagina

    HOJA="`cat ${TMPFILE} | tr '\n' ' ' | sed -n 's/.*HOJA[ ]*\([0-9][0-9][0-9]\).*/\1/gp'`"
    if [ "$HOJA" == "" ]; then
      HOJA="`cat ${TMPFILE} | tr '\n' '|' | sed -n 's/.*FULL[ ]*[|]*[ ]*[0-9]*[ ]*[|]*\([0-9][0-9][0-9]\)..*/\1/gp'`"
    fi
    if [ "$HOJA" == "" ]; then
      HOJA="`cat ${TMPFILE} | tr '\n' '|' | sed -n 's/.*FULL Nº[ ]*[|]*TELF.[ ]*[|]*REFERENCIA GESTORA[ ]*[|]*ENTITAT[ ]*OFICINA[ ]*DC[ ]*NUM. DE COMPTE[ ]*[|]*[0-9]*[|]*[0-9]*[|]*[0-9]*[|]*[0-9]*[|]*[ ]*\([0-9]*\).*/\1/gp'`"
    fi
    if [ "$HOJA" == "" ]; then
      # adeudo zurich vida
      HOJA="`cat ${TMPFILE} | tr '\n' '|' | sed -n 's/.*HOJA||.*CUENTA CLIENTE (IBAN)||[ ]*|ES[0-9 ]*||[ ]*\([0-9]*\).*/\1/gp'`"
    fi

    # posibles formas de fecha

    DATE="`cat ${TMPFILE} | tr '\n' '|' | sed -n 's/.*FECHA[|]*OFICINA[|]*\(..\)\.\(..\)\.\(....\).*/\3.\2.\1/gp'`"
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | sed -n 's/\(20[0-3][0-9]\)\([01][0-9]\)\([0-3][0-9]\)/\1.\2.\3/gp'`"
    fi
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | tr '\n' ' ' | sed -n 's/.*DATA[ ]*REF\.[ ]*CONCEPTE[ ]*\(..\)\.\(..\)\.\(....\).*/\3.\2.\1/gp'`"
    fi
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | tr '\n' ' ' | sed -n 's/.*DATA[ ]*OFICINA[ ]*\(..\)\.\(..\)\.\(....\).*/\3.\2.\1/gp'`"
    fi
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | tr '\n' ' ' | sed -n 's/.*DATA[ ]*OFICINA[ ]*N.[ ]*PRÉSTEC[ ]*\(..\)\.\(..\)\.\(....\).*/\3.\2.\1/gp'`"
    fi
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | tr '\n' ' ' | sed -n 's/.*FECHA[ ]*OFICINA[ ]*TELF.[ ]*CUENTA CLIENTE (IBAN)[ ]*\(..\)\.\(..\)\.\(....\).*/\3.\2.\1/gp'`"
    fi
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | tr '\n' ' ' | sed -n 's/.*POSICIÓ GLOBAL A \(..\)\/\(..\)\/\(....\).*/\3.\2.\1/gp'`"
    fi
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | tr '\n' ' ' | sed -n 's/.*DATA,[ ]*\(..\)\.\(..\)\.\(....\).*/\3.\2.\1/gp'`"
    fi
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | tr '\n' ' ' | sed -n 's/DATA[ ]*\(..\)\.\(..\)\.\(..\).*/20\3.\2.\1/gp'`"
    fi
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | tr '\n' ' ' | sed -n 's/.*VALOR[ ]*\(..\)\.\(..\)\.\(..\).*/20\3.\2.\1/gp'`"
    fi
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | sed -n 's/\(20[0-3][0-9]\)\([01][0-9]\)\([0-3][0-9]\)/\1.\2.\3/gp'`"
    fi

    # posibles textos conocidos

    if grep -s "ADEUDO POR DOMICILIACIÓN SEPA" ${TMPFILE} >/dev/null ; then
      TYPE="adeudo"
      EXTRA="`cat ${TMPFILE} | tr '\n' '|' | sed -n 's/.*ORDENANTE[|]*\([ñÑáéíóúÁÉÍÓ\.,ÚA-Za-z0-9 -]*\).*/\1/gp'`"
    elif grep -s "INFORMACIÓ SOBRE ELS PERFILS DELS SEUS PRODUCTES" ${TMPFILE} >/dev/null ; then
      TYPE="info-perfiles"
    elif grep -s "EXTRACTO CUENTA NOMINA BANCA ASOCIADA DB" ${TMPFILE} >/dev/null ; then
      TYPE="extracto-cuenta"
    elif grep -s "EXTRACTE LIQUIDACIÓ COMPTE TARGETA DE CRÈDIT" ${TMPFILE} >/dev/null ; then
      TYPE="liq-tarjeta"
    elif grep -s "DENOMINACIÓ PRODUCTE" ${TMPFILE} >/dev/null ; then
      TYPE="producto"
    elif grep -s "CÀRREC REBUT PRÉSTEC HIPOTECARI" ${TMPFILE} >/dev/null ; then
      TYPE="recibo-hipoteca"
    elif grep -s "ABONO TRANSFERENCIA SEPA" ${TMPFILE} >/dev/null ; then
      TYPE="abono-transferencia"
    elif grep -s "NOVES CONDICIONS DE LA CUENTA MULTIRIESGO" ${TMPFILE} >/dev/null ; then
      TYPE="producto-multiriesgo"
    elif grep -s "ESTAT DE POSICIÓ DE FONS" ${TMPFILE} >/dev/null ; then
      TYPE="extracto-fondo-inversion"
      if [ "$DATE" == "" ]; then
        HOJA="2"
      fi
    elif grep -s "CAPITAL PENDENT" ${TMPFILE} >/dev/null ; then
      if grep -s "PER CÀLCUL" ${TMPFILE} >/dev/null ; then
        if grep -s "D'INTERESSOS" ${TMPFILE} >/dev/null ; then
          TYPE="interes-hipoteca"
        fi
      fi
    elif grep -s "RENOVACIÓ TIPUS" ${TMPFILE} >/dev/null ; then
      TYPE="renovacion-interes"
    elif grep -s "RENOVACIÓ TIPUS" ${TMPFILE} >/dev/null ; then
      TYPE="renovacion-interes"
    elif grep -s "FONS D'INVERSIÓ - SUBSCRIPCIÓ" ${TMPFILE} >/dev/null ; then
      TYPE="suscripcion-fondo"
    else
      TYPE="unknown"
    fi
  fi

  # nuevo nombre

  if [ "$TYPE" == "error" ]; then
    echo "$DOC: Could not process. Document is encrypted."
  elif [ "$DATE" == "NOTFOUND" ]; then
    echo "$DOC: Type is $TYPE but date can't be found"
  else
    if [ "$EXTRA" != "" ]; then
      EXTRA=" `echo $EXTRA | sed 's/[^ a-zA-Z0-9-]//g'`"
    fi
    if [ "$HOJA" != "" ]; then
      HOJA=" $HOJA"
    fi
    echo "$DOC: $DATE $TYPE$EXTRA$HOJA"
  fi
done
