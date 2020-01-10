docker image build -t t2msp ner-server/spacy
docker run -d -p 8001:80 --name t2msp t2msp