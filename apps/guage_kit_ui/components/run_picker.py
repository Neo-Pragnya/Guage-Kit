from typing import List
import streamlit as st

def run_picker(runs: List[str], selected_run: str) -> str:
    """Display a dropdown to select a run from the available runs."""
    selected_run = st.selectbox("Select a Run", runs, index=0)
    return selected_run

# Example usage within a Streamlit app
if __name__ == "__main__":
    available_runs = ["Run 1", "Run 2", "Run 3"]  # This should be populated dynamically
    selected_run = run_picker(available_runs, "")
    st.write(f"You selected: {selected_run}")