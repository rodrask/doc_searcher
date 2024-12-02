import argparse
import json
import pathlib
from collections import Counter
from datetime import datetime

import tantivy
from robyn import Robyn
from robyn.templating import JinjaTemplate

from doc_searcher.web_service.search_functions import (
    doc_to_render,
    normalize_query,
    raw_search,
)
from doc_searcher.web_service.stat import ServiceStats


def init_jinja():
    current_file_path = pathlib.Path(__file__).parent.resolve()
    return JinjaTemplate(current_file_path / "web_service" / "templates")


JINJA_TEMPLATE = init_jinja()

app = Robyn(__file__)


@app.get("/")
async def index(request):
    return JINJA_TEMPLATE.render_template("index.html")


@app.get("/search")
async def search(request, global_dependencies):
    start = datetime.now()

    raw_query = request.query_params.get("q", "")
    if not raw_query:
        return JINJA_TEMPLATE.render_template(
            "search.html", {"error": "Query parameter 'q' is required"}
        )
    top_n = int(request.query_params.get("n") or 10)
    query = normalize_query(raw_query)

    raw_results = list(raw_search(global_dependencies["index"], query, top_n))
    results = [doc_to_render(r.doc, r.snippet) for r in raw_results]
    finsh = datetime.now()
    latency_ms = (finsh - start).microseconds / 1000

    global_dependencies["stat"].update_with_serp([d.url for d in results], latency_ms)
    return JINJA_TEMPLATE.render_template(
        "search.html", query=query.query, results=results, latency=latency_ms
    )


@app.post("/click")
async def click(request, global_dependencies):
    url = request.json().get("url", "")
    if not url:
        print("No url in request")
        return
    global_dependencies["stat"].update_with_click(url)
    return


@app.get("/stat")
async def stat(request, global_dependencies):
    stat = global_dependencies["stat"]
    return JINJA_TEMPLATE.render_template("stat.html", stat=stat)


def init_stats(stat_path):
    if not stat_path.exists():
        return ServiceStats(0, [], [])

    with open(stat_path) as f:
        index_stat = Counter(json.load(f))

    n_docs = sum(index_stat.values())
    n_domains = len(index_stat)
    top3_domains = index_stat.most_common(3)
    return ServiceStats(n_docs, n_domains, top3_domains)


parser = argparse.ArgumentParser()
parser.add_argument("-i", "--index", help="Path to the index file")
parser.add_argument("-p", "--port", type=int, default=8080, help="Web service port")


def main():
    args = parser.parse_args()
    index = tantivy.Index.open(args.index)
    stat = init_stats(pathlib.Path(args.index) / "index_stat.json")

    app.inject_global(stat=stat, index=index)
    app.start(port=args.port)


if __name__ == "__main__":
    main()
