from guage_kit.utils.io import load_run_artifacts
import streamlit as st

st.title("Compare Runs")

# File uploader for selecting run artifacts
run1_file = st.file_uploader("Upload first run artifact (JSON)", type="json")
run2_file = st.file_uploader("Upload second run artifact (JSON)", type="json")

if run1_file and run2_file:
    # Load the run artifacts
    run1_data = load_run_artifacts(run1_file)
    run2_data = load_run_artifacts(run2_file)

    # Display the metrics for both runs
    st.subheader("Run 1 Metrics")
    st.json(run1_data)

    st.subheader("Run 2 Metrics")
    st.json(run2_data)

    # Compare metrics
    st.subheader("Comparison")
    comparison = {key: (run1_data.get(key), run2_data.get(key)) for key in set(run1_data) | set(run2_data)}
    st.json(comparison)

    # Optionally, add visualizations for comparison
    # e.g., bar charts, line charts, etc. using Streamlit's charting capabilities
    st.line_chart([run1_data.get('metric_name'), run2_data.get('metric_name')], 
                   use_container_width=True)  # Replace 'metric_name' with actual metric keys

else:
    st.warning("Please upload both run artifacts to compare.")