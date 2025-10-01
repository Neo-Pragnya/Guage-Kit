from typing import Any, Dict, List
import pandas as pd

def normalize_data(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize the dataset by scaling features to a range of [0, 1]."""
    return (data - data.min()) / (data.max() - data.min())

def split_data(data: pd.DataFrame, train_size: float = 0.8) -> Dict[str, pd.DataFrame]:
    """Split the dataset into training and testing sets.

    Args:
        data (pd.DataFrame): The dataset to split.
        train_size (float): The proportion of the dataset to include in the training set.

    Returns:
        Dict[str, pd.DataFrame]: A dictionary containing 'train' and 'test' DataFrames.
    """
    train_size = int(len(data) * train_size)
    return {
        'train': data.iloc[:train_size],
        'test': data.iloc[train_size:]
    }