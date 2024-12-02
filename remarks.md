### General Remarks

The task as a whole is divided into three parts:

- Crawler
- Indexer
- Web interface for search and ranking

There is no actual interaction between them, and three separate modules can be used, which interact through the created files.

#### Crawler

I chose Scrapy as the library for the crawler because it is the most well-known, has a large amount of documentation and examples, and is quite easy to use. It also has the ability to add proxy servers for bypassing.

One crawler process handles one domain, and parallelism is achieved using the `parallel` utility, which runs multiple processes for different domains simultaneously.

What was used during crawling:

- The domain was checked, and a starting URL was selected, preferably with words like `doc`, `docs`, `guide`, and similar in the domain or path.
- During domain traversal, URLs with words like `doc`, `docs`, `guide`, and similar in the path or domain were prioritized.
- The `trafilatura` library was used to extract the main part of the document.
- Multiple processes were launched for parallel collection using the `gnu-parallel` utility.

Problems encountered:

- Different sites have different types of links; some links can be relative, while others are absolute. The HTML itself was not always valid.

#### Indexer

I chose Tantivy as the library for the index because it seemed simpler and faster to use compared to others, although it lacks features, and the Python library is poorly documented.

The crawler collected more than 10k pages, so it was necessary to choose which pages to index. For this, I used a simple heuristic and took the sum of the normalized average document length, the number of links to it, and similar factors as the importance.

Fields created in the index and used for search are:
- URL
- Title
- Content
- Code on the page (from the `<code>` tag)
- Text from links pointing to this page

All processing was done using an in-memory SQLite3 database.

#### Web Search

For better quality, the following techniques were used:
- The query was split into tokens and bigrams, which were searched together.
- Boost was added for the fields `url`, `title`, and `code`.