#!/usr/bin/env python3
"""
Basic tests for the Research Trend Analyzer Light Agent workflow.
These tests verify the core functionality without making actual API calls.
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import tempfile
import shutil

from agent.state import ResearchWorkflowConfig, initialize_workflow_state
from agent.nodes import (
    generate_keywords_node,
    crawl_papers_node,
    filter_papers_node,
    summarize_papers_node,
    aggregate_summary_node
)


class TestWorkflowState(unittest.TestCase):
    """Test the workflow state management."""
    
    def test_state_initialization(self):
        """Test that workflow state is properly initialized."""
        config = ResearchWorkflowConfig(
            conference="popets",
            year=2025,
            topic="dp_theory",
            method="keyword",
            language="CH",
            api="gemini",
            model_name="gemini-2.5-flash"
        )
        
        state = initialize_workflow_state(config)
        
        self.assertEqual(state["conference"], "popets")
        self.assertEqual(state["year"], 2025)
        self.assertEqual(state["topic"], "dp_theory")
        self.assertEqual(state["method"], "keyword")
        self.assertEqual(state["language"], "CH")
        self.assertEqual(state["status"], "pending")
        self.assertEqual(state["current_step"], "initialize")


class TestWorkflowNodes(unittest.TestCase):
    """Test individual workflow nodes with mocked dependencies."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state = {
            "conference": "popets",
            "year": 2025,
            "topic": "dp_theory",
            "method": "keyword",
            "language": "CH",
            "api": "gemini",
            "model_name": "gemini-2.5-flash",
            "status": "pending",
            "current_step": "initialize",
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
        
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "configs"
        self.papers_dir = Path(self.temp_dir) / "papers"
        self.config_dir.mkdir(parents=True)
        self.papers_dir.mkdir(parents=True)
        
        # Create a test analysis scope file
        self.scope_file = self.config_dir / "analysis_scope.json"
        with open(self.scope_file, 'w', encoding='utf-8') as f:
            json.dump({
                "dp_theory": {
                    "definition": "Privacy and data protection research",
                    "keywords": ["dp_theory", "data protection", "encryption"]
                }
            }, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    @patch('tools.keywords_generator.KeywordsGeneratorTool._run')
    def test_generate_keywords_node_success(self, mock_keyword_tool):
        """Test successful keyword generation."""
        mock_keyword_tool.return_value = {
            "status": "success",
            "topic": "dp_theory",
            "keywords": ["dp_theory", "data protection"],
            "save_result": "configs/analysis_scope.json",
            "keywords_count": 2
        }
        
        state = generate_keywords_node(self.test_state)
        
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["generated_keywords"], ["dp_theory", "data protection"])
        self.assertEqual(state["keywords_save_path"], "configs/analysis_scope.json")
    
    @patch('tools.paper_crawler.PaperCrawlerTool._run')
    def test_crawl_papers_node_success(self, mock_crawler_tool):
        """Test successful paper crawling."""
        mock_crawler_tool.return_value = {
            "status": "success",
            "conference": "popets",
            "year": 2025,
            "papers_count": 5,
            "new_papers_added": 5,
            "save_path": "papers/paper_list/popets_2025/full_list.jsonl",
            "message": "Successfully crawled 5 papers"
        }
        
        state = crawl_papers_node(self.test_state)
        
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["papers_crawled_count"], 5)
        self.assertEqual(state["paper_list_path"], "papers/paper_list/popets_2025/full_list.jsonl")
    
    @patch('tools.paper_filter.PaperFilterTool._run')
    def test_filter_papers_node_success(self, mock_filter_tool):
        """Test successful paper filtering."""
        mock_filter_tool.return_value = {
            "status": "success",
            "conference": "popets",
            "year": 2025,
            "topic": "dp_theory",
            "filtered_count": 3,
            "new_papers_added": 3,
            "save_path": "papers/paper_list/popets_2025/filtered_dp_theory.jsonl",
            "message": "Successfully filtered 3 papers"
        }
        
        state = filter_papers_node(self.test_state)
        
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["papers_filtered_count"], 3)
        self.assertEqual(state["filtered_papers_path"], "papers/paper_list/popets_2025/filtered_dp_theory.jsonl")
    
    @patch('tools.paper_summarizer.PaperSummarizerTool._run')
    def test_summarize_papers_node_success(self, mock_summarizer_tool):
        """Test successful paper summarization."""
        mock_summarizer_tool.return_value = {
            "status": "success",
            "conference": "popets",
            "year": 2025,
            "topic": "dp_theory",
            "papers_processed": 3,
            "successful_summaries": 3,
            "failed_summaries": 0,
            "message": "Successfully summarized 3 papers"
        }
        
        state = summarize_papers_node(self.test_state)
        
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["papers_summarized_count"], 3)
    
    @patch('tools.summary_aggregator.SummaryAggregatorTool._run')
    def test_aggregate_summary_node_success(self, mock_aggregator_tool):
        """Test successful summary aggregation."""
        mock_aggregator_tool.return_value = {
            "status": "success",
            "conference": "popets",
            "year": 2025,
            "topic": "dp_theory",
            "language": "CH",
            "aggregated_count": 3,
            "failed_count": 0,
            "excel_path": "papers/paper_summary/popets_2025/privacy/summary.xlsx",
            "message": "Aggregated 3 summaries"
        }
        
        state = aggregate_summary_node(self.test_state)
        
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["excel_output_path"], "papers/paper_summary/popets_2025/privacy/summary.xlsx")


class TestErrorHandling(unittest.TestCase):
    """Test error handling in workflow nodes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_state = {
            "conference": "popets",
            "year": 2025,
            "topic": "dp_theory",
            "method": "keyword",
            "language": "CH",
            "api": "gemini",
            "model_name": "gemini-2.5-flash",
            "status": "pending",
            "current_step": "initialize",
            "error_message": None
        }
    
    @patch('tools.keywords_generator.KeywordsGeneratorTool._run')
    def test_generate_keywords_node_error(self, mock_keyword_tool):
        """Test error handling in keyword generation."""
        mock_keyword_tool.return_value = {
            "status": "error",
            "topic": "dp_theory",
            "error": "Failed to generate keywords"
        }
        
        state = generate_keywords_node(self.test_state)
        
        self.assertEqual(state["status"], "error")
        self.assertIn("error", state["error_message"].lower())


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration validation."""
    
    def test_valid_configuration(self):
        """Test that valid configuration passes validation."""
        config = ResearchWorkflowConfig(
            conference="popets",
            year=2025,
            topic="dp_theory",
            api="gemini",
            model_name="gemini-2.5-flash"
        )
        
        # Should not raise any exceptions
        self.assertEqual(config.conference, "popets")
        self.assertEqual(config.year, 2025)
        self.assertEqual(config.topic, "dp_theory")
    
    def test_invalid_configuration(self):
        """Test that invalid configuration raises validation errors."""
        with self.assertRaises(ValueError):
            ResearchWorkflowConfig(
                conference="",  # Empty conference
                year=2025,
                topic="dp_theory"
            )
        
        with self.assertRaises(ValueError):
            ResearchWorkflowConfig(
                conference="popets",
                year=1800,  # Invalid year
                topic="dp_theory"
            )


if __name__ == "__main__":
    unittest.main()