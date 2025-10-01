.. Guage-Kit API Documentation

Welcome to the Guage-Kit API documentation. This section provides an overview of the public API and its functionalities.

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api
   metrics
   schemas
   adapters
   datasets
   providers
   utils

.. _api:

Guage-Kit API
=============

The Guage-Kit API provides a unified interface for evaluating LLMs, RAG systems, and embeddings. The main entry point is the `evaluate` function, which allows users to run selected metrics and obtain aggregated scores.

.. autofunction:: guage_kit.api.evaluate

.. _metrics:

Metrics
-------

Guage-Kit includes a variety of metrics for evaluating LLMs, RAG systems, and embeddings. Each metric is implemented as a separate module within the `metrics` package.

.. toctree::
   :maxdepth: 1

   metrics/llm_quality
   metrics/rag_quality
   metrics/retrieval_ir
   metrics/embeddings
   metrics/hallucination
   metrics/safety_bias
   metrics/calibration
   metrics/runtime_cost

.. _schemas:

Schemas
-------

The `schemas` package defines data models used throughout the API. These models are built using Pydantic for data validation and serialization.

.. toctree::
   :maxdepth: 1

   schemas/core

.. _adapters:

Adapters
--------

Guage-Kit supports various adapters for integrating with external systems. The `adapters` package contains implementations for different adapters.

.. toctree::
   :maxdepth: 1

   adapters/ragas_adapter
   adapters/trulens_adapter
   adapters/promptfoo_adapter

.. _datasets:

Datasets
--------

The `datasets` package provides functionality for loading and transforming datasets used in evaluations.

.. toctree::
   :maxdepth: 1

   datasets/schema
   datasets/loaders
   datasets/transforms

.. _providers:

Providers
---------

Guage-Kit includes providers for accessing external services. The `providers` package contains implementations for different providers.

.. toctree::
   :maxdepth: 1

   providers/openai_provider
   providers/bedrock_provider
   providers/vllm_provider

.. _utils:

Utilities
---------

The `utils` package contains various utility functions that assist with common tasks in the evaluation process.

.. toctree::
   :maxdepth: 1

   utils/nlp
   utils/scoring
   utils/parallel
   utils/io