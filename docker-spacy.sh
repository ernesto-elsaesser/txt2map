docker image build -t t2msp ner-server/spacy
docker image build -t t2mui server/ui
docker run -d -p 8001:80 --name t2msp t2msp
docker run -d -p 80:80 --name t2mui t2mui