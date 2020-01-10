FROM python:3.8-slim
RUN pip install flask requests spacy google-cloud-language pylev unidecode geojson_utils
RUN ["python", "-m", "spacy", "download", "en_core_web_sm"]
# RUN ["python", "-m", "spacy", "download", "en_core_web_lg"]
WORKDIR /txt2map
ADD ./geoparser /txt2map/annotation
ADD ./geoparser /txt2map/geoparser
ADD ./illinois-ner /txt2map/illinois-ner
ADD ./start-cogcomp-server.sh /txt2map/ner.sh
ADD ./start-cogcomp-ui-server.sh /txt2map/ui.sh
EXPOSE 80
ENTRYPOINT ["cd /txt2map; ./ner.sh & ./ui.sh"]