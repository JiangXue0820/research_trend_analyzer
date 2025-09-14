# Research Trend Analyzer Light Agent

A langgraph-based agent system for analyzing research trends in academic conferences. This project provides a modern langchain agent architecture with English documentation and langgraph compatibility for research paper analysis.

## Features

- **Keyword Generation**: Generate research keywords for specific topics using LLMs
- **Paper Crawling**: Fetch papers from academic conferences (NeurIPS, PoPETs, USENIX, ACL)
- **Paper Filtering**: Filter papers by topic relevance using keyword matching or LLM assessment
- **Paper Summarization**: Download PDFs, extract content, and generate summaries in both English and Chinese
- **Summary Aggregation**: Structure and aggregate summaries into Excel reports
- **Langgraph Workflow**: Orchestrated workflow with state management and error handling

## Project Structure

```
research_trend_analyzer_light_agent/
├── agent/                    # Langgraph agent components
│   ├── state.py             # Workflow state definition
│   ├── nodes.py             # Workflow nodes implementation
│   └── graph.py             # Langgraph construction
├── configs/                  # Configuration files
│   ├── __init__.py
│   ├── llm_provider.py      # LLM configuration for langchain
│   ├── log_config.py        # Logging configuration
│   └── analysis_scope.json  # Research topics and keywords
├── tools/                    # Langchain tools
│   ├── keywords_generator.py
│   ├── paper_crawler.py
│   ├── paper_filter.py
│   ├── paper_summarizer.py
│   └── summary_aggregator.py
├── utils/                    # Utility functions
│   ├── __init__.py
│   ├── call_llms.py         # Langchain-compatible LLM calling
│   ├── helper_func.py       # File operations and utilities
│   ├── paper_process.py     # PDF processing utilities
│   └── prompts.py          # LLM prompts
├── tests/                   # Unit tests
│   └── test_workflow.py
├── main.py                  # Main entry point (CLI)
├── example_usage.py         # Programmatic usage examples
├── run_tests.py            # Test runner
├── requirements.txt        # Dependencies
└── .env.example           # Environment variables template
```

## Installation

1. **Clone and setup**:
   ```bash
   cd research_trend_analyzer_light_agent
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example configs/.env
   # Edit .env with your API keys and configurations
   ```

## Usage

### Command Line Interface

```bash
# Basic usage
python main.py --conference neurips --year 2023 --topic dp_theory

# Advanced options
python main.py --conference popets --year 2023 --topic usable_privacy \
               --method llm --language EN --output results.json

# Skip existing steps
python main.py --conference neurips --year 2023 --topic AI_audit \
               --skip-keyword-generation --skip-crawling

# Display help
python main.py --help
```

### Programmatic Usage

```python
from agent.graph import run_research_workflow

# Run workflow programmatically
config = {
    "conference": "neurips",
    "year": 2023,
    "topic": "privacy",
    "method": "llm",
    "language": "CH",
    "max_papers": 10  # Optional: limit for testing
}

results = run_research_workflow(config)
print(f"Workflow status: {results['status']}")
```

### Example Workflow

```python
from example_usage import example_basic_usage, example_advanced_usage

# Run examples
example_basic_usage()
example_advanced_usage()
```

## Supported Conferences

- **NeurIPS** (Neural Information Processing Systems)
- **PoPETs** (Proceedings on Privacy Enhancing Technologies)
- **USENIX Security** (USENIX Security Symposium)
- **USENIX SOUPS** (Symposium on Usable Privacy and Security)
- **ACL Long** (ACL Anthology Long Papers)
- **ACL Findings** (ACL Anthology Findings Papers)

## Configuration

### Environment Variables

Create a `.env` file with your API keys:

```env
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Analysis Scope

Edit `configs/analysis_scope.json` to define research topics:

```json
{
  "privacy": {
    "definition": "Privacy and data protection research",
    "keywords": ["privacy", "data protection", "encryption", "differential privacy"]
  },
  "machine_learning": {
    "definition": "Machine learning and AI research",
    "keywords": ["machine learning", "ai", "neural networks", "deep learning"]
  }
}
```

## Workflow Steps

1. **Keyword Generation**: Generate keywords for the research topic
2. **Paper Crawling**: Fetch papers from the specified conference and year
3. **Paper Filtering**: Filter papers by topic relevance
4. **Paper Summarization**: Download PDFs and generate summaries
5. **Summary Aggregation**: Create structured Excel reports

## Error Handling

The agent includes comprehensive error handling:
- Graceful failure with detailed error messages
- State preservation for resumable workflows
- Logging for debugging and monitoring

## Testing

Run the test suite:

```bash
python run_tests.py
```

Or run individual tests:

```bash
python -m unittest tests.test_workflow
```

## Dependencies

- **langchain**: Agent framework and tool integration
- **langgraph**: Workflow orchestration and state management
- **pydantic**: Data validation and configuration management
- **requests**: HTTP requests for paper crawling
- **pymupdf**: PDF parsing and text extraction
- **pandas**: Data analysis and Excel export
- **tqdm**: Progress bars for long-running operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper testing
4. Submit a pull request

## License

This project is built upon the original `research_trend_analyzer_light` codebase and maintains compatibility with its functionality while adding langchain agent capabilities.

## Acknowledgments

- Original `research_trend_analyzer_light` project for the core functionality
- Langchain and Langgraph teams for the excellent agent frameworks
- Academic conferences for providing open access to research papers