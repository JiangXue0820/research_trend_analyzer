from typing import Dict, Any, Optional
import logging
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from .state import ResearchWorkflowState, is_workflow_complete
from .nodes import (
    generate_keywords_node,
    crawl_papers_node,
    filter_papers_node,
    summarize_papers_node,
    aggregate_summary_node,
    finalize_workflow_node,
    error_handler_node
)


def create_research_workflow_graph() -> CompiledStateGraph:
    """
    Create and compile the research trend analysis workflow graph.
    
    Returns:
        Compiled state graph for the research workflow
    """
    logging.info("[GRAPH] Creating research trend analysis workflow graph")
    
    # Create the state graph
    workflow = StateGraph(ResearchWorkflowState)
    
    # Add all nodes to the graph
    workflow.add_node("generate_keywords", generate_keywords_node)
    workflow.add_node("crawl_papers", crawl_papers_node)
    workflow.add_node("filter_papers", filter_papers_node)
    workflow.add_node("summarize_papers", summarize_papers_node)
    workflow.add_node("aggregate_summary", aggregate_summary_node)
    workflow.add_node("finalize_workflow", finalize_workflow_node)
    workflow.add_node("handle_error", error_handler_node)
    
    # Define the main workflow sequence with conditional entry points
    workflow.set_entry_point("check_keyword_generation")

    # Add conditional check nodes
    workflow.add_node("check_keyword_generation", lambda state: state)
    workflow.add_node("check_crawling", lambda state: state)

    # Conditional edges for keyword generation
    workflow.add_conditional_edges(
        "check_keyword_generation",
        check_skip_keyword_generation,
        {"skip": "check_crawling", "generate": "generate_keywords"}
    )

    # Conditional edges for paper crawling
    workflow.add_conditional_edges(
        "check_crawling",
        check_skip_crawling,
        {"skip": "filter_papers", "crawl": "crawl_papers"}
    )

    # Main success path
    workflow.add_edge("generate_keywords", "check_crawling")
    workflow.add_edge("crawl_papers", "filter_papers")
    workflow.add_edge("filter_papers", "summarize_papers")
    workflow.add_edge("summarize_papers", "aggregate_summary")
    workflow.add_edge("aggregate_summary", "finalize_workflow")
    workflow.add_edge("finalize_workflow", END)
    
    # Error handling - any node can transition to error handler
    workflow.add_conditional_edges(
        "generate_keywords",
        check_for_errors,
        {"continue": "crawl_papers", "error": "handle_error"}
    )
    
    workflow.add_conditional_edges(
        "crawl_papers",
        check_for_errors,
        {"continue": "filter_papers", "error": "handle_error"}
    )
    
    workflow.add_conditional_edges(
        "filter_papers",
        check_for_errors,
        {"continue": "summarize_papers", "error": "handle_error"}
    )
    
    workflow.add_conditional_edges(
        "summarize_papers",
        check_for_errors,
        {"continue": "aggregate_summary", "error": "handle_error"}
    )
    
    workflow.add_conditional_edges(
        "aggregate_summary",
        check_for_errors,
        {"continue": "finalize_workflow", "error": "handle_error"}
    )
    
    # Error handler always goes to end
    workflow.add_edge("handle_error", END)
    
    # Compile the graph
    compiled_graph = workflow.compile()
    
    logging.info("[GRAPH] Research workflow graph compiled successfully")
    return compiled_graph


def check_for_errors(state: ResearchWorkflowState) -> str:
    """
    Check if the current state contains any errors.
    
    Args:
        state: Current workflow state
        
    Returns:
        "continue" if no errors, "error" if errors found
    """
    if state.get("status") == "error":
        logging.warning(f"[GRAPH] Error detected in state: {state.get('error_message', 'Unknown error')}")
        return "error"
    return "continue"


