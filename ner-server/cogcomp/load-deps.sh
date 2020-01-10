#!/bin/sh
curl -L0 http://cogcomp.seas.upenn.edu/software/illinois-ner-3.0.23.zip > ner.zip
unzip -q ner.zip
rm ner.zip
mkdir lib
mv illinois-ner/lib/* lib
mv illinois-ner/dist/illinois-ner-3.0.23.jar lib/illinois-ner-3.0.23.jar
rm -rf illinois-ner
