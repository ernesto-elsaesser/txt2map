FROM python:3.8-slim
RUN pip install flask requests spacy google-cloud-language pylev unidecode geojson_utils
RUN ["python", "-m", "spacy", "download", "en_core_web_sm"]
# RUN ["python", "-m", "spacy", "download", "en_core_web_lg"]
WORKDIR /map2txt
ADD ./geoparser /map2txt/annotation
ADD ./geoparser /map2txt/geoparser
ADD ./server /map2txt/server
ADD ./build-cogcomp.sh /map2txt/build.sh
ADD ./start-servers.sh /map2txt/start.sh
RUN ["/map2txt/build.sh"]
EXPOSE 80
ENTRYPOINT ["/map2txt/start.sh"]