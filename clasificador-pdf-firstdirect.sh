#!/bin/bash

# virtualenv --python=python3 venv
# source venv/bin/activate
# pip install -r requirements.txt

# date usage works on mac os x - need testing on Linux (!)
UNAME="`uname -a`"
if [[ $UNAME =~ *Darwin* ]] ; then
  echo "Need to test this on linux - take a look"
  exit 1
fi
  

TMPFILE="/tmp/procesar-tmp.txt"

for DOC in ./fd\ statement\ *.pdf; do

  TYPE="error"
  DATE="NOTFOUND"
  EXTRA=""
  if pdf2txt.py -Y loose -A "$DOC" >${TMPFILE} 2>${TMPFILE}-err; then

    DATE="`cat ${TMPFILE} | sed -n 's/.*[0-9]* [a-zA-Z]* to \([0-9]*\) \([a-zA-z]*\) \([0-9][0-9][0-9][0-9]\).*/\3.\2.\1/gp' | head -1`"
    if [ "$DATE" == "" ]; then
      DATE="`cat ${TMPFILE} | sed -n 's/.*[0-9]* [a-zA-Z]* [0-9][0-9][0-9][0-9] to \([0-9]*\) \([a-zA-z]*\) \([0-9][0-9][0-9][0-9]\).*/\3.\2.\1/gp' | head -1`"
    fi
    # convert from 2018.december.12 to 2018.12.12
    DATE="`date -j -f \"%Y.%B.%d\" \"$DATE\" \"+%Y.%m.%d\"`"

    # posibles textos conocidos

    if grep -s "Your Bonus Savings A/C details" ${TMPFILE} >/dev/null ; then
      TYPE="first direct bonus statement"
    elif grep -s "Your 1st Account details" ${TMPFILE} >/dev/null ; then
      TYPE="first direct statement"
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
    NAME="$DATE $TYPE$EXTRA firstdirect.pdf"
    NAME="`echo $NAME | awk '{print tolower($0)}'`"
    if [ -f "$NAME" ]; then
      echo "$DOC: Can't copy to $NAME as it already exists"
    else
      cp "$DOC" "$NAME"
      mv "$DOC" "$DOC.processed"
    fi
  fi
done
