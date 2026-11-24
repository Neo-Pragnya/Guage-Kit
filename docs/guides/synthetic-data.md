---
title: Synthetic test sets
description: Build a question set with relevant passage ids from your own documents, offline with cloze questions or with a model.
---

# Synthetic test sets

When you have documents but no test questions, generate them. Every generated sample records the passage it came from
in `relevant_ids`, so the same set tests retrieval and grounded answering.

```bash
guage synth docs/ -o data/synthetic.jsonl --corpus data/corpus.jsonl            # offline cloze questions
guage synth docs/ -o data/synthetic.jsonl --provider anthropic:claude-opus-5-5 --per-chunk 2   # with a model
```

`--corpus` writes the chunks (`{"id", "source", "text"}` per line), which is the corpus your retriever under test
should index, so that `relevant_ids` match its document ids.

## Reading and chunking

`read_documents(paths)` reads `.md`, `.txt`, `.rst` and `.html` files (folders recursively; scripts, styles and tags
are stripped from HTML). `chunk(documents, size=120, overlap=20)` makes word windows. A chunk id hashes the source
name, the offset and the text, so it stays stable as long as the document does, and repeated passages still get
distinct ids. Windows shorter than 8 words are dropped.

## Offline: cloze questions

`cloze_dataset(chunks, per_chunk=1, seed=0)` picks sentences of 8–40 words, blanks out a key span (a number or a
capitalised phrase), and asks for it:

```python
from guage_kit.synth import chunk, cloze_dataset

docs = [("faq.md", "Lumen Notes syncs every 30 seconds when you are online. Pro costs 6 dollars per month and includes 100 GB of storage. Shared notebooks can be opened by up to 20 collaborators.")]
chunks = chunk(docs, size=60, overlap=10)
ds = cloze_dataset(chunks)
print(len(chunks), ds[0].input, "->", ds[0].expected)
```

```text
1 Fill in the blank: Lumen Notes syncs every _____ seconds when you are online. -> 30
```

Cloze questions are mechanical, but they are deterministic, free and grounded by construction. They are good for
regression-testing retrieval and for catching answers that ignore their context.

## With a model: natural questions

`generate_qa(chunks, provider, per_chunk=2)` asks a model (any [provider spec](judges.md#providers) or object) for
question-answer pairs about each passage, in varied kinds (factual, why/how, comparison), as structured JSON. The
passage is passed as untrusted content. Then a **grounding filter** keeps only answers the passage supports
(lexical support of at least 0.5), so questions the model could not ground are dropped. A passage whose request
fails is skipped, and generation continues.

Each sample's metadata keeps the source, the passage, the question kind and the generating model. Review a sample
of the questions by hand before you use the set as a gate: generated questions tend to be easier and more literal
than real users' questions.
