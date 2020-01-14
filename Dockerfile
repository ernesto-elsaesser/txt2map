FROM python:3.8-slim

RUN pip install flask requests google-cloud-language pylev unidecode geojson_utils
 
WORKDIR /t2mui
ADD ./annotation annotation
ADD ./geoparser geoparser
ADD ./ui-server server

EXPOSE 80
ENTRYPOINT python3 -m server 80