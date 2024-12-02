import argparse
from collections import Counter
import gzip
import json
import pathlib
from datetime import datetime

import tantivy

from doc_searcher.crawl import CRAWL_SUFFIX
from doc_searcher.indexer.index_functions import (
    clean_db,
    create_in_memory_db,
    generate_doc_table,
    index_selected_docs,
    init_tantify_index,
    insert_data_from_json,
)

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", help="Base path to index the data")
parser.add_argument(
    "-op", "--out_pages", type=int, default=10000, help="Max number of pages to output"
)
parser.add_argument("-i", "--index", help="Path to the index file")


def prepare_index(index_path):
    index_path = pathlib.Path(index_path)
    if not index_path.exists():
        index_path.mkdir(parents=True)
        index = init_tantify_index(index_path)
    else:
        index = tantivy.Index.open(str(index_path.resolve()))
    return index


def parse_gzip_file(file_path, conn):
    with gzip.open(file_path, "rt") as file:
        for line in file:
            json_data = json.loads(line)
            insert_data_from_json(conn, json_data, do_commit=False)
        conn.commit()
    return conn


def process_crawled_files(path, conn, writer, out_pages):
    if path.endswith(CRAWL_SUFFIX):
        crawled_files = [pathlib.Path(path)]
    else:    
        crawled_files = pathlib.Path(path).rglob(f"*{CRAWL_SUFFIX}")
    index_stat = Counter()
    for file in sorted(crawled_files):
        start = datetime.now()
        print(f"Start processing {file} at {start}")
        parse_gzip_file(file, conn)
        generate_doc_table(conn, n=out_pages)
        domain = file.stem.split(".")[0].replace("_", ".")
        index_stat[domain] = index_selected_docs(conn, writer)
        clean_db(conn)
        finish = datetime.now()
        print(
            f"Finished processing {file} at {finish} {(finish-start).seconds} seconds"
        )
    return index_stat


def update_index_stat(index_stat, index_path):
    if index_stat:
        if (index_path / "index_stat.json").exists():
            print("Updating index_stat")
            index_stat.update(json.load(open(index_path / "index_stat.json")))
        json.dump(index_stat, open(index_path / "index_stat.json", "w"))


def main():
    args = parser.parse_args()
    index_path = pathlib.Path(args.index)

    conn = create_in_memory_db()

    index = prepare_index(index_path)
    writer = index.writer()

    index_stat = process_crawled_files(
        args.path, conn, writer, args.out_pages
    )

    writer.wait_merging_threads()

    update_index_stat(index_stat, index_path)


if __name__ == "__main__":
    main()
