from typing import Dict, Any, List, Optional
import logging
import time
from datetime import datetime
from pathlib import Path

from .state import ResearchWorkflowState, update_state_progress, update_state_error
from tools.keywords_generator import KeywordsGeneratorTool
from tools.paper_crawler import PaperCrawlerTool
from tools.paper_filter import PaperFilterTool
from tools.paper_summarizer import PaperSummarizerTool
from tools.summary_aggregator import SummaryAggregatorTool


def generate_keywords_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node for generating research keywords for the given topic.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated workflow state with generated keywords
    """
    logging.info(f"[NODE] Generating keywords for topic: {state['topic']}")
    
    try:
        # Update state to show we're working on keyword generation
        state = update_state_progress(state, "generate_keywords")
        
        # Check if we should skip keyword generation
        if state.get("skip_keyword_generation", False):
            logging.info("[NODE] Skipping keyword generation as requested")
            return state
        
        # Initialize keyword generator tool with LLM configuration
        keyword_tool = KeywordsGeneratorTool(
            api=state["api"],
            model_name=state["model_name"]
        )
        
        # Generate keywords
        result = keyword_tool._run(state["topic"])
        
        if result["status"] != "success":
            error_msg = f"Failed to generate keywords: {result.get('error', 'Unknown error')}"
            logging.error(f"[NODE] {error_msg}")
            return update_state_error(state, error_msg)
        
        # Update state with generated keywords
        state["generated_keywords"] = result.get("keywords", [])
        state["keywords_save_path"] = result.get("save_result", "")
        state["status"] = "completed"
        
        logging.info(f"[NODE] Generated {len(state['generated_keywords'])} keywords for topic: {state['topic']}")
        return state
        
    except Exception as e:
        error_msg = f"Error in generate_keywords_node: {str(e)}"
        logging.exception(f"[NODE] {error_msg}")
        return update_state_error(state, error_msg)


def crawl_papers_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node for crawling papers from the specified conference and year.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated workflow state with crawled papers
    """
    logging.info(f"[NODE] Crawling papers for {state['conference']} {state['year']}")
    
    try:
        # Update state to show we're working on paper crawling
        state = update_state_progress(state, "crawl_papers")
        
        # Check if we should skip crawling
        if state.get("skip_crawling", False):
            logging.info("[NODE] Skipping paper crawling as requested")
            return state
        
        # Initialize paper crawler tool
        crawler_tool = PaperCrawlerTool()

        # Crawl papers
        result = crawler_tool._run(state["conference"], state["year"])
        
        if result["status"] != "success":
            error_msg = f"Failed to crawl papers: {result.get('error', 'Unknown error')}"
            logging.error(f"[NODE] {error_msg}")
            return update_state_error(state, error_msg)
        
        # Update state with crawl results
        state["crawled_papers"] = []  # Papers are saved to file, not stored in memory
        state["paper_list_path"] = result.get("save_path", "")
        state["papers_crawled_count"] = result.get("papers_count", 0)
        state["status"] = "completed"
        
        logging.info(f"[NODE] Crawled {state['papers_crawled_count']} papers from {state['conference']} {state['year']}")
        return state
        
    except Exception as e:
        error_msg = f"Error in crawl_papers_node: {str(e)}"
        logging.exception(f"[NODE] {error_msg}")
        return update_state_error(state, error_msg)


def filter_papers_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node for filtering papers by topic relevance.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated workflow state with filtered papers
    """
    logging.info(f"[NODE] Filtering papers for topic: {state['topic']}")
    
    try:
        # Update state to show we're working on paper filtering
        state = update_state_progress(state, "filter_papers")
        
        # Initialize paper filter tool with LLM configuration
        filter_tool = PaperFilterTool(
            api=state["api"],
            model_name=state["model_name"]
        )
        
        # Filter papers
        result = filter_tool._run(
            state["conference"], 
            state["year"], 
            state["topic"], 
            state["method"]
        )
        
        if result["status"] != "success":
            error_msg = f"Failed to filter papers: {result.get('error', 'Unknown error')}"
            logging.error(f"[NODE] {error_msg}")
            return update_state_error(state, error_msg)
        
        # Update state with filter results
        state["filtered_papers"] = []  # Papers are saved to file, not stored in memory
        state["filtered_papers_path"] = result.get("save_path", "")
        state["papers_filtered_count"] = result.get("filtered_count", 0)
        state["status"] = "completed"
        
        logging.info(f"[NODE] Filtered {state['papers_filtered_count']} papers for topic: {state['topic']}")
        return state
        
    except Exception as e:
        error_msg = f"Error in filter_papers_node: {str(e)}"
        logging.exception(f"[NODE] {error_msg}")
        return update_state_error(state, error_msg)


def summarize_papers_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node for summarizing filtered papers.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated workflow state with paper summaries
    """
    logging.info(f"[NODE] Summarizing papers for {state['conference']} {state['year']}")
    
    try:
        # Update state to show we're working on paper summarization
        state = update_state_progress(state, "summarize_papers")
        
        # Initialize paper summarizer tool with LLM configuration
        summarizer_tool = PaperSummarizerTool(
            api=state["api"],
            model_name=state["model_name"]
        )
        
        # Summarize papers
        result = summarizer_tool._run(
            state["conference"], 
            state["year"], 
            state["topic"]
        )
        
        if result["status"] != "success":
            error_msg = f"Failed to summarize papers: {result.get('error', 'Unknown error')}"
            logging.error(f"[NODE] {error_msg}")
            return update_state_error(state, error_msg)
        
        # Update state with summarization results
        state["summarized_papers"] = []  # Summaries are saved to files, not stored in memory
        state["summary_directory"] = f"{state['conference']}_{state['year']}/{state['topic']}" if state["topic"] else f"{state['conference']}_{state['year']}"
        state["papers_summarized_count"] = result.get("successful_summaries", 0)
        state["status"] = "completed"
        
        logging.info(f"[NODE] Summarized {state['papers_summarized_count']} papers")
        return state
        
    except Exception as e:
        error_msg = f"Error in summarize_papers_node: {str(e)}"
        logging.exception(f"[NODE] {error_msg}")
        return update_state_error(state, error_msg)


