from typing import List

try:
    from sacrebleu import corpus_bleu
    HAS_SACREBLEU = True
except ImportError:
    HAS_SACREBLEU = False

try:
    from rouge_score import rouge_scorer
    HAS_ROUGE_SCORE = True
except ImportError:
    HAS_ROUGE_SCORE = False
    HAS_ROUGE_SCORE = True
except ImportError:
    HAS_ROUGE_SCORE = False


def compute_rouge(predictions: List[str], references: List[List[str]]) -> dict:
    """Compute ROUGE scores (ROUGE-1, ROUGE-2, ROUGE-L)."""
    if not HAS_ROUGE_SCORE:
        raise ImportError("rouge-score is required for ROUGE metrics. Install with: pip install rouge-score")
    
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = {key: 0 for key in ['rouge1', 'rouge2', 'rougeL']}

    for pred, refs in zip(predictions, references):
        score = scorer.score(pred, refs[0])  # Assuming single reference for simplicity
        for key in scores:
            scores[key] += score[key].fmeasure

    # Average scores
    if len(predictions) > 0:
        for key in scores:
            scores[key] /= len(predictions)

    return scores


def compute_bleu(predictions: List[str], references: List[List[str]]) -> float:
    """Compute corpus-level BLEU score."""
    if not HAS_SACREBLEU:
        raise ImportError("sacrebleu is required for BLEU metrics. Install with: pip install sacrebleu")
    
    # Convert to format expected by sacrebleu
    refs_by_sentence = []
    for i in range(len(references[0]) if references else 0):
        refs_by_sentence.append([ref[i] for ref in references])
    
    bleu = corpus_bleu(predictions, refs_by_sentence)
    return bleu.score / 100.0  # Convert to 0-1 scale

def compute_meteor(predictions: List[str], references: List[List[str]]) -> float:
    """Compute METEOR score (requires external dependencies)."""
    try:
        from nltk.translate.meteor_score import meteor_score
        import numpy as np
        return np.mean([meteor_score(refs, pred) for pred, refs in zip(predictions, references)])
    except ImportError:
        raise ImportError("NLTK and numpy are required for METEOR metrics. Install with: pip install nltk numpy")

def evaluate_llm_quality(predictions: List[str], references: List[List[str]]) -> dict:
    """Evaluate LLM quality using multiple metrics."""
    rouge_scores = compute_rouge(predictions, references)
    bleu_score = compute_bleu(predictions, references)
    
    try:
        meteor_score_value = compute_meteor(predictions, references)
    except ImportError:
        meteor_score_value = None
    
    result = {
        'rouge': rouge_scores,
        'bleu': bleu_score,
    }
    
    if meteor_score_value is not None:
        result['meteor'] = meteor_score_value
    
    return result