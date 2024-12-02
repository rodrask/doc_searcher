# Deployment Instructions

## On Local Machine

1. Clone the repository:
    ```sh
    git clone git@github.com:rodrask/doc_searcher.git
    ```

2. Install `uv`:
    ```sh
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

3. Build the project:
    ```sh
    uv build
    ```

## Deploy on Host

1. Install required packages:
    ```sh
    sudo apt install -y python3.11-venv parallel
    ```

2. Create and navigate to the project directory:
    ```sh
    mkdir srch && cd srch
    mkdir scripts
    ```

3. Create a virtual environment:
    ```sh
    python3 -m venv venv
    ```

4. Copy the built wheel file to the host:
    ```sh
    scp dist/test_doc_searcher-0.1.0-py3-none-any.whl user@host
    ```

5. Copy the scripts to the host:
    ```sh
    scp scripts/*.sh user@host:srch/scripts
    ```

6. Activate the virtual environment:
    ```sh
    source venv/bin/activate
    ```

7. Install the package:
    ```sh
    pip install -I -U --force-reinstall test_doc_searcher-0.1.0-py3-none-any.whl
    ```

## Usage

### Crawler

- Crawl a single domain:
    ```sh
    python -m doc_searcher.crawl -d $DOMAIN -p $OUT_DIR -mp 15000
    ```

- Crawl domains from a file in parallel:
    ```sh
    cat $FILE | parallel -j$N_JOBS python -m doc_searcher.crawl -p $OUTPUT_DIR -d {}
    ```

The crawler creates a `domain.crawl.gz` file with parsed pages.

### Indexer

- Index files from a list:
    ```sh
    for IN_FILE in $(cat $IN_DIR_FILE)
    do
        python -m doc_searcher.index -p $IN_FILE -i $INDEX_DIR -op 10000
    done
    ```

- Index all files in subdirectories:
    ```sh
    python -m doc_searcher.index -p $IN_DIR -i $INDEX_DIR -op 10000
    ```

The indexer creates or updates the Tantivy index and saves some stats in `index-stats.json`.

### Run Web Search

- Start the web search service:
    ```sh
    python -m doc_searcher.web -i $INDEX_DIR -p $PORT
    ```