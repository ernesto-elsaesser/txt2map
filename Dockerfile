FROM python:3.8
RUN pip install requests spacy
WORKDIR /map2txt
ADD server.py /map2txt/server.py
ADD parser.py /map2txt/parser.py
ADD geonames.py /map2txt/geonames.py
ADD osm.py /map2txt/osm.py
ADD data /map2txt/data
EXPOSE 80
ENTRYPOINT ["python", "server.py"]