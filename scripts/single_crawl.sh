#!/bin/bash
DOMAIN=$1
OUT_DIR=${2:-data}
python -m doc_searcher.crawl -d $DOMAIN -p $OUT_DIR -mp 30000 