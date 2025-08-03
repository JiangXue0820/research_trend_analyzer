# Research Trend Analyzer 🧠

**Research Trend Analyzer** is an LLM-based agent that automates the process of crawling, storing, filtering, analyzing, and summarizing research papers—ideal for scanning academic conferences or journals (e.g., NeurIPS, ICML, ACL) to discover emerging trends.

## Features

- **Fetch and store papers** from conference proceedings (e.g. NeurIPS) into a local SQLite database.
- **Filter papers by topic or keywords** (e.g. “privacy”, “federated learning”).
- **Download, parse PDFs**, split into text chunks, and store embed documents in a FAISS-based vector database.
- **Retrieve relevant chunks** using RAG (Retrieval-Augmented Generation) for downstream Q&A or summarization.
- **Summarize research trends** across filtered papers using LLMs.

## Structure

The repository is organized into the following directories and files to ensure modularity and ease of use:

- **configs/**: Stores configuration files (e.g., API keys, fetching parameters, analysis settings) to customize tool behavior.
- **logs/**: Generates and stores logs for debugging, tracking paper fetching/analysis processes, and monitoring system performance.
- **papers/**: Serves as a local storage directory for downloaded or processed academic papers.
- **tools/**: Includes utility tools for fetching and analyzing papers.
- **utils/**: Provides helper functions and shared utilities (e.g., file handling, data parsing) used across the repository.
- **main.py**: The entry point to run the research trend analysis workflow, coordinating agents and tools.

## Installation

Follow these steps to set up the repository locally:

1. **Clone the repository**  
   ```bash
   git clone https://github.com/JiangXue0820/research_trend_analyzer.git
   cd research_trend_analyzer

2. Dependencies**  
   Install the required Python packages using pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration**  
   Update the configuration files in the `configs/.env` directory with your API keys and preferences for fetching and analyzing papers.

## Usage 

Run the main script to start the research trend analysis process:
```bash
   python main.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
