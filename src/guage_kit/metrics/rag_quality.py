from typing import Any, Dict, List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from ..schemas.core import EvalSample

def faithfulness(reference: str, generated: str) -> float:
    """Calculate faithfulness score based on cosine similarity."""
    # Simple TF-IDF based similarity for now
    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    try:
        tfidf_matrix = vectorizer.fit_transform([reference, generated])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)
    except:
        return 0.0

def answer_relevancy(query: str, answer: str) -> float:
    """Calculate answer relevancy score based on cosine similarity."""
    # Simple TF-IDF based similarity for now
    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    try:
        tfidf_matrix = vectorizer.fit_transform([query, answer])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)
    except:
        return 0.0


def compute_answer_relevancy(eval_samples: List[EvalSample]) -> float:
    """Compute answer relevancy across multiple evaluation samples."""
    if not eval_samples:
        return 0.0
    
    scores = []
    for sample in eval_samples:
        query_text = sample.query.prompt
        answer_text = sample.generation.text
        score = answer_relevancy(query_text, answer_text)
        scores.append(score)
    
    return np.mean(scores) if scores else 0.0


def rag_quality_metrics(query: str, reference: str, generated: str) -> Dict[str, Any]:
    """Compute RAG quality metrics."""
    return {
        "faithfulness": faithfulness(reference, generated),
        "answer_relevancy": answer_relevancy(query, generated)
    }