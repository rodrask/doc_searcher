import re
from dataclasses import dataclass
from urllib import parse

import tantivy

INDEXED_FIELDS = ["url", "title", "content", "code", "links_texts"]
FIELDS_BOOST = [3, 1, 1, 0.5, 0.5]
PHRASE_BOOST = 1.5


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


@dataclass
class PreprocessedQuery:
    query: str
    query_terms: list[str]
    query_len: int
    is_phrase: bool

    def bigrams(self):
        return zip(self.query_terms, self.query_terms[1:])


def is_phrase_query(query: str):
    return query[0] == '"' and query[-1] == '"'


nonwords = re.compile("[\W_]+")
spaces = re.compile("\s+")


def normalize_query(raw_query: str):
    raw_query = parse.unquote(raw_query.replace("+", " ")).strip()
    is_phrase = is_phrase_query(raw_query)
    terms = re.sub(spaces, " ", re.sub(nonwords, " ", raw_query)).strip().split()
    return PreprocessedQuery(raw_query, terms, len(terms), is_phrase)


def parse_query(index_schema: tantivy.Schema, query: PreprocessedQuery):
    all_queries = []
    for field, boost in zip(INDEXED_FIELDS, FIELDS_BOOST):
        field_term_queries = []
        if query.is_phrase:
            slop = 1 if query.query_len < 3 else 2
            field_term_queries.append(
                tantivy.Query.phrase_query(index_schema, field, query.query_terms, slop)
            )
        else:
            for term in query.query_terms:
                field_term_queries.append(
                    tantivy.Query.term_query(index_schema, field, term)
                )
        field_query = tantivy.Query.boost_query(
            tantivy.Query.boolean_query(
                [(tantivy.Occur.Should, q) for q in field_term_queries]
            ),
            boost
        )

        all_queries.append((tantivy.Occur.Should, field_query))
    return tantivy.Query.boolean_query(all_queries)


def load_index(path: str):
    index = tantivy.Index.open(path)
    index.config_reader(reload_policy="manual", num_warmers=3)


def raw_search(index: tantivy.Index, query: PreprocessedQuery, top_n: int):
    searcher = index.searcher()

    parsed_query = index.parse_query(query.query, default_field_names=INDEXED_FIELDS)

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


def doc_to_render(doc: tantivy.Document, snippet: str):
    return SearchRenderItem(url=doc["url"][0], title=doc["title"][0], snippet=snippet)
