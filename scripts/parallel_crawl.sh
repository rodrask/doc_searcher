#!/bin/bash
FILE=$1
OUTPUT_DIR=${2:-data}
N_JOBS=${3:-1}
echo "Crawling $FILE with $N_JOBS jobs"
cat $FILE |  parallel -j$N_JOBS python -m doc_searcher.crawl -p $OUTPUT_DIR -d {}