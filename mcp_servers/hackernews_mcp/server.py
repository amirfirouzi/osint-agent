# mcp_servers/hackernews_mcp/server.py
"""
HackerNews MCP Server
Wraps the Algolia HN Search API — completely free, no auth required.
API docs: https://hn.algolia.com/api
"""

import httpx
from datetime import datetime, timezone, timedelta
from fastmcp import FastMCP
import logging
logging.getLogger("fastmcp").setLevel(logging.ERROR)
import os
os.environ["FASTMCP_LOG_LEVEL"] = "ERROR"

mcp = FastMCP("hackernews-mcp")

HN_SEARCH_URL = "https://hn.algolia.com/api/v1"
HN_ITEM_URL   = "https://hacker-news.firebaseio.com/v0"


def _age_to_timestamp(hours_ago: int) -> int:
    """Convert hours ago to unix timestamp for Algolia filter."""
    dt = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return int(dt.timestamp())


@mcp.tool()
def search_hackernews(
    query: str,
    hours_ago: int = 168,
    result_type: str = "story",
    limit: int = 10
) -> dict:
    """
    Search HackerNews stories and comments using full-text search.

    Use this to find recent HackerNews discussions about security topics,
    vulnerabilities, tools, or any technical subject.

    Args:
        query: Search query e.g. 'OpenSSL vulnerability' or 'supply chain attack'
        hours_ago: How far back to search (default 168 = last 7 days)
        result_type: 'story' for posts, 'comment' for comments, 'all' for both
        limit: Number of results to return (max 20)

    Returns:
        Dict with 'total' count and 'results' list of stories/comments
    """
    tags = f"({result_type})" if result_type != "all" else "(story,comment)"
    num_results = min(limit, 20)

    params = {
        "query":        query,
        "tags":         tags,
        "numericFilters": f"created_at_i>{_age_to_timestamp(hours_ago)}",
        "hitsPerPage":  num_results,
    }

    try:
        resp = httpx.get(f"{HN_SEARCH_URL}/search", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": str(e), "results": []}

    results = []
    for hit in data.get("hits", []):
        results.append({
            "id":        hit.get("objectID"),
            "title":     hit.get("title") or hit.get("comment_text", "")[:120],
            "url":       hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "author":    hit.get("author"),
            "points":    hit.get("points", 0),
            "comments":  hit.get("num_comments", 0),
            "created_at": hit.get("created_at"),
            "hn_url":    f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
        })

    return {
        "query":   query,
        "total":   data.get("nbHits", 0),
        "results": results
    }


@mcp.tool()
def get_hackernews_top_stories(limit: int = 10) -> dict:
    """
    Get current top stories from HackerNews front page.

    Use this to understand what the security/tech community is
    paying attention to right now, without a specific search query.

    Args:
        limit: Number of top stories to retrieve (max 15)

    Returns:
        Dict with list of current top stories with scores and links
    """
    limit = min(limit, 15)

    try:
        # get top story IDs
        resp = httpx.get(f"{HN_ITEM_URL}/topstories.json", timeout=10)
        resp.raise_for_status()
        story_ids = resp.json()[:limit]

        stories = []
        for story_id in story_ids:
            item_resp = httpx.get(
                f"{HN_ITEM_URL}/item/{story_id}.json",
                timeout=10
            )
            if item_resp.status_code == 200:
                item = item_resp.json()
                if item and item.get("type") == "story":
                    stories.append({
                        "id":       item.get("id"),
                        "title":    item.get("title"),
                        "url":      item.get("url", f"https://news.ycombinator.com/item?id={item.get('id')}"),
                        "author":   item.get("by"),
                        "points":   item.get("score", 0),
                        "comments": item.get("descendants", 0),
                        "hn_url":   f"https://news.ycombinator.com/item?id={item.get('id')}",
                    })

        return {"total": len(stories), "results": stories}

    except Exception as e:
        return {"error": str(e), "results": []}


@mcp.tool()
def get_hackernews_comments(story_id: str, max_comments: int = 10) -> dict:
    """
    Get top-level comments for a specific HackerNews story.

    Use this after finding an interesting story to get community
    discussion and expert opinions on the topic.

    Args:
        story_id: HN story ID (from search_hackernews results)
        max_comments: Maximum number of comments to retrieve

    Returns:
        Dict with story details and list of top comments
    """
    max_comments = min(max_comments, 20)

    try:
        # get story
        story_resp = httpx.get(
            f"{HN_ITEM_URL}/item/{story_id}.json",
            timeout=10
        )
        story_resp.raise_for_status()
        story = story_resp.json()

        if not story:
            return {"error": f"Story {story_id} not found"}

        # get top-level comments
        comment_ids = story.get("kids", [])[:max_comments]
        comments = []

        for cid in comment_ids:
            c_resp = httpx.get(f"{HN_ITEM_URL}/item/{cid}.json", timeout=10)
            if c_resp.status_code == 200:
                c = c_resp.json()
                if c and not c.get("deleted") and not c.get("dead"):
                    text = c.get("text", "")
                    # strip HTML tags simply
                    import re
                    text = re.sub(r"<[^>]+>", " ", text).strip()
                    comments.append({
                        "id":     c.get("id"),
                        "author": c.get("by"),
                        "text":   text[:500],
                        "url":    f"https://news.ycombinator.com/item?id={c.get('id')}",
                    })

        return {
            "story_id":    story_id,
            "title":       story.get("title"),
            "url":         story.get("url"),
            "points":      story.get("score", 0),
            "total_comments": story.get("descendants", 0),
            "comments":    comments
        }

    except Exception as e:
        return {"error": str(e), "comments": []}


if __name__ == "__main__":
    print("Starting HackerNews MCP server...")
    mcp.run(transport="stdio")