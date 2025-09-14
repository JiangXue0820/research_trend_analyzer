#!/usr/bin/env python3
"""
Example usage of the Research Trend Analyzer Light Agent.
This script demonstrates how to use the agent programmatically.
"""

import logging
from configs.log_config import configure_logging
from agent.graph import run_research_workflow


def example_basic_usage():
    """Example of basic agent usage."""
    print("=== Research Trend Analyzer Light Agent - Example Usage ===\n")
    
    # Configure logging
    configure_logging(console=True, console_level=logging.INFO, colored_console=True)
    
    # Example configuration for analyzing privacy research at NeurIPS 2023
    config = {
        "conference": "neurips",
        "year": 2023,
        "topic": "privacy",
        "method": "keyword",  # or "llm" for more sophisticated filtering
        "language": "CH",     # or "EN" for English summaries
        
        # Optional configuration (will use defaults if not specified)
        "skip_keyword_generation": False,  # Set to True if keywords already exist
        "skip_crawling": False,           # Set to True if papers already crawled
        "max_papers": 10,                 # Limit for testing (None for all papers)
    }
    
    print("Running research workflow with configuration:")
    print(f"  Conference: {config['conference']}")
    print(f"  Year: {config['year']}")
    print(f"  Topic: {config['topic']}")
    print(f"  Method: {config['method']}")
    print(f"  Language: {config['language']}")
    print(f"  Max Papers: {config.get('max_papers', 'All')}")
    print()
    
    try:
        # Run the research workflow
        results = run_research_workflow(config)
        
        print("=== Workflow Results ===")
        print(f"Status: {results.get('status', 'unknown')}")
        
        if results["status"] == "completed":
            print("✅ Workflow completed successfully!")
            print(f"Conference: {results.get('conference', 'unknown')}")
            print(f"Year: {results.get('year', 'unknown')}")
            print(f"Topic: {results.get('topic', 'unknown')}")
            
            # Papers processed
            papers = results.get('papers_processed', {})
            print(f"Papers Crawled: {papers.get('crawled', 0)}")
            print(f"Papers Filtered: {papers.get('filtered', 0)}")
            print(f"Papers Summarized: {papers.get('summarized', 0)}")
            
            # Output files
            files = results.get('output_files', {})
            print(f"Keywords File: {files.get('keywords', 'N/A')}")
            print(f"Paper List: {files.get('paper_list', 'N/A')}")
            print(f"Filtered Papers: {files.get('filtered_papers', 'N/A')}")
            print(f"Summaries Directory: {files.get('summaries', 'N/A')}")
            print(f"Excel Report: {files.get('excel_report', 'N/A')}")
            
            print(f"Completion Time: {results.get('completion_time', 'unknown')}")
            
        else:
            print("❌ Workflow failed!")
            print(f"Error: {results.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.exception("Detailed error information:")


def example_advanced_usage():
    """Example of advanced agent usage with custom configuration."""
    print("\n=== Advanced Usage Example ===\n")
    
    # Custom configuration with overrides
    config = {
        "conference": "popets",
        "year": 2023,
        "topic": "differential_privacy",
        "method": "llm",      # Use LLM for more accurate filtering
        "language": "EN",     # English summaries
        
        # Custom paths (optional - will use defaults if not specified)
        "scope_list_path": "configs/analysis_scope.json",
        "paper_list_root": "papers/paper_list",
        "paper_summary_root": "papers/paper_summary",
        "temp_pdf_root": "temp/pdfs",
        
        # Workflow control
        "skip_keyword_generation": False,
        "skip_crawling": False,
        "max_papers": 5,  # Process only 5 papers for quick testing
    }
    
    print("Running advanced workflow with custom configuration...")
    
    try:
        results = run_research_workflow(config)
        
        if results["status"] == "completed":
            print("✅ Advanced workflow completed!")
            print(f"Processed {results.get('papers_processed', {}).get('summarized', 0)} papers")
        else:
            print(f"❌ Advanced workflow failed: {results.get('error_message')}")
            
    except Exception as e:
        print(f"❌ Fatal error in advanced workflow: {e}")


def example_error_handling():
    """Example demonstrating error handling."""
    print("\n=== Error Handling Example ===\n")
    
    # Invalid configuration - unknown conference
    config = {
        "conference": "unknown_conference",
        "year": 2023,
        "topic": "privacy",
    }
    
    print("Running workflow with invalid conference...")
    
    try:
        results = run_research_workflow(config)
        
        if results["status"] == "error":
            print("✅ Error handling working correctly!")
            print(f"Error message: {results.get('error_message')}")
        else:
            print("❌ Expected error but workflow completed")
            
    except Exception as e:
        print(f"❌ Unexpected fatal error: {e}")


if __name__ == "__main__":
    # Run the examples
    example_basic_usage()
    example_advanced_usage()
    example_error_handling()
    
    print("\n=== Example Usage Complete ===")
    print("\nTo run the agent from command line, use:")
    print("  python main.py --conference neurips --year 2023 --topic privacy")
    print("\nFor more options, run:")
    print("  python main.py --help")