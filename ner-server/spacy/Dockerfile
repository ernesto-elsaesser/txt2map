FROM python:3.8-slim

RUN pip install flask spacy
RUN python -m spacy download en_core_web_lg
 
WORKDIR /t2msp
ADD ./server.py server.py
 
EXPOSE 80
ENTRYPOINT python3 server.py 80