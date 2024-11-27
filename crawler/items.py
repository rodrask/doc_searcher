from dataclasses import dataclass
from typing import Optional


@dataclass
class CrawledPageItem:
    date: Optional[int]
    url: str
    title: str
    content: str
    code_snippets: list[str]
    out_links: dict[str,list[str]]
