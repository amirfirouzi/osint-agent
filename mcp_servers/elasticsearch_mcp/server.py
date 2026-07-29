# mcp_servers/elasticsearch_mcp/server.py
"""
Elasticsearch MCP Server
Wraps your local ES cluster with domain-specific threat intelligence tools.
The agent uses this to correlate external signals against known indicators
and to persist intelligence reports.
"""

import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from fastmcp import FastMCP
import os
os.environ["FASTMCP_LOG_LEVEL"] = "ERROR"

load_dotenv()

mcp = FastMCP("elasticsearch-mcp")

es = Elasticsearch(
    os.getenv("ES_HOST", "http://localhost:9200"),
    basic_auth=(
        os.getenv("ES_USERNAME", "elastic"),
        os.getenv("ES_PASSWORD", "osint_password")
    )
)


@mcp.tool()
def search_threat_indicators(
    query: str,
    indicator_type: str = "all",
    severity: str = "all",
    limit: int = 5
) -> dict:
    """
    Search the local threat intelligence database for known indicators.

    Use this to check if external signals match known threats in our
    knowledge base — CVEs, threat actors, campaigns, malicious domains/IPs.

    Args:
        query: Search terms e.g. 'openssl tls' or 'APT supply chain'
        indicator_type: Filter by type: 'cve', 'actor', 'campaign', 'domain', 'ip',
                        'supply_chain', or 'all'
        severity: Filter by severity: 'critical', 'high', 'medium', 'low', or 'all'
        limit: Max results to return

    Returns:
        Dict with matching indicators from our knowledge base
    """
    must_clauses = [
        {
            "multi_match": {
                "query": query,
                "fields": ["description^2", "tags^2", "value", "indicator_id"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        }
    ]

    filter_clauses = []
    if indicator_type != "all":
        filter_clauses.append({"term": {"type": indicator_type}})
    if severity != "all":
        filter_clauses.append({"term": {"severity": severity}})

    es_query = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses
            }
        },
        "size": limit,
        "sort": [
            {"severity": {"order": "asc"}},  # critical first
            "_score"
        ]
    }

    try:
        result = es.search(index="threat_indicators", body=es_query)
    except Exception as e:
        return {"error": str(e), "matches": []}

    hits = result["hits"]["hits"]
    matches = []
    for hit in hits:
        src = hit["_source"]
        matches.append({
            "indicator_id": src.get("indicator_id"),
            "type":         src.get("type"),
            "value":        src.get("value"),
            "description":  src.get("description"),
            "severity":     src.get("severity"),
            "tags":         src.get("tags", []),
            "related_to":   src.get("related_to", []),
            "last_seen":    src.get("last_seen"),
            "relevance_score": round(hit["_score"], 2),
        })

    return {
        "query":        query,
        "total_matches": result["hits"]["total"]["value"],
        "returned":     len(matches),
        "matches":      matches
    }


@mcp.tool()
def get_indicator_by_id(indicator_id: str) -> dict:
    """
    Retrieve a specific threat indicator by its ID.

    Use this to get full details about a known indicator including
    all related indicators and metadata.

    Args:
        indicator_id: The indicator ID e.g. 'CVE-2024-0001' or 'ACTOR-APT-PHANTOM'

    Returns:
        Full indicator record with all fields and relationships
    """
    try:
        result = es.get(index="threat_indicators", id=indicator_id)
        return result["_source"]
    except Exception as e:
        return {"error": str(e), "indicator_id": indicator_id}


