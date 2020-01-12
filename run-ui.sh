#!/bin/sh
export SPACY_URL=http://localhost:8001
export COGCOMP_URL=http://localhost:8002
python3 -m ui-server 80
