#!/bin/sh
curl -L0 https://nlp.stanford.edu/software/stanford-ner-2018-10-16.zip > ner.zip
unzip -q ner.zip
rm ner.zip
mkdir lib
mv stanford-ner-2018-10-16/stanford-ner.jar lib/stanford-ner.jar
mv stanford-ner-2018-10-16/classifiers/english.conll.4class.distsim.crf.ser.gz lib/english.conll.4class.distsim.crf.ser.gz
rm -rf stanford-ner-2018-10-16
curl -L0 https://repo1.maven.org/maven2/commons-io/commons-io/1.3.2/commons-io-1.3.2.jar > lib/commons-io.jar
