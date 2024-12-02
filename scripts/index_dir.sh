#!/bin/bash
IN_DIR=${1:-data}
INDEX_DIR=${2:-index}
python -m doc_searcher.index -p $IN_DIR -i $INDEX_DIR -op 10000