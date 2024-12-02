import re
from collections import defaultdict
from dataclasses import dataclass
from urllib import parse

from doc_searcher.web_service.query_dicts import (
    ALL_CODE_TERMS,
    LANGUAGE_DICT,
    UNIQUE_KEYWORDS,
)


@dataclass
class PreprocessedQuery:
    in_query: str
    expanded_query: str
    query_len: int

    def bigrams(self):
        return zip(self.query_terms, self.query_terms[1:])


nonwords = re.compile("[\\W_]+")
spaces = re.compile("\\s+")
URL_BOOST = 3
TITLE_BOOST = 2
CODE_BOOST = 1.2


def site_expanders(sites):
    for site in sites:
        yield f"url:{site}^{URL_BOOST}"
        yield f"title:{site}^{TITLE_BOOST}"


def expand(terms, subterms_lst, expansions):
    result = []
    for subterms, expansion, in zip(subterms_lst, expansions):        
        result.extend(subterms)
        if expansion is not None:
            result.extend(expansion)
    return " ".join(result)


def generate_subterms(term):
    subparts = re.split(nonwords, term, 3)
    if len(subparts) > 1:
        yield "".join(subparts)
        for subpart in subparts:
            if len(subpart) >1:
                yield subpart
    else:
        yield term
        


def preprocess_query(raw_query: str):
    print(f"Preprocessing query: {raw_query}")
    raw_query = parse.unquote(raw_query.replace("+", " "))
    print(f"Unquoted: {raw_query}")
    terms = re.sub(spaces, " ", raw_query).lower().split()
    expansions = [None] * len(terms)
    term_sites = set()
    subterms = [list() for _ in range(len(terms))]
    for pos, term in enumerate(terms):
        term_sites.clear()
        for sub_term in generate_subterms(term):
            subterms[pos].append(sub_term)
            term_sites.update(LANGUAGE_DICT.get(sub_term, []))
        if term_sites:
            expansions[pos] = list(site_expanders(term_sites))
            continue

        code_expand = []
        if term in ALL_CODE_TERMS:
            code_expand.append(f"code:{term}^{CODE_BOOST}")

        unique_sites = UNIQUE_KEYWORDS.get(term, [])
        if unique_sites:
            for site in unique_sites:
                code_expand.append(f"url:{site}^{URL_BOOST}")
                code_expand.append(f"title:{site}^{TITLE_BOOST}")

        expansions[pos] = code_expand

    expanded_query = expand(terms, subterms, expansions)
    print(f"Expanded query: {expanded_query}")
    return PreprocessedQuery(raw_query, expanded_query, len(terms))
