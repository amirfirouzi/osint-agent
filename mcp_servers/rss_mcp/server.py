# mcp_servers/reddit_mcp/server.py
"""
Reddit MCP Server
Wraps Reddit's public JSON API — no auth needed for public subreddits.
Targets security-relevant subreddits for threat intelligence gathering.
"""

import httpx
from fastmcp import FastMCP

mcp = FastMCP("reddit-mcp")

REDDIT_BASE = "https://www.reddit.com"

# security-relevant subreddits for OSINT work
SECURITY_SUBREDDITS = [
    "netsec", "cybersecurity", "ReverseEngineering",
    "malware", "netsecstudents", "hacking", "AskNetsec",
    "blueteamsec", "threatintel"
]

HEADERS = {
    "User-Agent": "osint-agent/1.0 (research tool)"
}


def _clean_post(post: dict) -> dict:
    """Extract relevant fields from a Reddit post."""
    data = post.get("data", {})
    return {
        "id":          data.get("id"),
        "title":       data.get("title"),
        "subreddit":   data.get("subreddit"),
        "author":      data.get("author"),
        "url":         data.get("url"),
        "reddit_url":  f"https://reddit.com{data.get('permalink', '')}",
        "score":       data.get("score", 0),
        "comments":    data.get("num_comments", 0),
        "selftext":    (data.get("selftext", "") or "")[:500],
        "created_utc": data.get("created_utc"),
        "flair":       data.get("link_flair_text"),
    }


@mcp.tool()
def search_reddit(
    query: str,
    subreddit: str = "netsec+cybersecurity+blueteamsec",
    sort: str = "relevance",
    time_filter: str = "month",
    limit: int = 10
) -> dict:
    """
    Search Reddit posts across security subreddits.

    Use this to find community discussions about vulnerabilities,
    threat actors, malware, security tools, and incidents.

    Args:
        query: Search terms e.g. 'OpenSSL CVE' or 'supply chain npm malware'
        subreddit: Subreddit(s) to search. Use '+' to combine e.g. 'netsec+cybersecurity'.
                   Default covers main security subreddits.
        sort: Sort by 'relevance', 'hot', 'new', 'top'
        time_filter: Time range: 'hour', 'day', 'week', 'month', 'year', 'all'
        limit: Number of results (max 25)

    Returns:
        Dict with search results including titles, scores, and URLs
    """
    limit = min(limit, 25)
    url = f"{REDDIT_BASE}/r/{subreddit}/search.json"

    params = {
        "q":          query,
        "restrict_sr": True,
        "sort":       sort,
        "t":          time_filter,
        "limit":      limit,
    }

    try:
        resp = httpx.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": str(e), "results": []}

    posts = data.get("data", {}).get("children", [])
    results = [_clean_post(p) for p in posts if p.get("kind") == "t3"]

    return {
        "query":     query,
        "subreddit": subreddit,
        "total":     len(results),
        "results":   results
    }


@mcp.tool()
def get_subreddit_hot(
    subreddit: str = "netsec",
    limit: int = 10
) -> dict:
    """
    Get currently hot/trending posts from a security subreddit.

    Use this to understand what the security community is actively
    discussing right now without a specific search term.

    Args:
        subreddit: Subreddit name e.g. 'netsec', 'cybersecurity', 'blueteamsec'
        limit: Number of posts to retrieve (max 25)

    Returns:
        Dict with hot posts including titles, scores, and URLs
    """
    limit = min(limit, 25)
    url = f"{REDDIT_BASE}/r/{subreddit}/hot.json"

    try:
        resp = httpx.get(
            url,
            params={"limit": limit},
            headers=HEADERS,
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": str(e), "results": []}

    posts = data.get("data", {}).get("children", [])
    results = [_clean_post(p) for p in posts if p.get("kind") == "t3"]

    return {
        "subreddit": subreddit,
        "total":     len(results),
        "results":   results
    }


@mcp.tool()
def get_reddit_post_comments(
    post_id: str,
    subreddit: str,
    max_comments: int = 10
) -> dict:
    """
    Get top comments from a specific Reddit post.

    Use this after finding an interesting post to get community
    analysis, expert opinions, and additional context.

    Args:
        post_id: Reddit post ID (from search_reddit results, the 'id' field)
        subreddit: Subreddit the post belongs to (required by Reddit API)
        max_comments: Maximum top-level comments to retrieve

    Returns:
        Dict with post details and top comments
    """
    max_comments = min(max_comments, 20)
    url = f"{REDDIT_BASE}/r/{subreddit}/comments/{post_id}.json"

    try:
        resp = httpx.get(
            url,
            params={"limit": max_comments, "depth": 1},
            headers=HEADERS,
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": str(e), "comments": []}

    # data[0] = post, data[1] = comments
    if not isinstance(data, list) or len(data) < 2:
        return {"error": "Unexpected response format", "comments": []}

    post_data = data[0]["data"]["children"][0]["data"]
    comment_children = data[1]["data"]["children"]

    comments = []
    for child in comment_children:
        if child.get("kind") == "t1":
            c = child["data"]
            if not c.get("body") or c.get("body") in ("[deleted]", "[removed]"):
                continue
            comments.append({
                "id":     c.get("id"),
                "author": c.get("author"),
                "body":   c.get("body", "")[:500],
                "score":  c.get("score", 0),
                "url":    f"https://reddit.com{c.get('permalink', '')}",
            })

    return {
        "post_id":    post_id,
        "title":      post_data.get("title"),
        "score":      post_data.get("score", 0),
        "total_comments": post_data.get("num_comments", 0),
        "comments":   comments
    }


@mcp.tool()
def list_security_subreddits() -> dict:
    """
    List the security subreddits available for monitoring.

    Use this when you need to know which subreddits to target
    for a specific type of security intelligence.

    Returns:
        Dict with subreddit names and their focus areas
    """
    return {
        "subreddits": [
            {"name": "netsec",             "focus": "Network security, CVEs, research"},
            {"name": "cybersecurity",      "focus": "General cybersecurity news and discussion"},
            {"name": "blueteamsec",        "focus": "Defensive security, SOC, detection engineering"},
            {"name": "ReverseEngineering", "focus": "Malware analysis, RE techniques"},
            {"name": "malware",            "focus": "Malware samples, analysis, IOCs"},
            {"name": "threatintel",        "focus": "Threat intelligence, APTs, campaigns"},
            {"name": "AskNetsec",          "focus": "Q&A for security professionals"},
            {"name": "hacking",            "focus": "General hacking, CTFs, techniques"},
        ]
    }


if __name__ == "__main__":
    print("Starting Reddit MCP server...")
    mcp.run(transport="stdio")