# mcp_servers/rss_mcp/server.py
"""
RSS MCP Server
Monitors threat intelligence RSS feeds from primary security sources.
No auth, no API keys, completely open.

Sources:
  - CISA Alerts        (US government advisories)
  - Krebs on Security  (investigative security journalism)
  - The Hacker News    (breaking security news)
  - Schneier on Security (expert analysis)
  - ESET Research      (malware / APT research)
  - Bleeping Computer  (ransomware, breaches, CVEs)
"""

import httpx
import feedparser
from datetime import datetime, timezone
from fastmcp import FastMCP
import os
os.environ["FASTMCP_LOG_LEVEL"] = "ERROR"

mcp = FastMCP("rss-mcp")

# Primary threat intelligence feeds — all free, no auth
FEEDS = {
    "cisa_advisories": {
        "url":         "https://www.cisa.gov/cybersecurity-advisories/all.xml",
        "name":        "CISA Advisories",
        "description": "US Government cybersecurity advisories",
        "focus":       ["government", "advisories", "cve"]
    },
    "cisa_news": {
        "url":         "https://www.cisa.gov/news.xml",
        "name":        "CISA News",
        "description": "CISA news and announcements",
        "focus":       ["government", "policy", "announcements"]
    },
    "krebs": {
        "url":         "https://krebsonsecurity.com/feed/",
        "name":        "Krebs on Security",
        "description": "Investigative cybersecurity journalism",
        "focus":       ["breaches", "fraud", "cybercrime"]
    },
    "hackernews_sec": {
        "url":         "https://thehackernews.com/feeds/posts/default",
        "name":        "The Hacker News",
        "description": "Breaking cybersecurity news and CVEs",
        "focus":       ["cve", "breaches", "malware", "apt"]
    },
    "schneier": {
        "url":         "https://www.schneier.com/feed/atom/",
        "name":        "Schneier on Security",
        "description": "Expert security analysis and commentary",
        "focus":       ["analysis", "policy", "cryptography"]
    },
    "ncsc_uk": {
        "url":         "https://www.ncsc.gov.uk/api/1/services/v1/report-rss-feed.xml",
        "name":        "NCSC UK",
        "description": "UK National Cyber Security Centre advisories",
        "focus":       ["advisories", "uk", "government"]
    },
    "cve_mitre": {
        "url":         "https://cve.mitre.org/data/downloads/allitems-cvrf.xml",
        "name":        "MITRE CVE",
        "description": "CVE vulnerability database feed",
        "focus":       ["cve", "vulnerabilities"]
    },
}


def _parse_date(entry) -> str:
    """Extract published date from feed entry."""
    for field in ["published_parsed", "updated_parsed"]:
        val = getattr(entry, field, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def _clean_entry(entry, source_key: str) -> dict:
    """Extract relevant fields from a feed entry."""
    # strip HTML from summary
    import re
    summary = getattr(entry, "summary", "") or ""
    summary = re.sub(r"<[^>]+>", " ", summary).strip()
    summary = " ".join(summary.split())[:600]

    return {
        "id":           getattr(entry, "id", ""),
        "title":        getattr(entry, "title", ""),
        "url":          getattr(entry, "link", ""),
        "summary":      summary,
        "published_at": _parse_date(entry),
        "source":       source_key,
        "source_name":  FEEDS[source_key]["name"],
        "tags":         [t.term for t in getattr(entry, "tags", [])] if hasattr(entry, "tags") else [],
    }


def _fetch_feed(source_key: str) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    feed_config = FEEDS[source_key]
    try:
        resp = httpx.get(
            feed_config["url"],
            timeout=15,
            follow_redirects=True,
            headers={
                # use a browser UA — some feeds block obvious bot UAs
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
            }
        )
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)

        if not parsed.entries:
            # feedparser can also fetch directly as fallback
            parsed = feedparser.parse(feed_config["url"])

        return [_clean_entry(e, source_key) for e in parsed.entries]

    except Exception as e:
        return [{"error": f"{source_key}: {str(e)}", "source": source_key}]


