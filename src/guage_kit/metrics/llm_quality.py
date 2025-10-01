from typing import List
from sacrebleu import corpus_bleu, sentence_bleu
from rouge_score import rouge_scorer
from nltk.translate.meteor_score import meteor_score
import numpy as np

def compute_rouge(predictions: List[str], references: List[List[str]]) -> dict:
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = {key: 0 for key in ['rouge1', 'rouge2', 'rougeL']}
    
    for pred, refs in zip(predictions, references):
        score = scorer.score(pred, refs[0])  # Assuming single reference for simplicity
        for key in scores:
            scores[key] += score[key].fmeasure
            
    # Average scores
    for key in scores:
        scores[key] /= len(predictions)
    
    return scores

def compute_bleu(predictions: List[str], references: List[List[str]]) -> float:
    return corpus_bleu(predictions, references).score

def compute_meteor(predictions: List[str], references: List[List[str]]) -> float:
    return np.mean([meteor_score(refs, pred) for pred, refs in zip(predictions, references)])

def evaluate_llm_quality(predictions: List[str], references: List[List[str]]) -> dict:
    rouge_scores = compute_rouge(predictions, references)
    bleu_score = compute_bleu(predictions, references)
    meteor_score_value = compute_meteor(predictions, references)
    
    return {
        'rouge': rouge_scores,
        'bleu': bleu_score,
        'meteor': meteor_score_value
    }