#!/bin/bash

# virtualenv --python=python3 venv
# source venv/bin/activate
# pip install -r requirements.txt


TMPFILE="/tmp/procesar-tmp.txt"

for DOC in ./SCC_COMUNICADOS_PI_*.pdf; do

  TYPE="error"
  DATE="NOTFOUND"
  EXTRA=""
  if pdf2txt.py -Y loose -A "$DOC" >${TMPFILE} 2>${TMPFILE}-err; then

    DATE="`cat ${TMPFILE} | sed -n 's/.*Statement number: \([0-9][0-9]\)\/\([0-9][0-9][0-9][0-9]\).*/\2.\1/gp' | head -1`"

    # posibles textos conocidos

    if grep -s "Your account summary for" ${TMPFILE} >/dev/null ; then
      TYPE="santander statement"
    elif grep -s "Your ISA SAVER account summary for" ${TMPFILE} >/dev/null ; then
      TYPE="santander isa statement"
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
    NAME="$DATE $TYPE$EXTRA santander.pdf"
    NAME="`echo $NAME | awk '{print tolower($0)}'`"
    if [ -f "$NAME" ]; then
      echo "$DOC: Can't copy to $NAME as it already exists"
    else
      cp "$DOC" "$NAME"
      mv "$DOC" "$DOC.processed"
    fi
  fi
done
