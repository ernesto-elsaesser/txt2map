if [[ ! -e "illinois-ner" ]]; then
  echo "Downloading Illinois NER (~300MB) ..."
  curl -L0 http://cogcomp.seas.upenn.edu/software/illinois-ner-3.0.23.zip > ner.zip
  unzip -q ner.zip
  rm ner.zip
fi
CP="server:illinois-ner/lib/*:illinois-ner/dist/*"
javac -classpath "$CP" -d "server" "server/CogCompServer.java"
java -Xmx4g -classpath "$CP" CogCompServer 8002