@mcp.tool()
def get_related_indicators(indicator_id: str) -> dict:
    """
    Get all indicators related to a specific indicator.

    Use this to understand the full context around a threat —
    what campaigns an actor is involved in, what CVEs a campaign exploits, etc.

    Args:
        indicator_id: The indicator to find relationships for

    Returns:
        Dict with the indicator and all its related indicators
    """
    try:
        # get the indicator itself
        base = es.get(index="threat_indicators", id=indicator_id)
        base_src = base["_source"]
        related_ids = base_src.get("related_to", [])

        if not related_ids:
            return {
                "indicator_id": indicator_id,
                "indicator":    base_src,
                "related":      []
            }

        # fetch all related indicators
        result = es.mget(
            index="threat_indicators",
            body={"ids": related_ids}
        )

        related = []
        for doc in result["docs"]:
            if doc.get("found"):
                src = doc["_source"]
                related.append({
                    "indicator_id": src.get("indicator_id"),
                    "type":         src.get("type"),
                    "value":        src.get("value"),
                    "severity":     src.get("severity"),
                    "description":  src.get("description")[:150],
                })

        return {
            "indicator_id": indicator_id,
            "indicator":    base_src,
            "related":      related
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def save_intelligence_report(
    title: str,
    summary: str,
    full_report: str,
    topic: str,
    sources_used: list,
    indicators_found: list,
    severity: str,
    tags: list
) -> dict:
    """
    Save a synthesized intelligence report to the knowledge base.

    Use this as the final step after gathering and analyzing signals
    from external sources. Always save reports so findings can be
    correlated in future investigations.

    Args:
        title: Concise report title e.g. 'OpenSSL CVE-2024-0001 Community Response Analysis'
        summary: 2-3 sentence executive summary of findings
        full_report: Complete report text with all findings and analysis
        topic: Primary topic keyword e.g. 'openssl', 'apt-phantom', 'supply-chain'
        sources_used: List of source names used e.g. ['hackernews', 'reddit', 'github']
        indicators_found: List of indicator IDs that matched e.g. ['CVE-2024-0001']
        severity: Overall severity assessment: 'critical', 'high', 'medium', 'low'
        tags: List of relevant tags for future retrieval

    Returns:
        Dict confirming the saved report with its ID
    """
    report_id = f"REPORT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:6].upper()}"

    doc = {
        "report_id":        report_id,
        "title":            title,
        "summary":          summary,
        "full_report":      full_report,
        "topic":            topic,
        "sources_used":     sources_used,
        "indicators_found": indicators_found,
        "severity":         severity,
        "created_at":       datetime.now(timezone.utc).isoformat(),
        "tags":             tags
    }

    try:
        es.index(index="intelligence_reports", id=report_id, document=doc)
        es.indices.refresh(index="intelligence_reports")
        return {
            "success":   True,
            "report_id": report_id,
            "message":   f"Report saved successfully as {report_id}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def get_recent_reports(topic: str = "", limit: int = 5) -> dict:
    """
    Retrieve recent intelligence reports from the knowledge base.

    Use this to check if we've already investigated a topic recently
    before starting a new investigation.

    Args:
        topic: Optional topic filter e.g. 'openssl'. Leave empty for all recent reports.
        limit: Max number of reports to return

    Returns:
        Dict with recent reports sorted by date
    """
    if topic:
        query = {
            "bool": {
                "should": [
                    {"match": {"topic": topic}},
                    {"match": {"tags": topic}},
                    {"match": {"title": topic}}
                ]
            }
        }
    else:
        query = {"match_all": {}}

    try:
        result = es.search(
            index="intelligence_reports",
            body={
                "query": query,
                "size":  limit,
                "sort":  [{"created_at": {"order": "desc"}}]
            }
        )

        reports = []
        for hit in result["hits"]["hits"]:
            src = hit["_source"]
            reports.append({
                "report_id":        src.get("report_id"),
                "title":            src.get("title"),
                "summary":          src.get("summary"),
                "severity":         src.get("severity"),
                "sources_used":     src.get("sources_used", []),
                "indicators_found": src.get("indicators_found", []),
                "created_at":       src.get("created_at"),
                "tags":             src.get("tags", []),
            })

        return {
            "total":   result["hits"]["total"]["value"],
            "reports": reports
        }

    except Exception as e:
        return {"error": str(e), "reports": []}


@mcp.tool()
def get_knowledge_base_stats() -> dict:
    """
    Get statistics about the current state of the knowledge base.

    Use this at the start of an investigation to understand what
    data is available for correlation.

    Returns:
        Dict with counts and breakdowns of stored intelligence
    """
    try:
        # count by type
        type_agg = es.search(
            index="threat_indicators",
            body={
                "size": 0,
                "aggs": {
                    "by_type":     {"terms": {"field": "type"}},
                    "by_severity": {"terms": {"field": "severity"}}
                }
            }
        )

        report_count = es.count(index="intelligence_reports")["count"]
        signal_count = es.count(index="raw_signals")["count"]

        type_buckets = type_agg["aggregations"]["by_type"]["buckets"]
        sev_buckets  = type_agg["aggregations"]["by_severity"]["buckets"]

        return {
            "total_indicators":  type_agg["hits"]["total"]["value"],
            "total_reports":     report_count,
            "total_raw_signals": signal_count,
            "indicators_by_type": {b["key"]: b["doc_count"] for b in type_buckets},
            "indicators_by_severity": {b["key"]: b["doc_count"] for b in sev_buckets},
        }

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print("Starting Elasticsearch MCP server...")
    mcp.run(transport="stdio")