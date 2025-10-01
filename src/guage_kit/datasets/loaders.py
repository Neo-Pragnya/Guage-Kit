from typing import Union, List
import pandas as pd
import json
import csv
import pathlib

def load_jsonl(file_path: Union[str, pathlib.Path]) -> List[dict]:
    data = []
    with open(file_path, 'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data

def load_csv(file_path: Union[str, pathlib.Path]) -> List[dict]:
    data = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

def load_parquet(file_path: Union[str, pathlib.Path]) -> List[dict]:
    return pd.read_parquet(file_path).to_dict(orient='records')

def load_path(file_path: Union[str, pathlib.Path]) -> List[dict]:
    ext = pathlib.Path(file_path).suffix
    if ext == '.jsonl':
        return load_jsonl(file_path)
    elif ext == '.csv':
        return load_csv(file_path)
    elif ext == '.parquet':
        return load_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")