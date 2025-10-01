from typing import List, Dict
import numpy as np
from ..schemas.core import EvalSample

def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Calculate Recall@k metric.

    Args:
        retrieved (List[str]): List of retrieved document IDs.
        relevant (List[str]): List of relevant document IDs.
        k (int): The number of top retrieved documents to consider.

    Returns:
        float: Recall@k score.
    """
    if k > len(retrieved):
        k = len(retrieved)
    retrieved_at_k = set(retrieved[:k])
    relevant_set = set(relevant)
    true_positives = len(retrieved_at_k.intersection(relevant_set))
    return true_positives / len(relevant_set) if relevant_set else 0.0

def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Calculate Precision@k metric.

    Args:
        retrieved (List[str]): List of retrieved document IDs.
        relevant (List[str]): List of relevant document IDs.
        k (int): The number of top retrieved documents to consider.

    Returns:
        float: Precision@k score.
    """
    if k > len(retrieved):
        k = len(retrieved)
    retrieved_at_k = set(retrieved[:k])
    relevant_set = set(relevant)
    true_positives = len(retrieved_at_k.intersection(relevant_set))
    return true_positives / k if k > 0 else 0.0

def mean_average_precision(retrieved: List[List[str]], relevant: List[List[str]]) -> float:
    """Calculate Mean Average Precision (MAP).

    Args:
        retrieved (List[List[str]]): List of lists of retrieved document IDs for each query.
        relevant (List[List[str]]): List of lists of relevant document IDs for each query.

    Returns:
        float: Mean Average Precision score.
    """
    average_precisions = []
    for r, rel in zip(retrieved, relevant):
        ap = 0.0
        for k in range(1, len(r) + 1):
            if r[k - 1] in rel:
                ap += precision_at_k(r, rel, k)
        average_precisions.append(ap / len(rel) if rel else 0.0)
    return sum(average_precisions) / len(average_precisions) if average_precisions else 0.0


def compute_recall_at_k(eval_samples: List[EvalSample], k: int) -> float:
    """Compute Recall@k across multiple evaluation samples."""
    if not eval_samples:
        return 0.0
    
    scores = []
    for sample in eval_samples:
        if sample.retrieval and sample.query.references:
            retrieved_ids = [chunk.id for chunk in sample.retrieval.chunks]
            relevant_ids = sample.query.references
            score = recall_at_k(retrieved_ids, relevant_ids, k)
            scores.append(score)
    
    return np.mean(scores) if scores else 0.0


def compute_mrr(eval_samples: List[EvalSample]) -> float:
    """Compute Mean Reciprocal Rank across multiple evaluation samples."""
    if not eval_samples:
        return 0.0
    
    reciprocal_ranks = []
    for sample in eval_samples:
        if sample.retrieval and sample.query.references:
            retrieved_ids = [chunk.id for chunk in sample.retrieval.chunks]
            relevant_ids = set(sample.query.references)
            
            # Find the rank of the first relevant item
            for i, doc_id in enumerate(retrieved_ids, 1):
                if doc_id in relevant_ids:
                    reciprocal_ranks.append(1.0 / i)
                    break
            else:
                reciprocal_ranks.append(0.0)
    
    return np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0


def compute_ndcg(eval_samples: List[EvalSample], k: int) -> float:
    """Compute Normalized Discounted Cumulative Gain@k."""
    if not eval_samples:
        return 0.0
    
    ndcg_scores = []
    for sample in eval_samples:
        if sample.retrieval and sample.query.references:
            retrieved_ids = [chunk.id for chunk in sample.retrieval.chunks[:k]]
            relevant_ids = set(sample.query.references)
            
            # Simple binary relevance (1 if relevant, 0 if not)
            relevance_scores = [1.0 if doc_id in relevant_ids else 0.0 for doc_id in retrieved_ids]
            
            # DCG calculation
            dcg = 0.0
            for i, rel in enumerate(relevance_scores):
                dcg += rel / np.log2(i + 2)  # i+2 because log2(1) is 0
            
            # IDCG calculation (perfect ranking)
            ideal_relevance = sorted(relevance_scores, reverse=True)
            idcg = 0.0
            for i, rel in enumerate(ideal_relevance):
                idcg += rel / np.log2(i + 2)
            
            ndcg = dcg / idcg if idcg > 0 else 0.0
            ndcg_scores.append(ndcg)
    
    return np.mean(ndcg_scores) if ndcg_scores else 0.0


# Additional metrics can be added here as needed.