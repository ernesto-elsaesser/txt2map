#!/bin/sh
docker image build -t t2mcc ner-server/cogcomp
docker stop t2mcc
docker rm t2mcc
docker run -d -p 8002:80 --name t2mcc t2mcc
