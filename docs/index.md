# Guage-Kit

A unified, extensible toolkit for evaluating LLMs, RAG systems, and embeddings.

## Installation

```bash
pip install guage-kit
```

Or with UV:

```bash
uv add guage-kit
```

## Quick Start

```python
from guage_kit import evaluate

# Basic evaluation
scores = evaluate(
    data="path/to/your/data.jsonl",
    metrics=["rougeL", "bleu", "answer_relevancy"]
)
print(scores)
```

## Features

- **Comprehensive Metrics**: LLM quality, RAG evaluation, retrieval metrics, embedding analysis
- **Multiple Interfaces**: Python API, CLI, and Streamlit UI
- **Extensible**: Plugin system for custom metrics
- **Production Ready**: CI/CD integration, comprehensive reporting

## Contents

```{toctree}
:maxdepth: 2
:caption: Contents

guides/quickstart
guides/installation
guides/examples
api/index
references/metrics
maintenance/pypi-publishing
maintenance/github-pages
maintenance/first-release
```

**Docstring style**: NumPy/Google; `napoleon` enabled. Ensure **all public functions** have comprehensive docstrings (parameters, returns, notes, examples).
```