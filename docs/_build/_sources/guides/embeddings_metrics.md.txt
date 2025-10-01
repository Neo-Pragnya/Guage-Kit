# Embeddings Metrics Guide

## Overview

This document provides an overview of the metrics used to evaluate embeddings in the Guage-Kit project. Embeddings are crucial for various natural language processing tasks, and evaluating their quality is essential for ensuring the effectiveness of models.

## Intrinsic Metrics

Intrinsic metrics assess the quality of embeddings based on their internal properties. The following intrinsic metrics are included in Guage-Kit:

1. **STS Spearman**: Measures the correlation between the cosine similarity of embeddings and human-annotated similarity scores. A higher score indicates better alignment with human judgment.

2. **Clustering Metrics**:
   - **Adjusted Rand Index (ARI)**: Evaluates the similarity between two data clusterings. It ranges from -1 to 1, where 1 indicates perfect agreement.
   - **Normalized Mutual Information (NMI)**: Measures the amount of information obtained about one clustering from the other. It ranges from 0 to 1, with higher values indicating better clustering.

3. **k-NN Accuracy**: Evaluates the accuracy of the k-nearest neighbors algorithm when applied to the embeddings. This metric helps assess how well the embeddings represent the underlying data structure.

## Extrinsic Metrics

Extrinsic metrics evaluate embeddings based on their performance in downstream tasks, such as information retrieval. The following extrinsic metrics are included:

1. **Recall@k**: Measures the proportion of relevant items retrieved in the top-k results. A higher recall indicates better performance in retrieving relevant information.

2. **Mean Average Precision (MAP)**: Computes the average precision across multiple queries. It provides a single score that summarizes the precision-recall trade-off.

3. **Mean Reciprocal Rank (MRR)**: Evaluates the effectiveness of a system in retrieving relevant documents. It is the average of the reciprocal ranks of the first relevant document for a set of queries.

## Drift Metrics

Drift metrics assess changes in the distribution of embeddings over time. These metrics are important for monitoring model performance and ensuring that embeddings remain relevant:

1. **Embedding Shift (Cosine Delta)**: Measures the cosine similarity between the current and previous embedding distributions. A significant shift may indicate a need for model retraining.

2. **Coverage**: Evaluates the proportion of the data space covered by the embeddings. Low coverage may suggest that the embeddings are not adequately representing the data.

3. **Outlier Rate**: Measures the proportion of embeddings that are significantly different from the majority. A high outlier rate may indicate issues with data quality or model performance.

## Conclusion

Evaluating embeddings is a critical step in ensuring the effectiveness of natural language processing models. The metrics outlined in this document provide a comprehensive framework for assessing both intrinsic and extrinsic qualities of embeddings, as well as monitoring their stability over time.