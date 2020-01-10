FROM python:3.8-slim

RUN pip install flask requests spacy google-cloud-language pylev unidecode geojson_utils
RUN python -m spacy download en_core_web_sm
RUN python -m spacy download en_core_web_lg
 
WORKDIR /txt2map
ADD ./annotation annotation
ADD ./geoparser geoparser
ADD ./server server
 
# spacy
ADD ./start-spacy-server.sh ner.sh
ADD ./start-spacy-ui-server.sh ui.sh
 
# cogcomp
# RUN apt-get update
# RUN apt-get install -y openjdk-8-jdk curl unzip
# RUN curl -L0 http://cogcomp.seas.upenn.edu/software/illinois-ner-3.0.23.zip > ner.zip
# RUN unzip -q ner.zip
# RUN rm ner.zip
# ADD ./start-cogcomp-server.sh ner.sh
# ADD ./start-cogcomp-ui-server.sh ui.sh
 
EXPOSE 80
ENTRYPOINT ./ner.sh