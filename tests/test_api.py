from src.guage_kit.api import evaluate
import pytest

def test_evaluate_with_valid_data():
    data = [
        {
            "query": {
                "id": "q1",
                "prompt": "What is CRISPR?",
                "references": ["A genome editing tool"]
            },
            "retrieval": {
                "query_id": "q1",
                "chunks": [
                    {"id": "c1", "text": "CRISPR is a genome editing tool...", "source": "wiki"}
                ]
            },
            "generation": {
                "query_id": "q1",
                "text": "CRISPR is a genome editing technology.",
                "model": "my-llm"
            }
        }
    ]
    metrics = ["rougeL", "bleu"]
    config = None
    report = None

    scores = evaluate(data, metrics, config, report=report)
    
    assert isinstance(scores, dict)
    assert all(metric in scores for metric in metrics)

def test_evaluate_with_empty_data():
    data = []
    metrics = ["rougeL"]
    config = None
    report = None

    scores = evaluate(data, metrics, config, report=report)

    assert scores == {}

def test_evaluate_with_invalid_metrics():
    data = [
        {
            "query": {
                "id": "q1",
                "prompt": "What is CRISPR?",
                "references": ["A genome editing tool"]
            },
            "retrieval": {
                "query_id": "q1",
                "chunks": [
                    {"id": "c1", "text": "CRISPR is a genome editing tool...", "source": "wiki"}
                ]
            },
            "generation": {
                "query_id": "q1",
                "text": "CRISPR is a genome editing technology.",
                "model": "my-llm"
            }
        }
    ]
    metrics = ["invalid_metric"]
    config = None
    report = None

    with pytest.raises(ValueError):
        evaluate(data, metrics, config, report=report)