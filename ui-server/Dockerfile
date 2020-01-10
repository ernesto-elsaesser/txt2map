FROM python:3.8-slim

RUN pip install flask requests spacy google-cloud-language pylev unidecode geojson_utils
RUN python -m spacy download en_core_web_sm
 
WORKDIR /t2m
ADD ../annotation annotation
ADD ../geoparser geoparser
ADD ./__main__.py server.py
ADD ./index.html index.html

EXPOSE 80
ENTRYPOINT python3 server.py 80