def check_skip_keyword_generation(state: ResearchWorkflowState) -> str:
    """
    Check if keyword generation should be skipped.
    
    Args:
        state: Current workflow state
        
    Returns:
        "skip" to skip keyword generation, "generate" to proceed
    """
    if state.get("skip_keyword_generation", False):
        logging.info("[GRAPH] Skipping keyword generation as configured")
        return "skip"
    return "generate"


def check_skip_crawling(state: ResearchWorkflowState) -> str:
    """
    Check if paper crawling should be skipped.
    
    Args:
        state: Current workflow state
        
    Returns:
        "skip" to skip crawling, "crawl" to proceed
    """
    if state.get("skip_crawling", False):
        logging.info("[GRAPH] Skipping paper crawling as configured")
        return "skip"
    return "crawl"


def check_workflow_completion(state: ResearchWorkflowState) -> str:
    """
    Check if the workflow has completed successfully.
    
    Args:
        state: Current workflow state
        
    Returns:
        "complete" if workflow is done, "continue" otherwise
    """
    if is_workflow_complete(state):
        logging.info("[GRAPH] Workflow completed successfully")
        return "complete"
    return "continue"


class ResearchWorkflowAgent:
    """
    Main agent class for research trend analysis workflow.
    Manages the execution of the langgraph workflow.
    """
    
    def __init__(self):
        """Initialize the research workflow agent."""
        self.graph = create_research_workflow_graph()
        logging.info("[AGENT] Research workflow agent initialized")
    
    def run_workflow(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the complete research trend analysis workflow.
        
        Args:
            config: Configuration dictionary for the workflow
            
        Returns:
            Final workflow state with results
        """
        logging.info(f"[AGENT] Starting research workflow with config: {config}")
        
        try:
            # Initialize state from config
            from .state import ResearchWorkflowConfig, initialize_workflow_state
            workflow_config = ResearchWorkflowConfig(**config)
            initial_state = initialize_workflow_state(workflow_config)
            
            # Execute the workflow graph
            final_state = self.graph.invoke(initial_state)
            
            # Get workflow summary
            from .state import get_workflow_summary
            summary = get_workflow_summary(final_state)
            
            logging.info(f"[AGENT] Workflow completed with status: {summary['status']}")
            return summary
            
        except Exception as e:
            error_msg = f"Failed to execute workflow: {str(e)}"
            logging.exception(f"[AGENT] {error_msg}")
            return {
                "status": "error",
                "error_message": error_msg,
                "conference": config.get("conference", "unknown"),
                "year": config.get("year", "unknown"),
                "topic": config.get("topic", "unknown")
            }
    
    def get_graph_visualization(self) -> Optional[str]:
        """
        Get a visualization of the workflow graph.
        
        Returns:
            Graph visualization in DOT format, or None if not available
        """
        try:
            return self.graph.get_graph().draw_mermaid()
        except Exception as e:
            logging.warning(f"[AGENT] Could not generate graph visualization: {e}")
            return None
    
    def get_graph_structure(self) -> Dict[str, Any]:
        """
        Get the structure of the workflow graph.
        
        Returns:
            Dictionary describing the graph structure
        """
        try:
            graph = self.graph.get_graph()
            return {
                "nodes": list(graph.nodes),
                "edges": list(graph.edges),
                "entry_point": graph.entry_point,
                "conditional_edges": getattr(graph, "conditional_edges", {})
            }
        except Exception as e:
            logging.warning(f"[AGENT] Could not get graph structure: {e}")
            return {"error": str(e)}


# Create a singleton instance of the agent
research_agent = ResearchWorkflowAgent()


def run_research_workflow(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to run the research workflow.
    
    Args:
        config: Configuration dictionary for the workflow
        
    Returns:
        Final workflow results
    """
    return research_agent.run_workflow(config)


def get_workflow_visualization() -> Optional[str]:
    """
    Convenience function to get workflow visualization.
    
    Returns:
        Graph visualization in DOT format
    """
    return research_agent.get_graph_visualization()