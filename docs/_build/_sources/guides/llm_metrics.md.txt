# LLM Metrics in Guage-Kit

## Overview

The Guage-Kit project provides a comprehensive toolkit for evaluating Large Language Models (LLMs) using various metrics. This document outlines the key metrics related to LLM quality that are implemented in the project.

## Metrics

### 1. ROUGE-L

ROUGE-L (Recall-Oriented Understudy for Gisting Evaluation) is a metric for evaluating the quality of summaries by comparing them to reference summaries. It measures the longest common subsequence between the generated text and the reference text, providing a score that reflects the overlap in content.

### 2. BLEU

BLEU (Bilingual Evaluation Understudy) is a metric primarily used for evaluating machine translation. It compares n-grams of the generated text against n-grams of reference texts, calculating a score based on precision and applying a brevity penalty to account for shorter translations.

### 3. METEOR

METEOR (Metric for Evaluation of Translation with Explicit ORdering) is designed to improve upon BLEU by considering synonyms and stemming. It aligns generated text with reference text based on word matches and calculates a score that reflects both precision and recall.

### 4. FKGL Readability

The Flesch-Kincaid Grade Level (FKGL) is a readability test designed to indicate the understandability of English texts. It calculates a score based on the average number of syllables per word and the average number of words per sentence, providing an estimate of the grade level required to understand the text.

## Usage

To evaluate LLM quality using these metrics, you can use the `evaluate` function from the `guage_kit.api` module. Specify the metrics you want to use in your evaluation configuration.

### Example

```python
from guage_kit.api import evaluate

data = [...]  # Your evaluation data
metrics = ["rougeL", "bleu", "meteor"]
results = evaluate(data, metrics)
```

## Conclusion

The LLM quality metrics implemented in Guage-Kit provide a robust framework for assessing the performance of language models. By leveraging these metrics, users can gain insights into the quality and effectiveness of their models in generating coherent and relevant text.