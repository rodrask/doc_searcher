#!/bin/bash
FILE=$1
N_JOBS=${2:-1}
echo "Crawling $FILE with $N_JOBS jobs"
cat $FILE |  parallel -j$N_JOBS python crawl.py -p data -mp 30000 -d {}