FROM python:3.8-slim
RUN pip install flask requests spacy pylev unidecode
WORKDIR /map2txt
ADD ./geoparser /map2txt/geoparser
ADD ./webserver /map2txt/webserver
RUN ["python", "-m", "spacy", "download", "en_core_web_sm"]
RUN ["python", "-m", "spacy", "download", "en_core_web_lg"]
EXPOSE 80
ENTRYPOINT ["python", "-m", "webserver"]