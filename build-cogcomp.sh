CC_DIR="annotation/cogcomp"
CC_LIB_DIR="$CC_DIR/lib"
mkdir tmp
cd tmp
curl http://cogcomp.seas.upenn.edu/software/illinois-ner-3.0.23.zip > ner.zip
unzip ner.zip
cd ..
mkdir $CC_LIB_DIR
mv tmp/illinois-ner/lib/* $CC_LIB_DIR
mv tmp/illinois-ner/dist/* $CC_LIB_DIR
rm -rf tmp
javac -classpath "$CC_LIB_DIR/*" -d "$CC_DIR" "$CC_DIR/CogCompServer.java"