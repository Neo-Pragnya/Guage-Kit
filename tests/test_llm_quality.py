import pytest
from guage_kit.metrics.llm_quality import calculate_rouge, calculate_bleu, calculate_meteor

def test_calculate_rouge():
    reference = "The cat sat on the mat."
    hypothesis = "The cat is sitting on the mat."
    score = calculate_rouge(reference, hypothesis)
    assert score >= 0  # ROUGE score should be non-negative

def test_calculate_bleu():
    reference = ["The cat sat on the mat."]
    hypothesis = "The cat is sitting on the mat."
    score = calculate_bleu(reference, hypothesis)
    assert score >= 0  # BLEU score should be non-negative

def test_calculate_meteor():
    reference = ["The cat sat on the mat."]
    hypothesis = "The cat is sitting on the mat."
    score = calculate_meteor(reference, hypothesis)
    assert score >= 0  # METEOR score should be non-negative

def test_calculate_rouge_edge_case():
    reference = ""
    hypothesis = ""
    score = calculate_rouge(reference, hypothesis)
    assert score == 0  # ROUGE score for empty strings should be 0

def test_calculate_bleu_edge_case():
    reference = [""]
    hypothesis = ""
    score = calculate_bleu(reference, hypothesis)
    assert score == 0  # BLEU score for empty strings should be 0

def test_calculate_meteor_edge_case():
    reference = [""]
    hypothesis = ""
    score = calculate_meteor(reference, hypothesis)
    assert score == 0  # METEOR score for empty strings should be 0