import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

DOCS_KEYWORDS_LIST = [
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
    "faq",
]
DOCS_KEYWORDS = set(DOCS_KEYWORDS_LIST)


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
    resolved_domain: str
    code: int
    message: str
    start_url: str

    def is_ok(self) -> bool:
        return self.code == 200


def drop_www(domain: str) -> str:
    return domain[4:] if domain.startswith("www.") else domain


def probe_domain(domain: str) -> ProbeResult:
    try:
        result = requests.get(f"https://{domain}")
        resolved = urlparse(result.url)
        resolved_domain = drop_www(resolved.netloc)

        scheme = resolved.scheme
        start_url = select_start_url(scheme, resolved_domain) or result.url

        return ProbeResult(
            resolved_domain=resolved_domain,
            code=result.status_code,
            message=result.reason,
            start_url=start_url,
        )
    except requests.exceptions.RequestException as e:
        print(e)
        return ProbeResult(domain, -1, e.strerror, f"https://{domain}")


def select_start_url(scheme: str, domain: str):
    for candidate_url in candidates(scheme, domain):
        try:
            result = requests.get(
                candidate_url,
            )
            if result.status_code == 200:
                return result.url
        except requests.exceptions.RequestException:
            continue
        time.sleep(0.1)

    return None


def candidates(scheme: str, domain: str):
    for word in DOCS_KEYWORDS_LIST:
        yield f"{scheme}://{word}.{domain}"
        yield f"{scheme}://{domain}/{word}"
