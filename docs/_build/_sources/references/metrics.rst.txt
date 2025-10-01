Metrics Reference
==================

This document provides an overview of the metrics available in the Guage-Kit project for evaluating LLMs, RAG systems, and embeddings.

LLM Quality Metrics
--------------------
- **ROUGE-L**: Measures the overlap of n-grams between the generated text and reference text.
- **BLEU**: A metric for evaluating the quality of text which has been machine-translated from one language to another.
- **METEOR**: A metric that evaluates machine translation by aligning generated text with reference text based on exact, stem, synonym, and paraphrase matches.

RAG Quality Metrics
--------------------
- **Faithfulness**: Evaluates the alignment between the generated answer and the context provided.
- **Answer Relevancy**: Measures the cosine similarity between the question and the generated answer embeddings.

Information Retrieval Metrics
------------------------------
- **Recall@k**: Measures the proportion of relevant items retrieved in the top-k results.
- **Precision@k**: Measures the proportion of retrieved items that are relevant in the top-k results.
- **Mean Reciprocal Rank (MRR)**: The average of the reciprocal ranks of the first relevant item for a set of queries.
- **Mean Average Precision (MAP)**: The mean of the average precision scores for each query.

Embeddings Metrics
--------------------
- **STS Spearman**: Measures the correlation between the semantic textual similarity scores of embeddings.
- **Clustering ARI/NMI**: Adjusted Rand Index and Normalized Mutual Information for evaluating clustering quality.
- **k-NN Accuracy**: Evaluates the accuracy of k-nearest neighbors classification.

Hallucination Metrics
----------------------
- **Unsupported Claim Rate**: Measures the rate of unsupported claims in generated text.
- **Hallucination Rate**: Evaluates the frequency of hallucinations in generated responses.

Safety and Bias Metrics
------------------------
- **Toxicity**: Measures the level of toxicity in generated text.
- **Bias**: Evaluates the presence of bias in the generated responses.

Calibration Metrics
--------------------
- **Expected Calibration Error (ECE)**: Measures the difference between predicted probabilities and actual outcomes.
- **Brier Score**: A measure of how close the predicted probabilities are to the actual outcomes.
- **Log Loss**: Evaluates the performance of a classification model where the prediction input is a probability value between 0 and 1.

Runtime Cost Metrics
----------------------
- **Tokens**: Counts the number of tokens processed during evaluation.
- **Latency**: Measures the time taken to generate responses.
- **Cost**: Evaluates the monetary cost associated with running the evaluation, based on the provider used.