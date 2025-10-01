# src/guage_kit/__init__.py

"""Guage-Kit: A unified evaluation toolkit for LLMs, RAG systems, and embeddings."""

__version__ = "0.1.0"
__author__ = "Neo Pragnya"
__email__ = "opensource@neo-pragnya.org"
__license__ = "Apache-2.0"

from .api import evaluate

__all__ = ["evaluate", "__version__"]