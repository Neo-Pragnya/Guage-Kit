# Installing Guage-Kit

To install Guage-Kit, follow the steps below:

## Prerequisites

Ensure you have Python 3.9 or higher installed on your system. You can check your Python version by running:

```bash
python --version
```

## Installation Steps

1. **Clone the Repository**

   First, clone the Guage-Kit repository from GitHub:

   ```bash
   git clone https://github.com/yourusername/Guage-Kit.git
   cd Guage-Kit
   ```

2. **Install Dependencies Using UV**

   Instead of using pip, we will use UV to install the project dependencies. Run the following command:

   ```bash
   uv install -e .[dev,docs,reports]
   ```

   This command installs the core package along with optional dependencies for development, documentation, and reporting.

3. **Verify Installation**

   After installation, you can verify that Guage-Kit is installed correctly by running:

   ```bash
   guage-kit --help
   ```

   This should display the help message for the command-line interface.

## Additional Setup

- **Streamlit UI**

  To run the Streamlit UI, navigate to the `apps/guage_kit_ui` directory and run:

  ```bash
  streamlit run Home.py
  ```

- **Documentation**

  To build the documentation, navigate to the `docs` directory and run:

  ```bash
  sphinx-build -b html . _build/html
  ```

## Conclusion

You are now ready to use Guage-Kit for evaluating LLMs, RAG systems, and embeddings. For further guidance, refer to the other documentation pages available in the `docs` directory.