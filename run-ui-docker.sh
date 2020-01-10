docker image build -t t2mui ui-server
docker run -d -p 80:80 -e SPACY_PORT=8001 -e COGCOMP_PORT=8002 --name t2mui t2mui