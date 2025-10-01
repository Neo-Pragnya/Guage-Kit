"""Guage-Kit Streamlit UI - Run Evaluation Page"""

import json
import yaml
import pathlib
import streamlit as st
import sys
import os

# Add the src directory to path to import guage_kit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

try:
    from guage_kit.api import evaluate
    from guage_kit.datasets.loaders import load_jsonl, load_csv
    API_AVAILABLE = True
except ImportError as e:
    st.error(f"Failed to import guage_kit: {e}")
    API_AVAILABLE = False

st.title("🏃 Run Evaluation")

if not API_AVAILABLE:
    st.error("Guage-Kit API is not available. Please check your installation.")
    st.stop()

# File upload
data_file = st.file_uploader(
    "📂 Upload Dataset", 
    type=["jsonl", "csv"], 
    help="Upload a JSONL or CSV file containing your evaluation data"
)

# Metric selection
available_metrics = [
    "rougeL", "bleu", "answer_relevancy", 
    "recall@10", "mrr", "ndcg@10", "sts_spearman"
]

metrics = st.multiselect(
    "⚙️ Select Metrics", 
    available_metrics,
    default=["rougeL", "bleu"],
    help="Choose which metrics to compute for your evaluation"
)

# Configuration
cfg_text = st.text_area(
    "🔧 Configuration (YAML or JSON)", 
    value="retrieval.k: 10",
    help="Optional configuration parameters for metrics"
)

# Report options
col1, col2 = st.columns(2)
with col1:
    save_json = st.checkbox("💾 Save JSON Report", value=True)
with col2:
    save_html = st.checkbox("📄 Save HTML Report", value=True)

# Run button
run_btn = st.button("🚀 Run Evaluation", type="primary")

def parse_config(text: str):
    try:
        return yaml.safe_load(text) if ":" in text else json.loads(text)
    except Exception:
        return {}

if run_btn and data_file and metrics:
    with st.spinner("🔄 Running evaluation..."):
        try:
            # Create uploads directory
            uploads_dir = pathlib.Path(".guage_kit/uploads")
            uploads_dir.mkdir(parents=True, exist_ok=True)
            
            # Save uploaded file
            data_path = uploads_dir / data_file.name
            data_path.write_bytes(data_file.getvalue())
            
            # Parse configuration
            config = parse_config(cfg_text)
            
            # Setup report options
            report = {}
            if save_json:
                report["json"] = f".guage_kit/last_run_{data_file.name}.json"
            if save_html:
                report["html"] = f".guage_kit/last_report_{data_file.name}.html"
            
            # Run evaluation
            scores = evaluate(
                str(data_path),
                metrics=metrics,
                config=config,
                report=report if report else None
            )
            
            # Display results
            st.success("✅ Evaluation completed!")
            
            # Show metrics in columns
            metric_cols = st.columns(len(scores))
            for i, (metric, score) in enumerate(scores.items()):
                with metric_cols[i]:
                    st.metric(metric, f"{score:.4f}")
            
            # Show detailed results
            st.subheader("📊 Detailed Results")
            st.json(scores)
            
            # Show configuration used
            if config:
                st.subheader("⚙️ Configuration Used")
                st.json(config)
            
            # Show report file locations
            if report:
                st.subheader("📁 Report Files")
                for report_type, path in report.items():
                    if pathlib.Path(path).exists():
                        st.success(f"✅ {report_type.upper()} report saved: `{path}`")
                    else:
                        st.warning(f"⚠️ {report_type.upper()} report could not be saved")
                        
        except Exception as e:
            st.error(f"❌ Evaluation failed: {str(e)}")
            st.exception(e)

elif run_btn:
    if not data_file:
        st.warning("⚠️ Please upload a dataset file")
    if not metrics:
        st.warning("⚠️ Please select at least one metric")

# Help section
with st.expander("❓ Help & Examples"):
    st.markdown("""
    ### Expected Data Format
    
    **JSONL Format:**
    ```json
    {"id": "q1", "prompt": "What is the capital of France?", "prediction": "Paris", "reference": "Paris"}
    {"id": "q2", "prompt": "Who wrote Romeo and Juliet?", "prediction": "Shakespeare", "reference": "William Shakespeare"}
    ```
    
    **CSV Format:**
    ```csv
    id,prompt,prediction,reference
    q1,"What is the capital of France?","Paris","Paris"
    q2,"Who wrote Romeo and Juliet?","Shakespeare","William Shakespeare"
    ```
    
    ### Available Metrics
    - **rougeL**: ROUGE-L overlap score
    - **bleu**: BLEU score for text similarity
    - **answer_relevancy**: Cosine similarity between question and answer
    - **recall@k**: Retrieval recall at rank k
    - **mrr**: Mean Reciprocal Rank for retrieval
    - **ndcg@k**: Normalized Discounted Cumulative Gain
    - **sts_spearman**: Spearman correlation for semantic similarity
    """)