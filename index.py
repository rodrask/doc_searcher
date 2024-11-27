import argparse
from datetime import datetime
import json
import pathlib
import gzip

import tantivy

from crawl import CRAWL_SUFFIX
from indexer.index_functions import create_in_memory_db, feature_extraction, index_selected_docs, init_tantify_index, insert_data_from_json, clean_db

parser = argparse.ArgumentParser()
parser.add_argument("-p", '--path', help="Base path to index the data")
parser.add_argument("-op", '--out_pages', type=int, default=10000, help="Max number of pages to output")
parser.add_argument("-i", '--index', help="Path to the index file")

def parse_gzip_file(file_path, conn):
    with gzip.open(file_path, 'rt') as file:
        for line in file:
            json_data = json.loads(line)
            insert_data_from_json(conn, json_data, do_commit=False)
        conn.commit()
    return conn

if __name__ == "__main__":
    args = parser.parse_args()
    crawled_files = pathlib.Path(args.path).rglob(f"*{CRAWL_SUFFIX}")
    conn = create_in_memory_db()
    
    index_path = pathlib.Path(args.index)
    if not index_path.exists():
        index_path.mkdir(parents=True)
        index = init_tantify_index(index_path)
    else:
        index = tantivy.Index.open(str(index_path.resolve()))
    writer = index.writer()
    for file in crawled_files:
        print(f"Start processing {file} at {datetime.now()}")
        parse_gzip_file(file, conn)
        feature_extraction(conn)
        index_selected_docs(conn, writer)
        # conn.execute(f"vacuum main into '{file.name}.sqlite'")
        clean_db(conn)
        print(f"Finished processing {file} at {datetime.now()}")
        