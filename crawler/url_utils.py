from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
import re

import requests

DOCS_KEYWORDS = {
    "doc",
    "docs",
    "document",
    "documentation",
    "documents",
    "manual",
    "manuals",
    "guide",
    "guides",
    "user_guide",
    "userguide",
    "user_guides",
    "userguides",
    "howto",
    "howtos",
    "how-to",
    "how-tos",
    "tutorial",
    "tutorials",
    "reference",
    "references",
    "knowledgebase",
    "faq"}


def underscore_domain(domain: str) -> str:
    return domain.lower().strip().replace("www.", "").replace(".", "_")


def priority_url_dummy(url) -> int:
    urlparts = urlparse(url)
    priority = 0

    domains_parts = urlparts.netloc.split(".")
    path_parts = re.split(r"\W+", urlparts.path)
    fragment_parts = re.split(r"\W+", urlparts.fragment)

    for part in domains_parts + path_parts + fragment_parts:
        if part in DOCS_KEYWORDS:
            priority += 1
    return priority


@dataclass
class ProbeResult:
    init_domain: str
    code: int
    message: str
    start_url: str

    def is_ok(self) -> bool:
        return self.code == 200

    def real_domain(self) -> str:
        return urlparse(self.start_url).netloc


def probe_domain(domain: str) -> ProbeResult:
    try:
        result = requests.get(f"http://{domain}")
        return ProbeResult(
            init_domain=domain,
            code=result.status_code,
            message=result.reason,
            start_url=result.url,
        )
    except requests.exceptions.RequestException as e:
        return ProbeResult(domain, -1, e.strerror, f"http://{domain}")
