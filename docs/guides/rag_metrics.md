# RAG Metrics Documentation

## Overview

This document provides an overview of the metrics used to evaluate Retrieval-Augmented Generation (RAG) systems. RAG systems combine the strengths of retrieval-based and generation-based approaches to improve the quality and relevance of generated responses.

## Key Metrics

### 1. Faithfulness

Faithfulness measures how accurately the generated response reflects the information present in the retrieved context. It assesses whether the generated content is supported by the retrieved documents.

- **Metric Calculation**: 
  - Compare the generated response with the relevant context.
  - Use human judges or automated methods (e.g., Natural Language Inference) to evaluate alignment.

### 2. Groundedness

Groundedness evaluates the extent to which the generated response is based on the retrieved context. A grounded response should directly reference or be supported by the retrieved documents.

- **Metric Calculation**: 
  - Analyze the overlap between the generated response and the retrieved context.
  - Use cosine similarity between embeddings of the response and context.

### 3. Answer Relevancy

Answer relevancy measures how relevant the generated response is to the original query. This metric ensures that the response addresses the user's question effectively.

- **Metric Calculation**: 
  - Calculate the cosine similarity between the query and the generated response embeddings.
  - Higher similarity indicates better relevancy.

### 4. Retrieval Metrics

These metrics evaluate the performance of the retrieval component in the RAG system.

- **Recall@k**: Measures the proportion of relevant documents retrieved in the top-k results.
- **Precision@k**: Measures the proportion of retrieved documents that are relevant in the top-k results.
- **Mean Reciprocal Rank (MRR)**: Averages the reciprocal ranks of the first relevant document across queries.
- **Mean Average Precision (MAP)**: Averages the precision scores at each relevant document across queries.
- **Normalized Discounted Cumulative Gain (nDCG)**: Evaluates the ranking quality of the retrieved documents based on their relevance.

## Conclusion

Evaluating RAG systems requires a combination of metrics that assess both the quality of the generated responses and the effectiveness of the retrieval process. By using these metrics, developers can gain insights into the performance of their RAG systems and make informed improvements.