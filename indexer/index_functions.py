from array import array
import json
import sqlean as sqlite3
from urllib.parse import urlparse
import tantivy

from crawler.url_utils import DOCS_KEYWORDS, priority_url_dummy


def create_in_memory_db():
    sqlite3.extensions.enable("stats")
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE documents (
            docid INTEGER PRIMARY KEY,
            date INTEGER,
            domain TEXT,
            url TEXT UNIQUE,
            term_in_url INTEGER,
            url_num_appears INTEGER,
            title TEXT,
            term_in_title INTEGER,
            content TEXT,
            content_len INTEGER,
            code TEXT,
            code_len INTEGER,
            out_links TEXT,
            out_links_len INTEGER
        )
    """)
    cursor.execute("CREATE INDEX idx_docid ON documents (docid)")

    cursor.execute("""
        CREATE TABLE links (
            docid INTEGER PRIMARY KEY,
            in_urls TEXT,
            in_texts TEXT
        )
    """)
    cursor.execute("CREATE INDEX idx_docid_links ON links (docid)")

    conn.commit()
    return conn


def insert_data_from_json(conn, json_line, do_commit=True):
    cursor = conn.cursor()

    url = json_line["url"]
    docid = hash(url)

    date = json_line.get("date", 0)
    title = (json_line.get("title") or "").strip()
    content = (json_line.get("content") or "").strip()
    code_snippets = json_line.get("code_snippets", [])
    out_links = list(set(hash(key) for key in json_line.get("out_links", {}).keys()))
    out_links_len = len(out_links)

    domain = urlparse(url).netloc
    term_in_url = priority_url_dummy(url)
    url_num_appears = 0
    term_in_title = (
        len(DOCS_KEYWORDS.intersection(set(title.lower().split()))) if title else 0
    )
    content_len = len(content.split()) if content else 0
    code = "\n".join([code_snippets.strip() for code_snippets in code_snippets])
    code_len = len(code.split())

    cursor.execute(
        """
        INSERT INTO documents (docid, url, domain, date, title, content, code, 
                               url_num_appears, term_in_url, term_in_title, 
                               content_len, code_len, out_links, out_links_len)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (docid) DO UPDATE SET url_num_appears = url_num_appears + 1
    """,
        (
            docid,
            url,
            domain,
            date,
            title,
            content,
            code,
            url_num_appears,
            term_in_url,
            term_in_title,
            content_len,
            code_len,
            json.dumps(out_links),
            out_links_len,
        ),
    )
    upsert_links_data(conn, url, json_line["out_links"])
    if do_commit:
        conn.commit()
    return docid


def upsert_links_data(cursor, url_from, links_dict):
    for url_to, links_texts in links_dict.items():
        docid = hash(url_to)
        in_urls = url_from
        in_texts = " ".join((set(links_texts)))
        cursor.execute(
            """
            INSERT INTO links (docid, in_urls, in_texts)
            VALUES (?, ?, ?)
            ON CONFLICT(docid) DO UPDATE SET
                in_texts=json_insert(in_texts, '$[#]', excluded.in_texts -> 0),
                in_urls=json_insert(in_urls, '$[#]', excluded.in_urls -> 0)
            """,
            (docid, json.dumps([in_urls]), json.dumps([in_texts])),
        )


def clean_db(conn):
    cursor = conn.cursor()
    cursor.execute("DROP VIEW IF EXISTS enriched_documents_normalized")
    cursor.execute("DELETE FROM documents")
    cursor.execute("DELETE FROM links")
    
    conn.commit()


def feature_extraction(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE VIEW enriched_documents_normalized AS 
        WITH enriched_documents AS (
            SELECT
                d.*,
                coalesce(l.in_urls, '[]') AS in_urls,
                coalesce(l.in_texts, '[]') AS in_texts,
                json_array_length(coalesce(l.in_urls, '[]')) AS num_in_urls
            FROM documents d
            LEFT JOIN links l ON d.docid = l.docid
        ),
        domain_stats AS (
            SELECT
                AVG(term_in_url) AS mean_term_in_url,
                stats_stddev(term_in_url) AS std_term_in_url,
                AVG(term_in_title) AS mean_term_in_title,
                stats_stddev(term_in_title) AS std_term_in_title,
                AVG(content_len) AS mean_content_len,
                stats_stddev(content_len) AS std_content_len,
                AVG(code_len) AS mean_code_len,
                stats_stddev(code_len) AS std_code_len,
                AVG(num_in_urls) AS mean_num_in_urls,
                stats_stddev(num_in_urls) AS std_num_in_urls
            FROM enriched_documents
        )
        SELECT
            d.*,
            (d.num_in_urls + 1) / (d.out_links_len+1) AS in_out_ratio,
            (d.term_in_url - ds.mean_term_in_url) / ds.std_term_in_url AS normalized_term_in_url,
            (d.term_in_title - ds.mean_term_in_title) / ds.std_term_in_title AS normalized_term_in_title,
            (d.content_len - ds.mean_content_len) / ds.std_content_len AS normalized_content_len,
            (d.code_len - ds.mean_code_len) / ds.std_code_len AS normalized_code_len,
            (d.num_in_urls - ds.mean_num_in_urls) / ds.std_num_in_urls AS normalized_num_in_urls
        FROM enriched_documents d
        JOIN domain_stats ds ON 1=1
        ORDER BY normalized_term_in_url+normalized_term_in_title+normalized_code_len+normalized_content_len DESC
        LIMIT 10000;
    """)
    conn.commit()


def build_schema():
    schema_builder = tantivy.SchemaBuilder()
    schema_builder.add_integer_field("doc_id", stored=True, indexed=False)
    schema_builder.add_date_field("date", stored=True, indexed=False)
    schema_builder.add_text_field(
        "url", stored=True, tokenizer_name="default"
    )
    schema_builder.add_text_field(
        "title", stored=True, tokenizer_name="en_stem"
    )
    schema_builder.add_text_field(
        "content", stored=True, tokenizer_name="en_stem"
    )
    schema_builder.add_text_field(
        "code", stored=True, tokenizer_name="default"
    )
    schema_builder.add_text_field(
        "links_texts", stored=False, tokenizer_name="en_stem"
    )
    schema_builder.add_bytes_field("features", stored=False, indexed=False, fast=True)
    schema = schema_builder.build()
    return schema


def init_tantify_index(path):
    schema = build_schema()
    index = tantivy.Index(schema=schema, path=str(path))
    return index


feature_keys = [
    "term_in_url",
    "term_in_title",
    "content_len",
    "code_len",
    "num_in_urls",
    "in_out_ratio",
] + [
    f"normalized_{feature}"
    for feature in [
        "term_in_url",
        "term_in_title",
        "content_len",
        "code_len",
        "num_in_urls",
    ]
]


def index_selected_docs(conn, index_writer):
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM enriched_documents_normalized")
    for row in cursor:
        feature_vector = [row[key] or 0 for key in feature_keys]
        feature_vector_bytes = array("f", feature_vector).tobytes()

        index_writer.add_document(
            tantivy.Document(
                doc_id=row["docid"],
                date=row["date"],
                url=row["url"],
                title=row["title"],
                content=row["content"],
                code=row["code"],
                links_texts=" ".join(row["in_texts"]),
                features=feature_vector_bytes,
            )
        )
    index_writer.commit()