docker image build -t t2mcc ner-server/cogcomp
docker run -d -p 8002:80 --name t2mcc t2mcc