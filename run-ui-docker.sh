#!/bin/sh
docker image build -t t2mui .
echo "Removing running container ..."
docker stop t2mui
docker rm t2mui
echo "Starting new container ..."
docker run -d -p 80:80 \
  -e SPACY_PORT=8001 \
  -e COGCOMP_PORT=8002 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/t2mui/creds.json \
  -v $GOOGLE_APPLICATION_CREDENTIALS:/t2mui/creds.json:ro \
  --name t2mui \
  t2mui
