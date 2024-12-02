import argparse
import os
from datetime import datetime
from pathlib import Path

from scrapy.crawler import CrawlerProcess

from doc_searcher.crawler.domain_spider import DomainSpider
from doc_searcher.crawler.url_utils import probe_domain, underscore_domain

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--path", help="Base path to store the data")
parser.add_argument("-d", "--domain", help="Domain to scan")
parser.add_argument(
    "-mp",
    "--max_pages",
    type=int,
    default=25000,
    help="Max number of pages to download",
)

CRAWL_SUFFIX = ".crawl.gz"


def get_output_path(base_path: str, domain: str) -> str:
    return os.path.join(
        base_path,
        underscore_domain(domain),
        f"{underscore_domain(domain)}{CRAWL_SUFFIX}",
    )


def get_log_file(base_path: str, domain: str) -> str:
    return os.path.join(
        base_path, underscore_domain(domain), f"{underscore_domain(domain)}.log"
    )


def get_job_path(base_path: str, domain: str) -> str:
    return os.path.join(base_path, underscore_domain(domain))


def setup_export_feed(settings, path, domain):
    out_file = get_output_path(path, domain)
    settings["FEEDS"] = {
        out_file: {
            "format": "jsonlines",
            "overwrite": False,
            "encoding": "utf-8",
            "store_empty": False,
            "postprocessing": ["scrapy.extensions.postprocessing.GzipPlugin"],
            "gzip_compresslevel": 5,
        }
    }
    return settings


def setup_settings(settings, path, domain):
    settings["LOG_FILE"] = get_log_file(path, domain)
    settings["JOBDIR"] = get_job_path(path, domain)
    settings["BOT_NAME"] = "scrapy_rodrask_bot"
    settings["TELNETCONSOLE_ENABLED"] = False
    settings["LOG_LEVEL"] = "INFO"
    return settings


def setup_crawler_process(path, domain, start_url, max_pages):
    settings = {}
    settings = setup_settings(settings, path, domain)
    settings = setup_export_feed(settings, path, domain)

    process = CrawlerProcess(settings=settings)
    process.crawl(
        DomainSpider,
        domain=domain,
        allowed_domains=[domain],
        start_url=start_url,
        max_pages=max_pages,
    )
    return process


def main():
    args = parser.parse_args()
    probe_result = probe_domain(args.domain)
    if not probe_result.is_ok():
        print(
            f"Error probing domain {args.domain}: {probe_result.code} {probe_result.message}"
        )
        return
    domain = probe_result.resolved_domain
    start_url = probe_result.start_url

    start = datetime.now()
    print(f"Starting crawl for domain {domain} at {start_url} at {start}")

    out_dir = Path(args.path) / underscore_domain(domain)
    if not out_dir.exists():
        out_dir.mkdir(parents=True)

    process = setup_crawler_process(args.path, domain, start_url, args.max_pages)
    process.start()
    finish = datetime.now()
    print(
        f"Finished crawl for domain {domain} at {finish} {(finish-start).seconds} seconds"
    )


if __name__ == "__main__":
    main()
