export SPACY_PORT=8001
export COGCOMP_PORT=8002
docker image build -t t2mui ui-server
docker run -d -p 80:80 --name t2mui t2mui