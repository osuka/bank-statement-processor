#!/bin/bash

# download pdf statements from the app in Accounts / [Click on Name] / Statement History

# download qif bank statements in Summary / Export & Bank Statements / All time 
for i in Monzo*pdf ; do d=`pdf2txt.py $i | awk 'BEGIN { RS = "" ; FS = "\n" } {if ($1 == "Statement") { print $2 }}'`; mv "$i" "${d:6:4}.${d:3:2}.${d:0:2} monzo statement.pdf"; done
