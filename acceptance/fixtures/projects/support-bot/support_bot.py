"""A tiny support bot: keyword retrieval over the help centre, answer from the best passage."""

import re

DOCS = {
    "kb-sync": "Lumen Notes syncs across devices every 30 seconds when you are online. Offline edits are kept on the device and uploaded when the connection returns.",
    "kb-export": "You can export a notebook as Markdown, PDF or HTML from the notebook menu. Exports include attachments up to 25 MB each.",
    "kb-pricing": "Lumen Notes Free includes 3 notebooks and 1 GB of storage. Lumen Notes Pro costs 6 dollars per month and includes unlimited notebooks and 100 GB of storage.",
    "kb-sharing": "Shared notebooks can be opened by up to 20 collaborators. Owners can grant view, comment or edit access to each person.",
    "kb-security": "Notes are encrypted in transit with TLS 1.3 and at rest with AES-256. End-to-end encryption is available for Pro notebooks marked private.",
    "kb-refund": "Annual Pro subscriptions can be refunded in full within 14 days of purchase. Monthly plans are not refunded but can be cancelled at any time.",
    "kb-tags": "Tags are created by typing a hash sign before a word. A note can carry up to 50 tags, and tags can be nested with a slash.",
    "kb-search": "Search looks inside note text, attachments and handwriting. Handwriting search supports English, Spanish and German.",
    "kb-backup": "Pro accounts keep a version history of 90 days. Free accounts keep 7 days of history. Deleted notes stay in the trash for 30 days.",
    "kb-import": "Notes can be imported from Markdown folders, plain text files and ENEX archives. Imports keep creation dates and tags.",
    "kb-offline": "Offline mode is available on desktop and mobile. On mobile, choose which notebooks to keep offline from the notebook settings.",
    "kb-api": "The Lumen Notes API allows 600 requests per minute per token. Tokens are created in account settings and can be revoked at any time."
}

STOP = set("a an the is are do does i my how what which can of to in on for with and or it".split())


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP}


def retrieve(question, k=3):
    q = _words(question)
    ranked = sorted(DOCS, key=lambda d: (-len(q & _words(DOCS[d])), d))
    return ranked[:k]


def answer(question):
    ids = retrieve(question)
    best = DOCS[ids[0]]
    sentence = max(re.split(r"(?<=[.])\s+", best), key=lambda s: len(_words(question) & _words(s)))
    return {"output": sentence, "contexts": [DOCS[i] for i in ids], "retrieved_ids": ids}
