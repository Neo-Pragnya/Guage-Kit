from guage_kit.utils.io import load_run_artifacts
import streamlit as st
import json
import os

st.title("Results Explorer")

# Directory to load run artifacts from
artifacts_dir = ".guage_kit/runs"

# List all available runs
runs = [d for d in os.listdir(artifacts_dir) if os.path.isdir(os.path.join(artifacts_dir, d))]
selected_run = st.selectbox("Select a run", runs)

if selected_run:
    run_path = os.path.join(artifacts_dir, selected_run)
    
    # Load the JSON report
    report_path = os.path.join(run_path, "last_report.json")
    if os.path.exists(report_path):
        with open(report_path) as f:
            report = json.load(f)
        
        st.subheader("Metrics Overview")
        st.json(report)

        # Display detailed metrics
        for metric, value in report.items():
            st.write(f"**{metric}**: {value}")

    else:
        st.warning("No report found for the selected run.")