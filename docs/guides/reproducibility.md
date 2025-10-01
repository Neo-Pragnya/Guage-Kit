# Reproducibility in Evaluations

Reproducibility is a critical aspect of evaluating machine learning models, particularly in the context of LLMs (Large Language Models), RAG (Retrieval-Augmented Generation) systems, and embeddings. This document outlines the principles and practices to ensure that evaluations can be reliably reproduced.

## Key Principles

1. **Seeded Metrics**: All stochastic processes in the evaluation should be seeded with a fixed random seed. This ensures that results can be replicated across different runs. Users should be able to specify the seed in the configuration.

2. **Bootstrap Confidence Intervals**: To provide a measure of uncertainty in the evaluation metrics, bootstrap confidence intervals (CIs) should be calculated. Users can enable this feature by specifying the number of bootstrap samples in the configuration.

3. **Artifact Management**: All evaluation results, including metrics and reports, should be saved as artifacts. This allows users to revisit previous evaluations and compare results over time. The system should provide a clear structure for storing these artifacts.

4. **Version Control**: It is essential to keep track of the versions of the models, datasets, and evaluation scripts used in the evaluation. This can be achieved by including version information in the evaluation reports and artifacts.

5. **Environment Consistency**: The evaluation environment should be consistent across different runs. This includes using the same versions of libraries and dependencies. Users should be encouraged to use tools like `uv` to manage dependencies and ensure reproducibility.

## Configuration Example

Here is an example configuration that demonstrates how to set up reproducibility features:

```yaml
# config.yaml
seed: 42
bootstrap:
  n_samples: 1000
report:
  html: "reports/evaluation_report.html"
  json: "reports/evaluation_results.json"
```

## Running Evaluations

When running evaluations, users should ensure that they specify the configuration file that includes the reproducibility settings. For example, using the command line interface:

```bash
guage-kit run \
    --data data/evaluation_data.jsonl \
    --metrics retrieval@10 mrr ndcg@10 \
    --config config.yaml \
    --report-html reports/evaluation_report.html \
    --report-json reports/evaluation_results.json
```

By following these principles and practices, users can ensure that their evaluations are reproducible, facilitating better understanding and trust in the results obtained from the Guage-Kit toolkit.