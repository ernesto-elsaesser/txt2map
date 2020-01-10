if [[ ! -e "illinois-ner" ]]; then
  curl -L0 http://cogcomp.seas.upenn.edu/software/illinois-ner-3.0.23.zip > ner.zip
  unzip ner.zip
  rm ner.zip
fi
CP="annotation:illinois-ner/lib/*:illinois-ner/dist/*"
javac -classpath "$CP" -d "annotation" "annotation/CogCompServer.java"