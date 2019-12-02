FROM python:3.8-slim
RUN apt-get update && apt-get install -y libgeos-dev
RUN pip install requests spacy geojson_utils osm2geojson
WORKDIR /map2txt
ADD ./geoparser /map2txt/geoparser
ADD ./webserver /map2txt/webserver
RUN ["python", "-m", "spacy", "download", "en_core_web_sm"]
EXPOSE 80
ENTRYPOINT ["python", "-m", "webserver"]