def aggregate_summary_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node for aggregating paper summaries into structured format.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated workflow state with aggregated summary
    """
    logging.info(f"[NODE] Aggregating summaries for {state['conference']} {state['year']}")
    
    try:
        # Update state to show we're working on summary aggregation
        state = update_state_progress(state, "aggregate_summary")
        
        # Initialize summary aggregator tool
        aggregator_tool = SummaryAggregatorTool()
        
        # Aggregate summaries
        result = aggregator_tool._run(
            state["conference"], 
            state["year"], 
            state["topic"], 
        )
        
        if result["status"] != "success":
            error_msg = f"Failed to aggregate summaries: {result.get('error', 'Unknown error')}"
            logging.error(f"[NODE] {error_msg}")
            return update_state_error(state, error_msg)
        
        # Update state with aggregation results
        state["aggregated_summary"] = result
        
        # Extract Excel path from successful language results (prefer CH if available)
        excel_path = ""
        for lang in ["CH", "EN"]:
            lang_result = result.get("language_results", {}).get(lang, {})
            if lang_result.get("status") == "success" and lang_result.get("excel_path"):
                excel_path = lang_result["excel_path"]
                break
        
        state["excel_output_path"] = excel_path
        state["status"] = "completed"
        
        total_aggregated = sum(
            lang_result.get("aggregated_count", 0)
            for lang_result in result.get("language_results", {}).values()
        )
        logging.info(f"[NODE] Aggregated {total_aggregated} summaries into Excel files")
        return state
        
    except Exception as e:
        error_msg = f"Error in aggregate_summary_node: {str(e)}"
        logging.exception(f"[NODE] {error_msg}")
        return update_state_error(state, error_msg)


def finalize_workflow_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Final node to complete the workflow and prepare results.
    
    Args:
        state: Current workflow state
        
    Returns:
        Final workflow state with completion status
    """
    logging.info("[NODE] Finalizing workflow")
    
    try:
        # Update state to show completion
        state = update_state_progress(state, "finalize", "completed")
        
        # Add completion timestamp if not already set
        if state.get("processing_time") is None:
            state["processing_time"] = time.time()
        
        # Prepare final summary
        workflow_summary = {
            "conference": state["conference"],
            "year": state["year"],
            "topic": state["topic"],
            "status": "completed",
            "papers_processed": {
                "crawled": state["papers_crawled_count"],
                "filtered": state["papers_filtered_count"],
                "summarized": state["papers_summarized_count"]
            },
            "output_files": {
                "keywords": state["keywords_save_path"],
                "paper_list": state["paper_list_path"],
                "filtered_papers": state["filtered_papers_path"],
                "summaries": state["summary_directory"],
                "excel_report": state["excel_output_path"]
            },
            "completion_time": datetime.now().isoformat()
        }
        
        # Add language-specific aggregation results if available
        if state.get("aggregated_summary") and state["aggregated_summary"].get("language_results"):
            workflow_summary["aggregation_results"] = state["aggregated_summary"]["language_results"]
        
        state["aggregated_summary"] = workflow_summary
        logging.info("[NODE] Workflow completed successfully")
        return state
        
    except Exception as e:
        error_msg = f"Error in finalize_workflow_node: {str(e)}"
        logging.exception(f"[NODE] {error_msg}")
        return update_state_error(state, error_msg)


def error_handler_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """
    Node to handle errors and provide graceful failure.
    
    Args:
        state: Current workflow state with error
        
    Returns:
        Updated state with error information
    """
    logging.error(f"[NODE] Error handler triggered: {state.get('error_message', 'Unknown error')}")
    
    # Add error timestamp
    state["error_timestamp"] = datetime.now().isoformat()
    
    # Prepare error summary
    error_summary = {
        "status": "error",
        "conference": state["conference"],
        "year": state["year"],
        "topic": state["topic"],
        "current_step": state["current_step"],
        "error_message": state["error_message"],
        "error_timestamp": state["error_timestamp"]
    }
    
    state["aggregated_summary"] = error_summary
    return state