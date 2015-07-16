#! /usr/bin/env sh

echo "<SECTIONS>" > raw.txt

cat $1 | grep -v "^\s*#\|<INCLUDE>\|</INCLUDE>\|<FILE>\|</FILE>\|<SUBSECTION.*>\|</SUBSECTION>" | sed "s/<\/TITLE>/<\/TITLE>\n<SYMBOLS>/" | sed "s/<\/SECTION>/<\/SYMBOLS>\n<\/SECTION>/g" | awk '!/^\s*(<|$)/{print "<SYMBOL>"$0"</SYMBOL>";next}1' >> raw.txt

echo "</SECTIONS>" >> raw.txt

xmllint --format raw.txt > $2 && rm raw.txt
