import re
from dataclasses import dataclass
from urllib import parse

import tantivy

from doc_searcher.web_service.query_parser import PreprocessedQuery

INDEXED_FIELDS = ["url", "title", "content", "code", "links_texts"]


@dataclass
class SearchItem:
    doc_id: int
    doc: tantivy.Document
    raw_score: float
    snippet: str


@dataclass
class SearchRenderItem:
    url: str
    title: str
    snippet: str


def load_index(path: str):
    index = tantivy.Index.open(path)
    index.config_reader(reload_policy="manual", num_warmers=3)


def raw_search(index: tantivy.Index, query: PreprocessedQuery, top_n: int):
    searcher = index.searcher()

    try:
        parsed_query = index.parse_query(query.expanded_query, default_field_names=INDEXED_FIELDS)

        snippet_generator_content = tantivy.SnippetGenerator.create(
            searcher, parsed_query, index.schema, "content"
        )
        snippet_generator_code = tantivy.SnippetGenerator.create(
            searcher, parsed_query, index.schema, "code"
        )
        result = searcher.search(
            parsed_query,
            limit=top_n,
        ).hits
        for score, doc_id in result:
            doc = searcher.doc(doc_id)
            snippet = (
                snippet_generator_content.snippet_from_doc(doc).to_html()
                or snippet_generator_code.snippet_from_doc(doc).to_html()
            )
            yield SearchItem(doc_id, doc, score, snippet)
    except Exception as e:
        print(f"Error during search: {e}, query {query}")


def doc_to_render(doc: tantivy.Document, snippet: str):
    return SearchRenderItem(url=doc["url"][0], title=doc["title"][0], snippet=snippet)
