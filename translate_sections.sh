#! /usr/bin/env sh

echo "<SECTIONS>" > raw.txt

cat $1 | grep -v "^<SUBSECTION.*>\|</SUBSECTION>" | grep -v "^\#.*$" >> raw.txt

echo "</SECTIONS>" >> raw.txt

mv raw.txt $2
