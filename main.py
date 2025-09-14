#!/usr/bin/env python3
"""
Main entry point for the Research Trend Analyzer Light Agent system.
This module provides the primary interface for running research trend analysis workflows.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
from configs.log_config import configure_logging

# Import the agent components
from agent.graph import run_research_workflow, get_workflow_visualization
from agent.state import ResearchWorkflowConfig


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Research Trend Analyzer Light Agent - Analyze research trends using langgraph"
    )
    
    # Required arguments
    parser.add_argument("--conference", "-c", required=True, 
                       help="Conference name (e.g., neurips, popets, usenix_security)")
    parser.add_argument("--year", "-y", type=int, required=True,
                       help="Conference year")
    parser.add_argument("--topic", "-t", required=True,
                       help="Research topic to analyze")
    
    # Optional arguments
    parser.add_argument("--method", "-m", default="llm", choices=["keyword", "llm"],
                       help="Filtering method: 'keyword' or 'llm' (default: llm)")
    parser.add_argument("--language", "-l", default="CH", choices=["CH", "EN"],
                       help="Summary language: 'CH' for Chinese, 'EN' for English (default: CH)")
    
    # LLM configuration
    parser.add_argument("--model-name", default="gemini-2.5-pro",
                       help="LLM model name (default: gemini-2.5-pro)")
    parser.add_argument("--api", default="gemini", choices=["mlops", "gemini"],
                       help="LLM API provider: 'mlops', or 'gemini' (default: gemini)")
    
    # Configuration overrides
    parser.add_argument("--scope-list-path", default="configs/scope_list.json",
                       help="Path to analysis scope JSON file")
    parser.add_argument("--paper-list-root", default="papers/paper_list",
                       help="Root directory for paper lists")
    parser.add_argument("--paper-summary-root", default="papers/paper_summary",
                       help="Root directory for paper summaries")
    parser.add_argument("--temp-pdf-root", default="papers/temp",
                       help="Temporary directory for PDF downloads")
    
    # Workflow control
    parser.add_argument("--skip-keyword-generation", action="store_true",
                       help="Skip keyword generation if keywords already exist")
    parser.add_argument("--skip-crawling", action="store_true",
                       help="Skip paper crawling if papers already exist")
    parser.add_argument("--max-papers", type=int,
                       help="Maximum number of papers to process (for testing)")
    
    # Output and logging
    parser.add_argument("--output", "-o", 
                       help="Output file for results (JSON format)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--visualize", action="store_true",
                       help="Display workflow graph visualization")
    
    return parser.parse_args()


def create_config_from_args(args) -> Dict[str, Any]:
    """Create workflow configuration from command line arguments."""
    config = {
        "conference": args.conference,
        "year": args.year,
        "topic": args.topic,
        "method": args.method,
        "language": args.language,
        "skip_keyword_generation": args.skip_keyword_generation,
        "skip_crawling": args.skip_crawling,
        "model_name": args.model_name,
        "api": args.api,
    }
    
    # Add optional configuration overrides if provided
    if args.scope_list_path:
        config["scope_list_path"] = args.scope_list_path
    if args.paper_list_root:
        config["paper_list_root"] = args.paper_list_root
    if args.paper_summary_root:
        config["paper_summary_root"] = args.paper_summary_root
    if args.temp_pdf_root:
        config["temp_pdf_root"] = args.temp_pdf_root
    if args.max_papers:
        config["max_papers"] = args.max_papers
    
    return config


def save_results(results: Dict[str, Any], output_path: str):
    """Save workflow results to a JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logging.info(f"Results saved to: {output_path}")
    except Exception as e:
        logging.error(f"Failed to save results to {output_path}: {e}")


def display_visualization():
    """Display the workflow graph visualization."""
    try:
        visualization = get_workflow_visualization()
        if visualization:
            print("\n=== Workflow Graph Visualization ===\n")
            print(visualization)
            print("\n" + "="*50)
        else:
            print("Could not generate workflow visualization")
    except Exception as e:
        logging.error(f"Failed to display visualization: {e}")


def main():
    """Main entry point for the research trend analyzer agent."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    configure_logging(console=True, console_level=log_level, colored_console=True)
    
    # Display visualization if requested
    if args.visualize:
        display_visualization()
        return
    
    logging.info("Starting Research Trend Analyzer Light Agent")
    logging.info(f"Conference: {args.conference}, Year: {args.year}, Topic: {args.topic}")
    
    try:
        # Create configuration from arguments
        config = create_config_from_args(args)
        
        # Validate configuration
        ResearchWorkflowConfig(**config)  # This will raise validation errors if invalid
        
        # Run the research workflow
        results = run_research_workflow(config)
        
        # Display results
        print("\n=== Workflow Results ===")
        print(f"Status: {results.get('status', 'unknown')}")
        
        if results["status"] == "completed":
            print(f"Conference: {results.get('conference', 'unknown')}")
            print(f"Year: {results.get('year', 'unknown')}")
            print(f"Topic: {results.get('topic', 'unknown')}")
            print(f"Papers Processed: {json.dumps(results.get('papers_processed', {}), indent=2)}")
            print(f"Output Files: {json.dumps(results.get('output_files', {}), indent=2)}")
            print(f"Completion Time: {results.get('completion_time', 'unknown')}")
        else:
            print(f"Error: {results.get('error_message', 'Unknown error')}")
        
        # Save results to file if requested
        if args.output:
            save_results(results, args.output)
        
        # Return appropriate exit code
        return 0 if results["status"] == "completed" else 1
        
    except Exception as e:
        logging.exception(f"Fatal error in research workflow: {e}")
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())