from typing import Dict, List, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field


class ResearchWorkflowState(TypedDict):
    """
    State for the research trend analysis workflow.
    Tracks the progress and data throughout the entire workflow.
    """
    # Input parameters
    conference: str
    year: int
    topic: str
    method: str = Field(default="llm")
    
    # LLM configuration
    api: str
    model_name: str
    
    # Workflow control flags
    skip_keyword_generation: bool
    skip_crawling: bool
    
    # Workflow progress tracking
    current_step: str
    status: str  # "pending", "in_progress", "completed", "error"
    error_message: Optional[str]
    
    # Data generated during workflow
    generated_keywords: Optional[List[str]]
    crawled_papers: Optional[List[Dict[str, Any]]]
    filtered_papers: Optional[List[Dict[str, Any]]]
    summarized_papers: Optional[List[Dict[str, Any]]]
    aggregated_summary: Optional[Dict[str, Any]]
    
    # File paths and metadata
    keywords_save_path: Optional[str]
    paper_list_path: Optional[str]
    filtered_papers_path: Optional[str]
    summary_directory: Optional[str]
    excel_output_path: Optional[str]
    
    # Statistics and metrics
    papers_crawled_count: int
    papers_filtered_count: int
    papers_summarized_count: int
    processing_time: Optional[float]


class ResearchWorkflowConfig(BaseModel):
    """
    Configuration for the research trend analysis workflow.
    """
    conference: str = Field(..., description="Conference name (e.g., 'neurips', 'popets')")
    year: int = Field(..., description="Conference year")
    topic: str = Field(..., description="Research topic to analyze")
    method: str = Field(default="llm", description="Filtering method: 'keyword' or 'llm'")
    
    # LLM configuration
    api: str = Field(default="gemini", description="API to use for LLM calls: 'gemini' or 'mlops'")
    model_name: str = Field(default="gemini-2.5-flash", description="Model name for LLM calls")
    
    # Optional configuration overrides
    scope_list_path: Optional[str] = Field(
        default=None,
        description="Path to analysis scope JSON file"
    )
    paper_list_root: Optional[str] = Field(
        default=None, 
        description="Root directory for paper lists"
    )
    paper_summary_root: Optional[str] = Field(
        default=None, 
        description="Root directory for paper summaries"
    )
    temp_pdf_root: Optional[str] = Field(
        default=None, 
        description="Temporary directory for PDF downloads"
    )
    
    # Workflow control
    skip_keyword_generation: bool = Field(
        default=False, 
        description="Skip keyword generation if keywords already exist"
    )
    skip_crawling: bool = Field(
        default=False, 
        description="Skip paper crawling if papers already exist"
    )
    max_papers: Optional[int] = Field(
        default=None, 
        description="Maximum number of papers to process (for testing)"
    )


def initialize_workflow_state(config: ResearchWorkflowConfig) -> ResearchWorkflowState:
    """
    Initialize the workflow state with the given configuration.
    
    Args:
        config: Research workflow configuration
        
    Returns:
        Initialized workflow state
    """
    return {
        "conference": config.conference,
        "year": config.year,
        "topic": config.topic,
        "method": config.method,
        
        # LLM configuration
        "api": config.api,
        "model_name": config.model_name,
        
        # Workflow control flags
        "skip_keyword_generation": config.skip_keyword_generation,
        "skip_crawling": config.skip_crawling,
        
        "current_step": "initialize",
        "status": "pending",
        "error_message": None,
        
        "generated_keywords": None,
        "crawled_papers": None,
        "filtered_papers": None,
        "summarized_papers": None,
        "aggregated_summary": None,
        
        "keywords_save_path": None,
        "paper_list_path": None,
        "filtered_papers_path": None,
        "summary_directory": None,
        "excel_output_path": None,
        
        "papers_crawled_count": 0,
        "papers_filtered_count": 0,
        "papers_summarized_count": 0,
        "processing_time": None
    }


def update_state_progress(state: ResearchWorkflowState, step: str, status: str = "in_progress") -> ResearchWorkflowState:
    """
    Update the workflow state with current progress.
    
    Args:
        state: Current workflow state
        step: Current step name
        status: Current status ("in_progress", "completed", "error")
        
    Returns:
        Updated workflow state
    """
    return {
        **state,
        "current_step": step,
        "status": status
    }


def update_state_error(state: ResearchWorkflowState, error_message: str) -> ResearchWorkflowState:
    """
    Update the workflow state with an error.
    
    Args:
        state: Current workflow state
        error_message: Error message to store
        
    Returns:
        Updated workflow state with error
    """
    return {
        **state,
        "status": "error",
        "error_message": error_message
    }


def is_workflow_complete(state: ResearchWorkflowState) -> bool:
    """
    Check if the workflow has completed successfully.
    
    Args:
        state: Workflow state to check
        
    Returns:
        True if workflow is complete, False otherwise
    """
    return (
        state.get("status") == "completed" and
        state.get("aggregated_summary") is not None and
        state.get("excel_output_path") is not None
    )


def get_workflow_summary(state: ResearchWorkflowState) -> Dict[str, Any]:
    """
    Get a summary of the workflow execution.
    
    Args:
        state: Workflow state to summarize
        
    Returns:
        Summary dictionary with key metrics and results
    """
    return {
        "conference": state["conference"],
        "year": state["year"],
        "topic": state["topic"],
        "status": state["status"],
        "current_step": state["current_step"],
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
        "error_message": state["error_message"],
        "processing_time": state["processing_time"]
    }