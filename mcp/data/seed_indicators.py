# data/seed_indicators.py
"""
Loads sample threat intelligence indicators into Elasticsearch.
This gives the agent real data to correlate against when it
searches external sources.
"""

import os
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

load_dotenv()

es = Elasticsearch(
    os.getenv("ES_HOST", "http://localhost:9200"),
    basic_auth=(
        os.getenv("ES_USERNAME", "elastic"),
        os.getenv("ES_PASSWORD", "osint_password")
    )
)

def ts(date_str):
    return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc).isoformat()

INDICATORS = [
    # ── CVEs ──────────────────────────────────────────────────────────────────
    {
        "indicator_id": "CVE-2024-0001",
        "type": "cve",
        "value": "CVE-2024-0001",
        "description": "Critical buffer overflow in OpenSSL 3.x affecting TLS handshake. Remote code execution possible without authentication.",
        "tags": ["openssl", "tls", "rce", "buffer-overflow", "critical"],
        "severity": "critical",
        "source": "nvd.nist.gov",
        "first_seen": ts("2024-01-15"),
        "last_seen": ts("2024-03-01"),
        "related_to": ["CAMPAIGN-2024-TLS", "ACTOR-APT-PHANTOM"],
        "metadata": {"cvss_score": 9.8, "affected_versions": ["3.0.0", "3.0.1", "3.1.0"]}
    },
    {
        "indicator_id": "CVE-2024-0042",
        "type": "cve",
        "value": "CVE-2024-0042",
        "description": "SQL injection vulnerability in popular open-source authentication library allowing privilege escalation.",
        "tags": ["sql-injection", "auth-bypass", "privilege-escalation"],
        "severity": "high",
        "source": "github.com/advisories",
        "first_seen": ts("2024-02-10"),
        "last_seen": ts("2024-02-28"),
        "related_to": [],
        "metadata": {"cvss_score": 8.1, "affected_library": "auth-lib", "patched_in": "2.1.1"}
    },
    {
        "indicator_id": "CVE-2024-0099",
        "type": "cve",
        "value": "CVE-2024-0099",
        "description": "Memory corruption vulnerability in Linux kernel networking stack. Local privilege escalation to root.",
        "tags": ["linux", "kernel", "lpe", "networking", "memory-corruption"],
        "severity": "high",
        "source": "kernel.org",
        "first_seen": ts("2024-03-05"),
        "last_seen": ts("2024-03-20"),
        "related_to": ["ACTOR-APT-PHANTOM"],
        "metadata": {"cvss_score": 7.8, "affected_kernels": ["5.15", "6.1", "6.6"]}
    },

    # ── Threat Actors ─────────────────────────────────────────────────────────
    {
        "indicator_id": "ACTOR-APT-PHANTOM",
        "type": "actor",
        "value": "APT-Phantom",
        "description": "Nation-state APT group targeting critical infrastructure. Known for exploiting TLS vulnerabilities and supply chain attacks. Active since 2021.",
        "tags": ["apt", "nation-state", "critical-infrastructure", "supply-chain", "tls"],
        "severity": "critical",
        "source": "internal-analysis",
        "first_seen": ts("2021-06-01"),
        "last_seen": ts("2024-03-15"),
        "related_to": ["CVE-2024-0001", "CVE-2024-0099", "CAMPAIGN-2024-TLS", "DOMAIN-phantom-c2"],
        "metadata": {"origin": "unknown", "aliases": ["Ghost Panda", "UNC4821"], "ttps": ["T1190", "T1195"]}
    },
    {
        "indicator_id": "ACTOR-HACKTIVIST-RED",
        "type": "actor",
        "value": "RedCollective",
        "description": "Hacktivist group conducting DDoS and defacement campaigns against financial institutions. Primarily opportunistic.",
        "tags": ["hacktivist", "ddos", "defacement", "financial"],
        "severity": "medium",
        "source": "osint",
        "first_seen": ts("2023-01-10"),
        "last_seen": ts("2024-02-20"),
        "related_to": ["CAMPAIGN-2024-DDOS"],
        "metadata": {"motivation": "political", "primary_targets": ["banking", "insurance"]}
    },

    # ── Campaigns ─────────────────────────────────────────────────────────────
    {
        "indicator_id": "CAMPAIGN-2024-TLS",
        "type": "campaign",
        "value": "Operation TLS-Harvest",
        "description": "Coordinated campaign exploiting TLS vulnerabilities across government and finance sectors. Attributed to APT-Phantom with medium confidence.",
        "tags": ["tls", "government", "finance", "apt", "ongoing"],
        "severity": "critical",
        "source": "internal-analysis",
        "first_seen": ts("2024-01-20"),
        "last_seen": ts("2024-03-18"),
        "related_to": ["CVE-2024-0001", "ACTOR-APT-PHANTOM", "DOMAIN-phantom-c2"],
        "metadata": {"confidence": "medium", "sectors": ["government", "finance", "telecom"]}
    },
    {
        "indicator_id": "CAMPAIGN-2024-DDOS",
        "type": "campaign",
        "value": "Operation Flood-2024",
        "description": "Wave of DDoS attacks targeting European banking infrastructure in Q1 2024.",
        "tags": ["ddos", "banking", "europe", "q1-2024"],
        "severity": "high",
        "source": "osint",
        "first_seen": ts("2024-01-05"),
        "last_seen": ts("2024-02-28"),
        "related_to": ["ACTOR-HACKTIVIST-RED"],
        "metadata": {"peak_volume_gbps": 850, "targets": ["DE", "FR", "NL", "BE"]}
    },

    # ── Domains / IPs ─────────────────────────────────────────────────────────
    {
        "indicator_id": "DOMAIN-phantom-c2",
        "type": "domain",
        "value": "update-cdn-secure.net",
        "description": "Command and control domain used by APT-Phantom. Masquerades as legitimate CDN infrastructure.",
        "tags": ["c2", "apt", "masquerade", "cdn"],
        "severity": "critical",
        "source": "passive-dns",
        "first_seen": ts("2023-11-01"),
        "last_seen": ts("2024-03-10"),
        "related_to": ["ACTOR-APT-PHANTOM", "CAMPAIGN-2024-TLS"],
        "metadata": {"registrar": "namecheap", "ip_history": ["185.220.101.45", "185.220.101.89"]}
    },
    {
        "indicator_id": "IP-TOR-EXIT-001",
        "type": "ip",
        "value": "185.220.101.45",
        "description": "Known Tor exit node also observed in APT-Phantom C2 communications.",
        "tags": ["tor", "exit-node", "c2", "apt"],
        "severity": "high",
        "source": "passive-dns",
        "first_seen": ts("2023-10-15"),
        "last_seen": ts("2024-03-12"),
        "related_to": ["DOMAIN-phantom-c2", "ACTOR-APT-PHANTOM"],
        "metadata": {"asn": "AS4766", "country": "DE"}
    },

    # ── Supply Chain ──────────────────────────────────────────────────────────
    {
        "indicator_id": "SUPPLY-NPM-2024",
        "type": "supply_chain",
        "value": "malicious-npm-lodash-clone",
        "description": "Malicious npm package impersonating lodash with typosquatting. Exfiltrates environment variables on install.",
        "tags": ["npm", "supply-chain", "typosquatting", "exfiltration", "nodejs"],
        "severity": "high",
        "source": "github.com/advisories",
        "first_seen": ts("2024-02-14"),
        "last_seen": ts("2024-02-20"),
        "related_to": [],
        "metadata": {"package_name": "lodash-utils-clone", "downloads_before_removal": 1240}
    }
]


def seed():
    actions = [
        {
            "_index": "threat_indicators",
            "_id": indicator["indicator_id"],
            "_source": indicator
        }
        for indicator in INDICATORS
    ]

    success, errors = helpers.bulk(es, actions, raise_on_error=False)
    print(f"✓ Indexed {success} indicators")
    if errors:
        print(f"✗ Errors: {errors}")

    # verify
    es.indices.refresh(index="threat_indicators")
    count = es.count(index="threat_indicators")["count"]
    print(f"✓ Total indicators in ES: {count}")


if __name__ == "__main__":
    try:
        es.info()
        print("✓ Connected to Elasticsearch\n")
    except Exception as e:
        print(f"✗ Cannot connect: {e}")
        exit(1)

    seed()
    print("\nSample queries you can now run:")
    print('  GET threat_indicators/_search?q=openssl')
    print('  GET threat_indicators/_search?q=type:actor')