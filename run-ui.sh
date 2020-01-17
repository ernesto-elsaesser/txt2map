#!/bin/sh
export SPACY_URL=http://localhost:8001
export COGCOMP_URL=http://localhost:8002
export STANFORD_URL=http://localhost:8003
python3 -m ui-server 80
