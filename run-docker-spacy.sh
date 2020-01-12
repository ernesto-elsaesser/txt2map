#!/bin/sh
docker image build -t t2msp ner-server/spacy
docker stop t2msp
docker rm t2msp
docker run -d -p 8001:80 --name t2msp t2msp
