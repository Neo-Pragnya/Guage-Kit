# Guage-Kit 🎯

[![PyPI version](https://badge.fury.io/py/guage-kit.svg)](https://badge.fury.io/py/guage-kit)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/abhikanap/Guage-Kit/workflows/CI/badge.svg)](https://github.com/abhikanap/Guage-Kit/actions)

**Guage-Kit** is a comprehensive, extensible evaluation toolkit designed for assessing Large Language Models (LLMs), Retrieval-Augmented Generation (RAG) systems, and embeddings. It provides a unified Python API, command-line interface (CLI), and web UI for seamless integration and evaluation across various AI applications.

## 🚀 Key Features

- **🔧 Unified API & CLI**: Consistent interface for all evaluation needs
- **📊 Comprehensive Metrics**: 7+ built-in metrics covering LLM quality, RAG performance, retrieval effectiveness, and embeddings evaluation
- **🎛️ Streamlit UI**: Interactive web interface for running and visualizing evaluations
- **📚 Rich Documentation**: Detailed Sphinx documentation with examples and API reference
- **⚡ Fast & Scalable**: Optimized for performance with parallel processing support
- **🔧 Extensible**: Easy to add custom metrics and evaluation workflows
- **📦 Production Ready**: Robust testing, type checking, and CI/CD pipeline

## 📦 Installation

### Using pip
```bash
pip install guage-kit
```

### Using uv (recommended)
```bash
uv add guage-kit
```

### Development Installation
```bash
git clone https://github.com/abhikanap/Guage-Kit.git
cd Guage-Kit
uv sync --all-extras
```

### Optional Dependencies

Install with specific extras for additional functionality:

```bash
# For Streamlit UI
pip install "guage-kit[ui]"

# For documentation building
pip install "guage-kit[docs]"

# For development
pip install "guage-kit[dev]"

# All extras
pip install "guage-kit[all]"
```

## 🎯 Quick Start

### Python API

```python
from guage_kit.api import evaluate
from guage_kit.schemas.core import EvalSample, Query, Generation

# Create evaluation sample
sample = EvalSample(
    query=Query(
        id="q1",
        prompt="What is CRISPR?",
        references=["CRISPR is a genome editing tool"]
    ),
    generation=Generation(
        query_id="q1",
        text="CRISPR is a revolutionary genome editing technology",
        model="gpt-4"
    )
)

# Run evaluation
results = evaluate(
    data=[sample],
    metrics=["rougeL", "bleu"],
    config={}
)

print(results)
# Output: {'rougeL': 0.85, 'bleu': 0.72}
```

### Command Line Interface

```bash
# Basic evaluation
guage-kit run --data eval_data.jsonl --metrics rougeL bleu

# Advanced evaluation with configuration
guage-kit run \
    --data data/rag_eval.jsonl \
    --metrics rougeL bleu recall_at_k mrr ndcg answer_relevancy \
    --config config.yaml \
    --output results.json
```

### Streamlit Web UI

```bash
# Launch interactive web interface
uv run streamlit run apps/guage_kit_ui/Home.py
```

## 📊 Supported Metrics

### LLM Quality Metrics
- **ROUGE-L**: Longest Common Subsequence-based evaluation
- **BLEU**: Bilingual Evaluation Understudy score

### RAG Quality Metrics  
- **Answer Relevancy**: Semantic similarity between query and response
- **Faithfulness**: Consistency between context and generated answer

### Information Retrieval Metrics
- **Recall@k**: Top-k retrieval accuracy
- **MRR**: Mean Reciprocal Rank
- **nDCG@k**: Normalized Discounted Cumulative Gain

### Embeddings Metrics
- **STS Spearman**: Semantic Textual Similarity correlation

## 📋 Data Format

Guage-Kit expects data in a structured format with clear separation of queries, context, and generations:

```json
{
  "query": {
    "id": "q1",
    "prompt": "What is machine learning?",
    "references": ["Machine learning is a subset of AI..."]
  },
  "retrieval": {
    "query_id": "q1",
    "chunks": [
      {
        "id": "c1",
        "text": "Machine learning involves algorithms...",
        "source": "textbook",
        "relevance_score": 0.95
      }
    ]
  },
  "generation": {
    "query_id": "q1",
    "text": "Machine learning is a powerful AI technique...",
    "model": "gpt-4",
    "metadata": {}
  }
}
```

## 🛠️ Configuration

Create a `config.yaml` file to customize evaluation settings:

```yaml
metrics:
  rougeL:
    use_stemmer: true
  bleu:
    max_order: 4
  recall_at_k:
    k: [1, 5, 10]
  ndcg:
    k: 10

output:
  format: "json"
  include_details: true
```

## 📚 Documentation

- **API Reference**: [docs/api/](docs/api/)
- **User Guides**: [docs/guides/](docs/guides/)
- **Metrics Reference**: [docs/references/metrics.rst](docs/references/metrics.rst)

Build documentation locally:
```bash
uv run sphinx-build docs docs/_build
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=guage_kit

# Run specific test file
uv run pytest tests/test_basic.py -v
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/abhikanap/Guage-Kit.git
cd Guage-Kit
uv sync --all-extras
uv run pre-commit install
```

### Code Quality

We maintain high code quality standards:
- **Type Checking**: mypy
- **Linting**: ruff
- **Formatting**: black, isort
- **Testing**: pytest with coverage

## 📈 Roadmap

- [ ] Additional metrics (METEOR, BERTScore, Semantic Similarity)
- [ ] Integration with popular frameworks (LangChain, LlamaIndex)
- [ ] Advanced reporting and visualization
- [ ] Distributed evaluation support
- [ ] Custom metric development toolkit

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to all contributors and the open-source community
- Built with modern Python tools: UV, Pydantic, Streamlit, Sphinx
- Inspired by the need for standardized AI evaluation practices

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/abhikanap/Guage-Kit/issues)
- **Discussions**: [GitHub Discussions](https://github.com/abhikanap/Guage-Kit/discussions)
- **Documentation**: [Project Documentation](docs/index.md)

---

**Made with ❤️ for the AI evaluation community**