@mcp.tool()
def search_security_feeds(
    query: str,
    sources: list = [],
    limit: int = 10
) -> dict:
    """
    Search across threat intelligence RSS feeds for a specific topic.

    Use this to find recent reporting from authoritative security sources
    about vulnerabilities, threat actors, malware, breaches, or campaigns.

    Args:
        query: Search terms e.g. 'OpenSSL' or 'ransomware supply chain'
               Matches against article title and summary (case-insensitive)
        sources: List of source keys to search. Leave empty for all sources.
                 Available: 'cisa', 'krebs', 'hackernews_sec', 'schneier',
                            'bleeping', 'eset'
        limit: Max total results to return across all sources

    Returns:
        Dict with matching articles sorted by date, most recent first
    """
    target_sources = sources if sources else list(FEEDS.keys())
    query_lower    = query.lower()
    query_terms    = query_lower.split()

    all_results = []

    for source_key in target_sources:
        if source_key not in FEEDS:
            continue

        entries = _fetch_feed(source_key)
        for entry in entries:
            if "error" in entry:
                continue

            # match if ANY query term appears in title or summary
            text = f"{entry['title']} {entry['summary']}".lower()
            if any(term in text for term in query_terms):
                all_results.append(entry)

    # sort by date, newest first
    all_results.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    all_results = all_results[:limit]

    return {
        "query":          query,
        "sources_checked": target_sources,
        "total_matches":  len(all_results),
        "results":        all_results
    }


@mcp.tool()
def get_latest_from_feed(
    source: str = "cisa",
    limit: int = 10
) -> dict:
    """
    Get the latest articles from a specific security feed.

    Use this to get a pulse on what a specific source is currently
    reporting, without a search term.

    Args:
        source: Feed key — one of: 'cisa', 'krebs', 'hackernews_sec',
                'schneier', 'bleeping', 'eset'
        limit: Number of latest articles to return (max 20)

    Returns:
        Dict with latest articles from that source
    """
    if source not in FEEDS:
        return {
            "error":     f"Unknown source '{source}'",
            "available": list(FEEDS.keys())
        }

    limit   = min(limit, 20)
    entries = _fetch_feed(source)
    valid   = [e for e in entries if "error" not in e][:limit]

    return {
        "source":      source,
        "source_name": FEEDS[source]["name"],
        "total":       len(valid),
        "results":     valid
    }


@mcp.tool()
def get_latest_across_all_feeds(limit_per_feed: int = 3) -> dict:
    """
    Get the latest articles from ALL security feeds simultaneously.

    Use this at the start of an investigation to get a broad current
    picture of what is happening across the security landscape.

    Args:
        limit_per_feed: How many recent articles to pull from each source

    Returns:
        Dict with recent articles from all sources, sorted by date
    """
    limit_per_feed = min(limit_per_feed, 5)
    all_results    = []

    for source_key in FEEDS:
        entries = _fetch_feed(source_key)
        valid   = [e for e in entries if "error" not in e][:limit_per_feed]
        all_results.extend(valid)

    all_results.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    return {
        "sources":       list(FEEDS.keys()),
        "total_fetched": len(all_results),
        "results":       all_results
    }


@mcp.tool()
def list_available_feeds() -> dict:
    """
    List all available threat intelligence RSS feeds.

    Use this to understand what sources are available before
    deciding which ones to search or monitor.

    Returns:
        Dict with feed names, descriptions, and focus areas
    """
    return {
        "feeds": [
            {
                "key":         key,
                "name":        config["name"],
                "description": config["description"],
                "focus":       config["focus"],
                "url":         config["url"],
            }
            for key, config in FEEDS.items()
        ]
    }


if __name__ == "__main__":
    print("Starting RSS MCP server...")
    mcp.run(transport="stdio")