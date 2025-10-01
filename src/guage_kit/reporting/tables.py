from typing import List
import pandas as pd

def generate_summary_table(data: List[dict]) -> pd.DataFrame:
    """Generate a summary table from evaluation data."""
    df = pd.DataFrame(data)
    summary = df.describe(include='all')
    return summary

def generate_metric_table(metrics: dict) -> pd.DataFrame:
    """Generate a table for metrics."""
    df = pd.DataFrame(metrics.items(), columns=['Metric', 'Score'])
    return df

def save_table_to_csv(table: pd.DataFrame, filename: str) -> None:
    """Save a DataFrame table to a CSV file."""
    table.to_csv(filename, index=False)

def save_table_to_excel(table: pd.DataFrame, filename: str) -> None:
    """Save a DataFrame table to an Excel file."""
    table.to_excel(filename, index=False)

def format_table_for_display(table: pd.DataFrame) -> str:
    """Format a DataFrame table for display."""
    return table.to_string(index=False)