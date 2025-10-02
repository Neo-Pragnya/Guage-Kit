from typing import List, Any
import numpy as np
from scipy.stats import spearmanr
from ..schemas.core import EvalSample

def sts_spearman(reference_embeddings: List[List[float]], candidate_embeddings: List[List[float]]) -> float:
    """Calculate the Spearman correlation coefficient between reference and candidate embeddings.

    Args:
        reference_embeddings (List[List[float]]): A list of reference embeddings.
        candidate_embeddings (List[List[float]]): A list of candidate embeddings.

    Returns:
        float: The Spearman correlation coefficient.
    """
    if len(reference_embeddings) != len(candidate_embeddings):
        raise ValueError("Reference and candidate embeddings must have the same length.")

    # Calculate Spearman correlation
    correlation, _ = spearmanr(reference_embeddings, candidate_embeddings, axis=0)
    return correlation


def compute_sts_spearman(eval_samples: List[EvalSample]) -> float:
    """Compute STS Spearman correlation across evaluation samples.
    
    This is a placeholder implementation that computes similarity between
    query and generation texts using simple character-level features.
    """
    if not eval_samples:
        return 0.0
    
    # Simple character-level features as a proxy for embeddings
    query_features = []
    generation_features = []
    
    for sample in eval_samples:
        query_text = sample.query.prompt
        gen_text = sample.generation.text
        
        # Simple features: length, character counts, etc.
        q_feat = [
            len(query_text),
            query_text.count(' '),
            query_text.count('.'),
            query_text.count('?'),
            len(set(query_text.lower()))
        ]
        
        g_feat = [
            len(gen_text),
            gen_text.count(' '),
            gen_text.count('.'),
            gen_text.count('?'),
            len(set(gen_text.lower()))
        ]
        
        query_features.append(q_feat)
        generation_features.append(g_feat)
    
    try:
        correlation, _ = spearmanr(query_features, generation_features, axis=0)
        return float(np.mean(correlation) if hasattr(correlation, '__iter__') else correlation)
    except (ValueError, TypeError, AttributeError):
        return 0.0


def intrinsic_metrics(embeddings: List[List[float]]) -> dict[str, Any]:
    """Calculate intrinsic metrics for embeddings.

    Args:
        embeddings (List[List[float]]): A list of embeddings.

    Returns:
        dict[str, Any]: A dictionary containing intrinsic metrics.
    """
    # Example metric: mean and std deviation of embeddings
    mean_embedding = np.mean(embeddings, axis=0)
    std_embedding = np.std(embeddings, axis=0)

    return {
        "mean": mean_embedding,
        "std": std_embedding,
    }

def evaluate_embeddings(reference_embeddings: List[List[float]], candidate_embeddings: List[List[float]]) -> dict[str, Any]:
    """Evaluate embeddings using various metrics.

    Args:
        reference_embeddings (List[List[float]]): A list of reference embeddings.
        candidate_embeddings (List[List[float]]): A list of candidate embeddings.

    Returns:
        dict[str, Any]: A dictionary containing evaluation results.
    """
    results = {}
    results["sts_spearman"] = sts_spearman(reference_embeddings, candidate_embeddings)
    results.update(intrinsic_metrics(candidate_embeddings))
    return results