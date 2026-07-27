# test_elasticsearch.py

from dotenv import load_dotenv
import os
from elasticsearch import Elasticsearch

load_dotenv()

es = Elasticsearch(
    os.getenv("ES_HOST"),
    basic_auth=(os.getenv("ES_USERNAME"), os.getenv("ES_PASSWORD"))
)

# search for anything related to OpenSSL
result = es.search(
    index="threat_indicators",
    body={"query": {"match": {"description": "openssl"}}}
)

hits = result["hits"]["hits"]
print(f"Found {len(hits)} indicators matching 'openssl':\n")
for hit in hits:
    src = hit["_source"]
    print(f"  [{src['severity'].upper()}] {src['indicator_id']}: {src['description'][:80]}...")