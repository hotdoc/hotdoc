#! /usr/bin/env sh

echo "<SECTIONS>" > raw.txt

cat $1 | grep -v "^\s*#\|<INCLUDE>\|</INCLUDE>\|<FILE>\|</FILE>\|<SUBSECTION.*>\|</SUBSECTION>" | sed "s/<TITLE>/<SYMBOL>/g" | sed "s/<\/TITLE>/<\/SYMBOL>\n<SYMBOLS>/" | sed "s/<\/SECTION>/<\/SYMBOLS>\n<\/SECTION>/g" | awk '!/^\s*(<|$)/{print "<SYMBOL>"$0"</SYMBOL>";next}1' >> raw.txt

echo "</SECTIONS>" >> raw.txt

xmllint --format raw.txt > $2 && rm raw.txt
