import os
import json
import shutil
import tempfile
import pytest
import sys
sys.path.append("../")
from research_trend_analyzer.tools import paper_fetch_tools as paper_fetch_tools
from research_trend_analyzer.tools.paper_fetch_tools import (
    save_paper_info, load_paper_list, filter_paper_by_topic, fetch_paper_list,
    generate_keyword_list, TopicKeywordsModel
)

# mock 依赖
import builtins

# ========== 测试 save_paper_info 和 load_paper_list ==========

def test_save_and_load_paper_info():
    # 使用临时目录防止污染
    tmpdir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmpdir, "paper_list", "iclr"))
        test_papers = [
            {"title": "Paper 1", "authors": ["A"], "paper_url": "url1"},
            {"title": "Paper 2", "authors": ["B"], "paper_url": "url2"},
        ]
        conference = "ICLR"
        year = 2024
        # Patch os.path.join 使所有文件落在 tmpdir 下
        orig_join = os.path.join
        os.path.join = lambda *args: orig_join(tmpdir, *args[1:]) if args[0] == "paper_list" else orig_join(*args)
        
        result = save_paper_info(test_papers, conference, year)
        assert result["count"] == 2
        path = result["filepath"]
        assert os.path.exists(path)
        # 再load回来
        loaded = load_paper_list(conference, year)
        assert loaded == test_papers
    finally:
        shutil.rmtree(tmpdir)
        os.path.join = orig_join

# ========== 测试 filter_paper_by_topic ==========

def test_filter_paper_by_topic(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        orig_dir = os.getcwd()
        os.chdir(tmpdir)
        try:
            conf = "neurips"
            year = 2023
            os.makedirs(os.path.join("paper_list", conf))
            master_file = os.path.join("paper_list", conf, f"{conf}{year}.jsonl")
            papers = [
                {"title": "privacy preserving ML", "paper_url": "u1", "abstract": "privacy"},
                {"title": "deep learning", "paper_url": "u2", "abstract": "image"},
            ]
            with open(master_file, "w", encoding="utf-8") as f:
                for p in papers:
                    f.write(json.dumps(p, ensure_ascii=False) + "\n")
            # Patch paper_matches_topic
            monkeypatch.setattr("utils.paper_crawler.paper_matches_topic", lambda paper, keywords: "privacy" in paper.get("abstract", ""))
            topic_keywords = TopicKeywordsModel(topic="privacy", keywords=["privacy"])
            result = filter_paper_by_topic(conf, year, topic_keywords)
            print(result)
            assert "error" not in result, f"Returned error: {result.get('error')}"
            assert result["filtered_count"] == 1
        finally:
            os.chdir(orig_dir)

# ========== 测试 generate_keyword_list ==========

def test_generate_keyword_list_success():
    class DummyLLM:
        def invoke(self, prompt):
            return type("Resp", (), {"content": "{'topic': 'privacy', 'keywords': ['privacy', 'private', 'anonymity', 'data protection', 'confidentiality']}"})()
    llm = DummyLLM()
    result = generate_keyword_list("privacy", llm=llm)
    assert result["topic"] == "privacy"
    assert "privacy" in result["keywords"]

def test_generate_keyword_list_llm_fail():
    class DummyLLM:
        def invoke(self, prompt):
            return type("Resp", (), {"content": "not a valid dict"})()
    llm = DummyLLM()
    result = generate_keyword_list("xxx", llm=llm)
    assert "error" in result
    assert "raw_response" in result

def test_generate_keyword_list_no_llm():
    result = generate_keyword_list("privacy", llm=None)
    assert "error" in result

# ========== fetch_paper_list 建议单独测试或集成测试 ==========
# 因为要依赖实际 fetch_neurips_papers，你可以 mock 它
def test_fetch_paper_list(monkeypatch):
    conf = "neurips"
    year = 2024
    test_papers = [
        {"title": "abc", "paper_url": "urlx"},
        {"title": "def", "paper_url": "urly"},
    ]
    # PATCH fetch_neurips_papers
    monkeypatch.setattr("utils.paper_crawler.fetch_neurips_papers", lambda y: test_papers)
    # PATCH load_paper_list: 只返回urlx
    def mock_load_paper_list(c, y, topic_keywords=None):
        return [{"paper_url": "urlx"}]
    monkeypatch.setattr(paper_fetch_tools, "load_paper_list", mock_load_paper_list)
    # PATCH save_paper_info
    def mock_save_paper_info(papers, c, y, topic_keywords=None):
        return {"filepath": "/tmp/fake", "count": len(papers)}
    monkeypatch.setattr(paper_fetch_tools, "save_paper_info", mock_save_paper_info)

    result = paper_fetch_tools.fetch_paper_list(conf, year)
    print("TEST_RESULT:", result)
    assert "new_count" in result
    assert result["new_count"] == 1