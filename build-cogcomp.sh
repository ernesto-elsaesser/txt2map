# NOTE:
# first download Illinois NER from http://cogcomp.seas.upenn.edu/software/illinois-ner-3.0.23.zip
# and copy everything from the lib and dist folders into nlptools/cogcomp/lib
javac -classpath "nlptools/cogcomp/lib/*" -d "nlptools/cogcomp" nlptools/cogcomp/CogCompServer.java