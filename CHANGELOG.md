# CHANGELOG

## [Unreleased]

## [0.1.0] - YYYY-MM-DD
### Added
- Initial project structure and files as per project plan.
- Implemented `evaluate()` function in `src/guage_kit/api.py`.
- Created CLI for running evaluations in `src/guage_kit/cli.py`.
- Defined data models in `src/guage_kit/schemas/core.py`.
- Added metrics for LLM quality: ROUGE-L, BLEU, METEOR in `src/guage_kit/metrics/llm_quality.py`.
- Implemented RAG quality metrics including faithfulness and answer relevancy in `src/guage_kit/metrics/rag_quality.py`.
- Developed information retrieval metrics in `src/guage_kit/metrics/retrieval_ir.py`.
- Created embeddings evaluation metrics in `src/guage_kit/metrics/embeddings.py`.
- Added hallucination detection metrics in `src/guage_kit/metrics/hallucination.py`.
- Implemented safety and bias metrics in `src/guage_kit/metrics/safety_bias.py`.
- Developed model calibration metrics in `src/guage_kit/metrics/calibration.py`.
- Created runtime cost metrics in `src/guage_kit/metrics/runtime_cost.py`.
- Added adapters for RAGAS, TruLens, and PromptFoo.
- Developed Streamlit UI with pages for running evaluations, exploring results, and comparing runs.
- Created documentation using Sphinx with Wagtail theme.
- Added unit tests for core functionalities in the `tests` directory.
- Configured CI/CD with GitHub Actions for linting, testing, and documentation building.

### Changed
- Initial versioning set to 0.1.0 following Semantic Versioning guidelines. 

### Fixed
- N/A

## [0.1.0] - YYYY-MM-DD
### Added
- Initial project structure and files as per project plan.
- Implemented `evaluate()` function in `src/guage_kit/api.py`.
- Created CLI for running evaluations in `src/guage_kit/cli.py`.
- Defined data models in `src/guage_kit/schemas/core.py`.
- Added metrics for LLM quality: ROUGE-L, BLEU, METEOR in `src/guage_kit/metrics/llm_quality.py`.
- Implemented RAG quality metrics including faithfulness and answer relevancy in `src/guage_kit/metrics/rag_quality.py`.
- Developed information retrieval metrics in `src/guage_kit/metrics/retrieval_ir.py`.
- Created embeddings evaluation metrics in `src/guage_kit/metrics/embeddings.py`.
- Added hallucination detection metrics in `src/guage_kit/metrics/hallucination.py`.
- Implemented safety and bias metrics in `src/guage_kit/metrics/safety_bias.py`.
- Developed model calibration metrics in `src/guage_kit/metrics/calibration.py`.
- Created runtime cost metrics in `src/guage_kit/metrics/runtime_cost.py`.
- Added adapters for RAGAS, TruLens, and PromptFoo.
- Developed Streamlit UI with pages for running evaluations, exploring results, and comparing runs.
- Created documentation using Sphinx with Wagtail theme.
- Added unit tests for core functionalities in the `tests` directory.
- Configured CI/CD with GitHub Actions for linting, testing, and documentation building.

### Changed
- Initial versioning set to 0.1.0 following Semantic Versioning guidelines. 

### Fixed
- N/A