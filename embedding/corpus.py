"""
Synthetic corpus simulating short social-media / threat-intel style posts.

Design notes (why these specific docs):
- doc_01 / doc_02 / doc_03: paraphrases of the same underlying event using
  totally different surface wording -> tests whether DENSE embeddings correctly
  cluster them despite near-zero word overlap.
- doc_10: contains an exact, unusual technical term (a CVE-style ID) that
  appears NOWHERE else -> tests whether BM25/sparse correctly surfaces it on
  an exact-term query, and whether DENSE search might miss/underrank it
  because there's no close semantic neighbor.
- doc_15 / doc_16: coded/evasive slang paraphrasing a harmful-content pattern
  with no lexical overlap with "normal" phrasing -> mirrors the real
  hateful/criminal-content detection problem: same underlying meaning,
  deliberately different surface form.
- The rest are distractor/unrelated posts so retrieval actually has to work.
"""

DOCS = [
    {"id": "doc_01", "text": "A coordinated network of accounts began pushing identical hashtags about the election within minutes of each other, suggesting automated amplification."},
    {"id": "doc_02", "text": "Dozens of bot-like profiles posted the same election hashtag almost simultaneously, a pattern consistent with a coordinated influence campaign."},
    {"id": "doc_03", "text": "Analysts flagged synchronized posting behavior across many suspicious accounts promoting one election narrative in a short time window."},
    {"id": "doc_04", "text": "The city council approved a new budget for road repairs starting next spring."},
    {"id": "doc_05", "text": "A local bakery announced it will open a second location downtown next month."},
    {"id": "doc_06", "text": "Ransomware operators encrypted the hospital's patient records system and demanded payment in cryptocurrency."},
    {"id": "doc_07", "text": "A healthcare provider's files were locked by malware and attackers requested a crypto ransom to restore access."},
    {"id": "doc_08", "text": "Weather forecasters predict heavy rainfall across the region through the weekend."},
    {"id": "doc_09", "text": "The football team clinched a playoff spot after last night's overtime win."},
    {"id": "doc_10", "text": "Security researchers published a technical writeup on CVE-2024-38112, a Windows MSHTML spoofing vulnerability exploited in the wild."},
    {"id": "doc_11", "text": "A new phishing kit is being sold on underground forums targeting online banking customers."},
    {"id": "doc_12", "text": "Fraudsters are impersonating bank support lines to trick customers into revealing one-time passcodes."},
    {"id": "doc_13", "text": "Scammers posing as bank representatives are calling customers to steal login verification codes."},
    {"id": "doc_14", "text": "The museum's new exhibit on ancient pottery opens to the public this Friday."},
    {"id": "doc_15", "text": "Some posts used coded slang and emoji substitutions to talk about hurting a specific ethnic group without triggering obvious keyword filters."},
    {"id": "doc_16", "text": "Users evaded content moderation by replacing slurs with symbols and euphemisms while still targeting the same minority group with threats."},
    {"id": "doc_17", "text": "A tech company announced record quarterly earnings driven by cloud services growth."},
    {"id": "doc_18", "text": "Investigators traced the coordinated posting activity back to a small cluster of accounts created the same week."},
    {"id": "doc_19", "text": "The city marathon route will be closed to traffic from 6am to 2pm on race day."},
    {"id": "doc_20", "text": "An open-source library used by thousands of projects disclosed a critical remote code execution flaw, tracked as CVE-2024-38112."},
]
