# agent/mcp_clients.py

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PYTHON = sys.executable

# absolute path to project root — works no matter where script is run from
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def get_mcp_client() -> MultiServerMCPClient:
    client = MultiServerMCPClient(
        {
            "github": {
                "command": os.getenv("NPX_PATH", "npx"),
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_TOKEN,
                },
                "transport": "stdio",
            },
            "hackernews": {
                "command": PYTHON,
                "args": [str(PROJECT_ROOT / "mcp_servers" / "hackernews_mcp" / "server.py")],
                "transport": "stdio",
            },
            "rss": {
                "command": PYTHON,
                "args": [str(PROJECT_ROOT / "mcp_servers" / "rss_mcp" / "server.py")],
                "transport": "stdio",
            },
            "elasticsearch": {
                "command": PYTHON,
                "args": [str(PROJECT_ROOT / "mcp_servers" / "elasticsearch_mcp" / "server.py")],
                "transport": "stdio",
                "env": {
                    "ES_HOST": os.getenv("ES_HOST", "http://localhost:9200"),
                    "ES_USERNAME": os.getenv("ES_USERNAME", "elastic"),
                    "ES_PASSWORD": os.getenv("ES_PASSWORD", "osint_password"),
                },
            },
        }
    )
    return client
