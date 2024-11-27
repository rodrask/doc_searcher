from collections import defaultdict
import re
from typing import Any, Optional
import scrapy
from scrapy.spiders import CrawlSpider
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Response
from trafilatura import extract
from email.utils import parsedate_to_datetime

from crawler.items import CrawledPageItem
from w3lib.url import canonicalize_url

from crawler.url_utils import priority_url_dummy


class DomainSpider(CrawlSpider):
    name = "domain_spider"

    def create_link_extractor(self):
        extr = LinkExtractor(
            allow_domains=self.allowed_domains,
            canonicalize=True,
            unique=False,
            strip=True,
        )
        return extr

    def start_requests(self):
        self.link_extractor = self.create_link_extractor()
        self.state["pages"] = 0
        self.logger.info(f"Starting crawl for domain {self.domain} {self.allowed_domains} at {self.start_url}")
        yield scrapy.Request(url=self.start_url, callback=self.parse_page)

    def extract_code_snippets(self, response) -> list[str]:
        return [code.strip() for code in response.css("code::text").extract() if code.strip()]

    def extract_title(self, response) -> str:
        return response.css("title::text").extract_first().strip() or ""
    
    def validate_content_type(self, response) -> bool:
        return response.headers.get("Content-Type", b"").startswith(b"text/html") or \
            response.headers.get("Content-Type", b"").startswith(b"text/plain")

    def extract_main_content(self, response) -> str:
        if response.headers.get("Content-Type", b"").startswith(b"text/html"):
            return extract(response.css("body").extract_first())
        elif response.headers.get("Content-Type", b"").startswith(b"text/plain"):
            return response.text.strip()
        else:
            return ""

    def extract_date(self, response) -> Optional[int]:
        date = response.headers.get("Last-Modified", None)
        if not date:
            date = response.headers.get("Date", None)        
        if date:
            try:
                return int(parsedate_to_datetime(str(date)).timestamp())
            except Exception:
                return None
        return None

    def parse_page(self, response: Response) -> Any:
        if not self.validate_content_type(response):
            return
        url = canonicalize_url(response.url)
        title = self.extract_title(response)
        date = self.extract_date(response)

        code_snippets = self.extract_code_snippets(response)
        content = self.extract_main_content(response)

        links = self.link_extractor.extract_links(response)
        
        grouped_links = defaultdict(list)
        for link in links:
            link_text = re.sub(r'\s+', ' ', link.text).strip()
            if link.fragment.strip():
                link_text += " " + link.fragment.strip()
            grouped_links[link.url].append(link_text)

        yield CrawledPageItem(
            date=date,
            url=url,
            title=title,
            content=content,
            code_snippets=code_snippets,
            out_links=grouped_links,
        )

        self.check_for_stop()

        for link in grouped_links.keys():
            priority = priority_url_dummy(link)
            yield scrapy.Request(url=link, priority=priority, callback=self.parse_page)

    def check_for_stop(self):
        self.state["pages"] += 1
        if self.state["pages"] > self.max_pages:
            raise scrapy.exceptions.CloseSpider("Max pages reached")
