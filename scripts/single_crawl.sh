#!/bin/bash
DOMAIN=$1
echo "Start crawling $DOMAIN " $(date +"%Y-%m-%d %H:%M:%S")
python crawl.py -p data -mp 30000 -d $DOMAIN
echo "Finish crawling $DOMAIN " $(date +"%Y-%m-%d %H:%M:%S")