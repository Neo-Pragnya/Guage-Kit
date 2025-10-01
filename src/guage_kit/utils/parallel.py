from typing import Callable, List
import multiprocessing

def parallel_map(func: Callable, iterable: List, num_workers: int = None) -> List:
    if num_workers is None:
        num_workers = multiprocessing.cpu_count()
    
    with multiprocessing.Pool(processes=num_workers) as pool:
        results = pool.map(func, iterable)
    
    return results

def parallel_batch(func: Callable, data: List, batch_size: int, num_workers: int = None) -> List:
    if num_workers is None:
        num_workers = multiprocessing.cpu_count()
    
    batches = [data[i:i + batch_size] for i in range(0, len(data), batch_size)]
    
    with multiprocessing.Pool(processes=num_workers) as pool:
        results = pool.map(func, batches)
    
    return results