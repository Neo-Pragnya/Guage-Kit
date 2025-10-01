"""Guage-Kit Streamlit UI - Home Page"""

import streamlit as st
import sys
import os

# Add the src directory to path to import guage_kit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def main():
    st.set_page_config(
        page_title="Guage-Kit",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🔍 Welcome to Guage-Kit")
    st.subheader("A unified, extensible toolkit for evaluating LLMs, RAG systems, and embeddings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🚀 Features
        - **LLM Quality Metrics**: ROUGE, BLEU, METEOR, BERTScore
        - **RAG Evaluation**: Faithfulness, groundedness, answer relevancy
        - **Retrieval Metrics**: Recall@k, MRR, nDCG
        - **Embedding Analysis**: STS correlation, clustering metrics
        - **Safety & Bias**: Toxicity detection, fairness metrics
        """)
        
    with col2:
        st.markdown("""
        ### 📊 Capabilities
        - Unified Python API and CLI
        - Streamlit UI for interactive evaluation
        - Comprehensive reporting (HTML/JSON)
        - Extensible plugin system
        - CI/CD integration ready
        """)
    
    st.markdown("---")
    
    st.markdown("""
    ### 🎯 Quick Start
    
    1. **📂 Upload Data**: Use the "Run Evaluation" page to upload your dataset
    2. **⚙️ Configure Metrics**: Select from our comprehensive metric catalog
    3. **🏃 Execute**: Run evaluations with configurable parameters
    4. **📈 Analyze**: Explore results and compare different runs
    
    ### 🔧 Environment Status
    """)
    
    # Environment checks
    try:
        import guage_kit
        st.success("✅ Guage-Kit core module loaded successfully")
        
        # Try importing key dependencies
        try:
            import numpy, pandas, sklearn
            st.success("✅ Core dependencies (numpy, pandas, sklearn) available")
        except ImportError as e:
            st.error(f"❌ Missing core dependencies: {e}")
            
        try:
            from guage_kit.api import evaluate
            st.success("✅ Main API function available")
        except ImportError as e:
            st.error(f"❌ API import failed: {e}")
            
    except ImportError as e:
        st.error(f"❌ Failed to import guage_kit: {e}")
        st.info("Make sure you're running from the correct environment")
    
    st.markdown("---")
    
    st.markdown("""
    ### 📚 Resources
    
    - 📖 [Documentation](https://guage-kit.readthedocs.io) (Coming soon)
    - 📝 [Jupyter Notebooks](./notebooks/) - Interactive tutorials
    - 💻 [CLI Reference](https://github.com/neo-pragnya/guage-kit) - Command line usage
    - 🐛 [Issues & Support](https://github.com/neo-pragnya/guage-kit/issues)
    """)

if __name__ == "__main__":
    main()