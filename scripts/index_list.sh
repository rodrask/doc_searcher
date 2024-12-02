#!/bin/bash
IN_DIR_FILE=${1}
INDEX_DIR=${2:-index}
for IN_DIR in $(cat $IN_DIR_FILE)
    do
        python -m doc_searcher.index -p $IN_DIR -i $INDEX_DIR -op 10000
    done