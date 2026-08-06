# main.py

import asyncio
import sys
from agent.osint_agent import run_investigation


EXAMPLE_QUERIES = [
    "What are the latest OpenSSL vulnerabilities being discussed in the security community? Check our knowledge base and external sources.",
    "Give me an intelligence briefing on supply chain attacks in npm packages. Search GitHub, HackerNews, and our threat database.",
    "What is APT-Phantom and what campaigns are they associated with? Pull everything we have and check external sources for recent activity.",
    "Search for recent ransomware news and check if any known threat actors in our database are involved.",
]


async def main():
    if len(sys.argv) > 1:
        # query passed as command line argument
        query = " ".join(sys.argv[1:])
    else:
        # interactive mode
        print("\n🔍 OSINT Intelligence Agent")
        print("─" * 40)
        print("\nExample queries:")
        for i, q in enumerate(EXAMPLE_QUERIES, 1):
            print(f"  {i}. {q[:80]}...")

        print("\nEnter your query (or press Enter for example 1):")
        query = input("> ").strip()

        if not query:
            query = EXAMPLE_QUERIES[0]

    result = await run_investigation(query)

    print("\n" + "="*60)
    print("  FINAL INTELLIGENCE REPORT")
    print("="*60)
    print(result)
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())