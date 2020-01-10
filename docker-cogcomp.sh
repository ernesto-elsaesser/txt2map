docker image build -t t2mcc ner-server/cogcomp
docker image build -t t2mui server/ui
docker run -d -p 8002:80 --name t2mcc t2mcc
docker run -d -p 80:80 --name t2mui t2mui