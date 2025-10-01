from typing import Dict, Any
import streamlit as st

def metric_card(metric_name: str, value: Any, description: str) -> None:
    """Display a metric card with the metric name, value, and description."""
    with st.card():
        st.header(metric_name)
        st.metric(label=metric_name, value=value)
        st.write(description)

def display_metrics(metrics: Dict[str, Any]) -> None:
    """Display a series of metric cards based on the provided metrics dictionary."""
    for metric_name, metric_data in metrics.items():
        metric_card(metric_name, metric_data['value'], metric_data['description'])