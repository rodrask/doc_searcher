#!/bin/bash
INDEX_DIR=$1
PORT=${2:-8080}

python -m doc_searcher.web -i $INDEX_DIR -p $PORT