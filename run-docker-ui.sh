#!/bin/sh
docker image build -t t2mui .
echo "Removing previous container ..."
docker stop t2mui
docker rm t2mui
echo "Starting new container ..."
docker run -d -p 80:80 \
  -e SPACY_URL=http://host.docker.internal:8001 \
  -e COGCOMP_URL=http://host.docker.internal:8002 \
  -e STANFORD_URL=http://localhost:8003 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/gac.json \
  -v $GOOGLE_APPLICATION_CREDENTIALS:/gac.json:ro \
  --name t2mui \
  t2mui
