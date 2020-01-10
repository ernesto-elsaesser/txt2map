FROM python:3.8-slim
RUN pip install flask requests spacy google-cloud-language pylev unidecode geojson_utils
RUN ["python", "-m", "spacy", "download", "en_core_web_sm"]
# RUN ["python", "-m", "spacy", "download", "en_core_web_lg"]
WORKDIR /map2txt
ADD ./geoparser /map2txt/annotation
ADD ./geoparser /map2txt/geoparser
ADD ./start-cogcomp-server.sh /map2txt/ner.sh
ADD ./start-cogcomp-ui-server.sh /map2txt/ui.sh
EXPOSE 80
ENTRYPOINT ["cd /map2txt; ./ner.sh & ./ui.sh"]