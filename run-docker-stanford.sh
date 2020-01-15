#!/bin/sh
docker image build -t t2msf ner-server/stanford
docker stop t2msf
docker rm t2msf
docker run -d -p 8003:80 --name t2msf t2msf
