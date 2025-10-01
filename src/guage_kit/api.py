"""Main API for the Guage-Kit evaluation toolkit."""

from typing import Iterable, Mapping, Any, Union, List, Optional
import json
import pathlib
from .schemas.core import EvalSample, Query, Generation, RetrievalResult
from .datasets.loaders import load_jsonl, load_csv
from .metrics.llm_quality import compute_rouge, compute_bleu
from .metrics.retrieval_ir import compute_recall_at_k, compute_mrr, compute_ndcg
from .metrics.rag_quality import compute_answer_relevancy
from .metrics.embeddings import compute_sts_spearman


def evaluate(
    data: Union[Iterable[EvalSample], str],
    metrics: List[str],
    config: Optional[Mapping[str, Any]] = None,
    parallelism: int = 1,
    report: Optional[Mapping[str, str]] = None,
) -> dict[str, float]:
    """Run selected metrics and return aggregated scores.
    
    Args:
        data: Either an iterable of EvalSample objects or a path to a data file
        metrics: List of metric names to compute (e.g., ['rougeL', 'bleu', 'recall@10'])
        config: Optional configuration dictionary for metric parameters
        parallelism: Number of parallel workers (currently not implemented)
        report: Optional dictionary mapping report types to file paths
        
    Returns:
        Dictionary mapping metric names to their computed scores
    """
    if config is None:
        config = {}
        
    # Load data if provided as string path
    if isinstance(data, str):
        data_path = pathlib.Path(data)
        if data_path.suffix == '.jsonl':
            raw_data = load_jsonl(data_path)
        elif data_path.suffix == '.csv':
            raw_data = load_csv(data_path)
        else:
            raise ValueError(f"Unsupported file format: {data_path.suffix}")
            
        # Convert raw data to EvalSample objects
        eval_samples = []
        for item in raw_data:
            # Handle different data formats
            if 'query' in item and 'generation' in item:
                # Already in the right format
                query = Query(**item['query'])
                generation = Generation(**item['generation'])
                retrieval = None
                if 'retrieval' in item and item['retrieval']:
                    retrieval = RetrievalResult(**item['retrieval'])
                eval_samples.append(EvalSample(query=query, generation=generation, retrieval=retrieval))
            else:
                # Simple format conversion
                query = Query(
                    id=item.get('id', str(len(eval_samples))),
                    prompt=item.get('prompt', item.get('question', '')),
                    references=item.get('references', [item.get('reference')] if item.get('reference') else None)
                )
                generation = Generation(
                    query_id=query.id,
                    text=item.get('prediction', item.get('answer', '')),
                    model=item.get('model', None)
                )
                eval_samples.append(EvalSample(query=query, generation=generation))
        
        data = eval_samples
    
    # Convert to list if iterator
    if not isinstance(data, list):
        data = list(data)
    
    # Compute metrics
    results = {}
    
    for metric in metrics:
        if metric == 'rougeL':
            predictions = [sample.generation.text for sample in data]
            references = []
            for sample in data:
                if sample.query.references:
                    references.append(sample.query.references)
                else:
                    references.append([''])  # Empty reference if none provided
            rouge_scores = compute_rouge(predictions, references)
            results['rougeL'] = rouge_scores.get('rougeL', 0.0)
            
        elif metric == 'bleu':
            predictions = [sample.generation.text for sample in data]
            references = []
            for sample in data:
                if sample.query.references:
                    references.append(sample.query.references)
                else:
                    references.append([''])
            bleu_score = compute_bleu(predictions, references)
            results['bleu'] = bleu_score
            
        elif metric.startswith('recall@'):
            k = int(metric.split('@')[1]) if '@' in metric else config.get('retrieval.k', 10)
            recall_score = compute_recall_at_k(data, k)
            results[metric] = recall_score
            
        elif metric == 'mrr':
            mrr_score = compute_mrr(data)
            results['mrr'] = mrr_score
            
        elif metric.startswith('ndcg@'):
            k = int(metric.split('@')[1]) if '@' in metric else config.get('retrieval.k', 10)
            ndcg_score = compute_ndcg(data, k)
            results[metric] = ndcg_score
            
        elif metric == 'sts_spearman':
            sts_score = compute_sts_spearman(data)
            results['sts_spearman'] = sts_score
            
        elif metric == 'answer_relevancy':
            relevancy_score = compute_answer_relevancy(data)
            results['answer_relevancy'] = relevancy_score
            
        else:
            raise ValueError(f"Unknown metric: {metric}")
    
    # Save reports if requested
    if report:
        if 'json' in report:
            with open(report['json'], 'w') as f:
                json.dump({
                    'metrics': results,
                    'config': config,
                    'num_samples': len(data)
                }, f, indent=2)
        
        if 'html' in report:
            # Simple HTML report
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Guage-Kit Evaluation Report</title></head>
            <body>
            <h1>Evaluation Results</h1>
            <h2>Metrics</h2>
            <ul>
            {''.join(f'<li>{k}: {v:.4f}</li>' for k, v in results.items())}
            </ul>
            <h2>Configuration</h2>
            <pre>{json.dumps(config, indent=2)}</pre>
            <p>Number of samples: {len(data)}</p>
            </body>
            </html>
            """
            with open(report['html'], 'w') as f:
                f.write(html_content)
    
    return results