FROM python:3.8-slim
RUN pip install flask requests spacy pylev unidecode
WORKDIR /map2txt
ADD ./geoparser /map2txt/geoparser
ADD ./nlpserver /map2txt/nlpserver
ADD ./uiserver /map2txt/uiserver
ADD ./start-servers.sh /map2txt/start.sh
RUN ["python", "-m", "spacy", "download", "en_core_web_sm"]
RUN ["python", "-m", "spacy", "download", "en_core_web_lg"]
EXPOSE 80
ENTRYPOINT ["/map2txt/start.sh"]