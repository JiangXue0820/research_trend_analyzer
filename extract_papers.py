import langgraph
from langgraph.graph import StateGraph, END
from typing import Dict, List, Any, TypedDict, Optional
import requests
import json
import time
import re
import os
import logging
import argparse
from scholarly import scholarly
import pycountry
import PyPDF2
from io import BytesIO

# 添加第三方PDF解析库
import pdfplumber
from urllib.parse import urlparse, urljoin

# 设置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义状态类型
class ScraperState(TypedDict):
    paper_id: str
    cited_papers: List[Dict[str, Any]]
    european_papers: List[Dict[str, Any]]
    errors: List[str]
    status: str
    progress: int
    total: int
    pdf_cache_dir: str

# 节点函数：初始化状态
def initialize_state(paper_id: str, pdf_cache_dir: str = "./pdf_cache") -> ScraperState:
    """初始化爬虫状态"""
    # 创建PDF缓存目录
    os.makedirs(pdf_cache_dir, exist_ok=True)
    
    return {
        "paper_id": paper_id,
        "cited_papers": [],
        "european_papers": [],
        "errors": [],
        "status": "initialized",
        "progress": 0,
        "total": 0,
        "pdf_cache_dir": pdf_cache_dir
    }

# 辅助函数：下载PDF文件
def download_pdf(url: str, save_path: str = None) -> Optional[BytesIO]:
    """从URL下载PDF文件"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
                # 保存到本地文件
                if save_path:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
                
                # 返回BytesIO对象
                return BytesIO(response.content)
            else:
                logger.warning(f"URL不是PDF文件: {url}, Content-Type: {content_type}")
                return None
        else:
            logger.warning(f"下载PDF失败，状态码: {response.status_code}, URL: {url}")
            return None
    except Exception as e:
        logger.error(f"下载PDF出错: {str(e)}, URL: {url}")
        return None

# 辅助函数：从PDF中提取作者和机构信息
def extract_info_from_pdf(pdf_file: BytesIO) -> Dict[str, Any]:
    """从PDF文件中提取标题、作者和机构信息"""
    result = {
        "title": "",
        "authors": [],
        "affiliations": [],
        "abstract": ""
    }
    
    try:
        # 使用pdfplumber提取第一页文本
        with pdfplumber.open(pdf_file) as pdf:
            if len(pdf.pages) > 0:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                if not text:
                    logger.warning("无法从PDF中提取文本")
                    return result
                
                # 提取标题 (通常是PDF第一页中最大字体的文本)
                # 这里简化处理，假设标题是第一页开头的几行文本
                lines = text.split('\n')
                if lines:
                    result["title"] = lines[0].strip()
                
                # 尝试识别作者部分（通常在标题之后，摘要之前）
                author_section = ""
                abstract_start = -1
                
                # 寻找关键词来定位作者和摘要部分
                for i, line in enumerate(lines):
                    if i > 0 and (re.search(r'abstract', line.lower()) or 
                                 re.search(r'^abstract$', line.lower())):
                        abstract_start = i
                        break
                    elif i > 0 and i < 10:  # 假设作者在前10行
                        author_section += line + " "
                
                # 提取摘要
                if abstract_start > 0 and abstract_start < len(lines) - 1:
                    abstract_text = ""
                    for i in range(abstract_start + 1, min(abstract_start + 10, len(lines))):
                        if re.search(r'introduction|keywords', lines[i].lower()):
                            break
                        abstract_text += lines[i] + " "
                    result["abstract"] = abstract_text.strip()
                
                # 处理作者部分
                # 查找电子邮件模式，这通常表示作者信息部分
                email_pattern = r'[\w\.-]+@[\w\.-]+'
                emails = re.findall(email_pattern, author_section)
                
                # 尝试从文本中提取机构名称
                # 常见的机构指示词
                institution_indicators = [
                    "University", "Institute", "College", "School", "Department", 
                    "Lab", "Centre", "Center", "Academy", "Corporation", "Inc", 
                    "Ltd", "LLC", "GmbH", "Research"
                ]
                
                # 查找包含机构指示词的行
                potential_affiliations = []
                for line in lines[:20]:  # 只在前20行查找
                    for indicator in institution_indicators:
                        if indicator in line and line not in potential_affiliations:
                            potential_affiliations.append(line.strip())
                            break
                
                # 查找上标数字模式，如¹Department of...
                superscript_pattern = r'[¹²³⁴⁵⁶⁷⁸⁹][A-Z][^\n]+'
                superscript_affiliations = re.findall(superscript_pattern, text)
                if superscript_affiliations:
                    potential_affiliations.extend(superscript_affiliations)
                
                # 更复杂的模式：通常机构在作者名字下方，并以Department、University等关键词开头
                for i, line in enumerate(lines):
                    if i > 0 and i < 20:
                        line_lower = line.lower()
                        if any(word in line_lower for word in ["department", "university", "institute", "school"]):
                            if line not in potential_affiliations:
                                potential_affiliations.append(line.strip())
                
                # 设置作者和机构
                # 尝试从作者部分提取名字
                author_pattern = r'[A-Z][a-z]+ [A-Z][a-z]+'
                author_matches = re.findall(author_pattern, author_section)
                
                if author_matches:
                    result["authors"] = [name.strip() for name in author_matches if len(name) > 5]
                
                if potential_affiliations:
                    result["affiliations"] = potential_affiliations
                
                # 如果没有找到作者或机构，尝试使用PyPDF2提取元数据
                if not result["authors"] or not result["affiliations"]:
                    pdf_file.seek(0)  # 重置文件指针
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    if pdf_reader.metadata:
                        # 提取作者信息
                        if '/Author' in pdf_reader.metadata and not result["authors"]:
                            authors_text = pdf_reader.metadata['/Author']
                            if authors_text:
                                # 尝试拆分多个作者
                                result["authors"] = [a.strip() for a in re.split(r'[,;]', authors_text)]
    
    except Exception as e:
        logger.error(f"从PDF提取信息时出错: {str(e)}")
    
    return result

# 辅助函数：获取引用论文的PDF链接
def get_pdf_links(publication_data: Dict) -> List[str]:
    """尝试从多个途径获取论文的PDF链接"""
    pdf_links = []
    
    # 方法1: 直接从pub_url获取PDF
    if 'pub_url' in publication_data and publication_data['pub_url']:
        url = publication_data['pub_url']
        if url.lower().endswith('.pdf'):
            pdf_links.append(url)
        else:
            # 尝试将论文链接转换为PDF链接
            parsed_url = urlparse(url)
            if 'arxiv.org' in parsed_url.netloc:
                # arXiv链接转换为PDF
                if 'abs' in parsed_url.path:
                    pdf_url = url.replace('/abs/', '/pdf/') + '.pdf'
                    pdf_links.append(pdf_url)
            elif 'doi.org' in parsed_url.netloc:
                # 一些DOI链接可能会重定向到PDF
                pdf_links.append(url)
    
    # 方法2: 尝试从scholarly中提取更多信息
    if 'eprint_url' in publication_data:
        pdf_links.append(publication_data['eprint_url'])
    
    # 方法3: 如果有网址，尝试访问并寻找PDF链接
    if 'pub_url' in publication_data and publication_data['pub_url'] and not pdf_links:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(publication_data['pub_url'], headers=headers, timeout=10)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找可能的PDF链接
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.lower().endswith('.pdf'):
                        # 将相对URL转换为绝对URL
                        abs_url = urljoin(publication_data['pub_url'], href)
                        pdf_links.append(abs_url)
        except Exception as e:
            logger.warning(f"获取PDF链接时出错: {str(e)}")
    
    return pdf_links

# 节点函数：获取引用论文列表并下载PDF
def fetch_cited_papers(state: ScraperState) -> ScraperState:
    """从Google Scholar获取引用该论文的所有论文，并尝试下载PDF获取详细信息"""
    try:
        logger.info(f"正在获取论文ID {state['paper_id']} 的引用文章...")
        
        # 使用scholarly获取论文信息
        paper = scholarly.get_publication(state['paper_id'])
        
        # 获取引用该论文的文章
        cited_papers = []
        citations = scholarly.citedby(paper)
        
        # 遍历所有引用论文
        for i, cited_paper in enumerate(citations):
            try:
                # 填充论文详细信息
                detailed_paper = scholarly.fill(cited_paper)
                
                # 提取基本信息
                paper_info = {
                    "paper_name": detailed_paper.get('bib', {}).get('title', ''),
                    "authors": detailed_paper.get('bib', {}).get('author', []),
                    "abstract": detailed_paper.get('bib', {}).get('abstract', ''),
                    "url": detailed_paper.get('pub_url', ''),
                    "year": detailed_paper.get('bib', {}).get('pub_year', ''),
                    "venue": detailed_paper.get('bib', {}).get('venue', ''),
                    "affiliations": []
                }
                
                # 尝试获取PDF链接
                pdf_links = get_pdf_links(detailed_paper)
                
                # 如果找到PDF链接，尝试下载并提取信息
                pdf_info = None
                for pdf_link in pdf_links:
                    # 创建缓存文件路径
                    safe_title = re.sub(r'[^\w\-_\. ]', '_', paper_info["paper_name"])
                    pdf_cache_path = os.path.join(state["pdf_cache_dir"], f"{safe_title[:100]}.pdf")
                    
                    # 检查缓存
                    if os.path.exists(pdf_cache_path):
                        logger.info(f"使用缓存的PDF: {pdf_cache_path}")
                        with open(pdf_cache_path, 'rb') as f:
                            pdf_bytes = BytesIO(f.read())
                            pdf_info = extract_info_from_pdf(pdf_bytes)
                            break
                    else:
                        # 下载PDF
                        logger.info(f"尝试下载PDF: {pdf_link}")
                        pdf_bytes = download_pdf(pdf_link, pdf_cache_path)
                        if pdf_bytes:
                            pdf_info = extract_info_from_pdf(pdf_bytes)
                            break
                
                # 如果成功从PDF中提取信息，更新论文信息
                if pdf_info:
                    if pdf_info["title"] and len(pdf_info["title"]) > len(paper_info["paper_name"]):
                        paper_info["paper_name"] = pdf_info["title"]
                    
                    if pdf_info["authors"]:
                        paper_info["authors"] = pdf_info["authors"]
                    
                    if pdf_info["affiliations"]:
                        paper_info["affiliations"] = pdf_info["affiliations"]
                    
                    if pdf_info["abstract"] and len(pdf_info["abstract"]) > len(paper_info["abstract"]):
                        paper_info["abstract"] = pdf_info["abstract"]
                else:
                    # 如果无法从PDF获取信息，尝试从scholarly数据中提取
                    if 'author_pub_affiliation' in detailed_paper:
                        if isinstance(detailed_paper['author_pub_affiliation'], list):
                            paper_info["affiliations"] = detailed_paper['author_pub_affiliation']
                        elif isinstance(detailed_paper['author_pub_affiliation'], str):
                            paper_info["affiliations"] = [detailed_paper['author_pub_affiliation']]
                
                # 如果仍然没有机构信息，标记为未知
                if not paper_info["affiliations"]:
                    paper_info["affiliations"] = ["Unknown"]
                
                # 添加到引用论文列表
                cited_papers.append(paper_info)
                
                # 更新进度
                logger.info(f"已处理 {i+1} 篇引用论文")
                state["progress"] = i + 1
                
                # 防止过快请求导致被封
                time.sleep(3)
                
            except Exception as e:
                error_msg = f"处理引用论文时出错: {str(e)}"
                logger.error(error_msg)
                state["errors"].append(error_msg)
        
        # 更新状态
        state["cited_papers"] = cited_papers
        state["total"] = len(cited_papers)
        state["status"] = "papers_fetched"
        
        logger.info(f"成功获取了 {len(cited_papers)} 篇引用论文")
        
    except Exception as e:
        error_msg = f"获取引用论文列表时出错: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["status"] = "error"
    
    return state

# 辅助函数：增强版欧洲机构检测
def is_european_institution(affiliation: str) -> bool:
    """增强版判断机构是否为欧洲机构"""
    # 欧洲国家和地区列表
    european_countries = [
        # 欧盟成员国
        "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic", "Czechia",
        "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
        "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands",
        "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden",
        # 非欧盟欧洲国家
        "United Kingdom", "UK", "Britain", "England", "Scotland", "Wales", "Northern Ireland",
        "Switzerland", "Norway", "Iceland", "Liechtenstein", "Monaco", "San Marino", "Vatican",
        "Serbia", "Bosnia", "Bosnia and Herzegovina", "Albania", "North Macedonia", "Macedonia",
        "Montenegro", "Kosovo", "Ukraine", "Belarus", "Moldova", "Russia", "Turkey",
        "Andorra", "Armenia", "Azerbaijan", "Georgia"
    ]
    
    # 欧洲城市列表
    european_cities = [
        "London", "Paris", "Berlin", "Madrid", "Rome", "Amsterdam", "Brussels", "Vienna",
        "Athens", "Stockholm", "Copenhagen", "Oslo", "Helsinki", "Dublin", "Lisbon", "Prague",
        "Budapest", "Warsaw", "Zurich", "Geneva", "Munich", "Frankfurt", "Milan", "Barcelona",
        "Oxford", "Cambridge", "Edinburgh", "Glasgow", "Manchester", "Heidelberg", "Freiburg",
        "Lyon", "Marseille", "Utrecht", "Rotterdam", "Leuven", "Bologna", "Florence", "Turin",
        "Naples", "Seville", "Valencia", "Porto", "Coimbra", "Lausanne", "Basel", "Bern",
        "Gothenburg", "Uppsala", "Tampere", "Turku", "Aarhus", "Odense", "Bergen", "Trondheim"
    ]
    
    # 欧洲知名大学和研究机构关键词
    european_institutions = [
        # 英国
        "Oxford", "Cambridge", "Imperial College", "UCL", "University College London",
        "Edinburgh", "King's College", "LSE", "London School of Economics", "Manchester",
        "Bristol", "Durham", "Warwick", "St Andrews", "Glasgow", "Queen Mary", "Nottingham",
        "Birmingham", "Sheffield", "Southampton", "Leeds", "Sussex", "York", "Lancaster",
        "Leicester", "Loughborough", "Royal Holloway", "Exeter", "Bath", "Aberdeen",
        # 德国
        "TU München", "LMU Munich", "Ludwig-Maximilians", "Heidelberg", "Humboldt",
        "Free University of Berlin", "RWTH Aachen", "TU Berlin", "Karlsruhe", "KIT",
        "Freiburg", "Tübingen", "Göttingen", "Bonn", "Frankfurt", "Erlangen-Nürnberg",
        "Würzburg", "Hamburg", "Cologne", "Köln", "Mannheim", "Stuttgart", "Dresden",
        "Max Planck", "Helmholtz", "Fraunhofer", "Leibniz",
        # 法国
        "Sorbonne", "École Polytechnique", "Sciences Po", "Université Paris", "ENS Paris",
        "École Normale Supérieure", "CNRS", "CEA", "INRIA", "INSERM", "Pasteur Institute",
        # 其他欧洲国家
        "ETH Zurich", "EPFL", "KU Leuven", "Karolinska", "CERN", "Utrecht", "Leiden",
        "Delft", "TU Delft", "Wageningen", "Copenhagen", "DTU", "Aarhus", "Lund", "Uppsala",
        "Stockholm", "Chalmers", "Helsinki", "Aalto", "Oslo", "Trinity College Dublin",
        "UCD", "Bologna", "Sapienza", "Politecnico di Milano", "Politecnico di Torino",
        "Bocconi", "Barcelona", "Complutense", "Autonoma", "Pompeu Fabra", "Lisbon",
        "Porto", "Vienna", "Innsbruck", "Graz", "Zurich", "Geneva", "Basel", "Lausanne",
        "Bern", "Fribourg", "Ghent", "VUB", "ULB", "Charles University", "Warsaw",
        "Jagiellonian", "Helsinki", "Oslo", "Bergen", "NTNU", "Vienna", "IST Austria"
    ]
    
    # 欧洲机构的不同语言表示
    european_uni_prefixes = [
        "Universität", "Université", "Università", "Universidad", "Universitet",
        "Universiteit", "Uniwersytet", "Univerzita", "Univerza", "Egyetem",
        "Università degli studi di", "Universidade de", "Universitat", "Universitetet i",
        "Universitetet i", "Université de", "Université d'", "Universität zu"
    ]
    
    # 标准化机构名称
    affiliation_normalized = affiliation.lower()
    
    # 检查是否包含欧洲国家名称
    for country in european_countries:
        if country.lower() in affiliation_normalized:
            return True
    
    # 检查是否包含欧洲城市名称
    for city in european_cities:
        if city.lower() in affiliation_normalized:
            return True
    
    # 检查是否为欧洲知名机构
    for institution in european_institutions:
        if institution.lower() in affiliation_normalized:
            return True
    
    # 检查是否使用欧洲语言表示大学
    for prefix in european_uni_prefixes:
        if prefix.lower() in affiliation_normalized:
            return True
    
    # 检查机构域名
    domain_patterns = [
        r'\.ac\.uk', r'\.edu\.[a-z]{2}', r'\.uni-[a-z]+\.de', r'\.edu\.fr', 
        r'\.ac\.[a-z]{2}', r'\.univ-[a-z]+\.fr', r'\.ens\.fr', r'\.mpg\.de',
        r'\.ethz\.ch', r'\.epfl\.ch', r'\.uzh\.ch', r'\.kuleuven\.be'
    ]
    
    for pattern in domain_patterns:
        if re.search(pattern, affiliation_normalized):
            return True
            
    return False

# 节点函数：筛选欧洲机构的论文
def filter_european_papers(state: ScraperState) -> ScraperState:
    """筛选出欧洲大学或研究机构的论文"""
    european_papers = []
    
    for paper in state["cited_papers"]:
        is_european = False
        european_affiliations = []
        
        # 检查每个机构是否为欧洲机构
        for affiliation in paper["affiliations"]:
            if is_european_institution(affiliation):
                is_european = True
                european_affiliations.append(affiliation)
        
        if is_european:
            # 创建输出格式
            output_paper = {
                "paper_name": paper["paper_name"],
                "authors": paper["authors"],
                "affiliations": european_affiliations if european_affiliations else paper["affiliations"],
                "abstract": paper["abstract"]
            }
            european_papers.append(output_paper)
    
    # 更新状态
    state["european_papers"] = european_papers
    state["status"] = "filtered"
    
    logger.info(f"筛选出 {len(european_papers)} 篇欧洲机构的论文")
    
    return state

# 节点函数：输出结果
def export_results(state: ScraperState) -> ScraperState:
    """将结果导出为JSON文件"""
    output_file = f"european_papers_citing_{state['paper_id']}.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(state["european_papers"], f, ensure_ascii=False, indent=2)
        
        state["status"] = "completed"
        logger.info(f"结果已保存到 {output_file}")
    except Exception as e:
        error_msg = f"导出结果时出错: {str(e)}"
        logger.error(error_msg)
        state["errors"].append(error_msg)
        state["status"] = "error"
    
    return state

# 条件函数：检查是否有错误
def has_errors(state: ScraperState) -> bool:
    """检查状态中是否有错误"""
    return len(state["errors"]) > 0

# 构建工作流图
def build_scraper_graph():
    """构建LangGraph工作流"""
    # 创建工作流
    workflow = StateGraph(ScraperState)
    
    # 添加节点
    workflow.add_node("fetch_cited_papers", fetch_cited_papers)
    workflow.add_node("filter_european_papers", filter_european_papers)
    workflow.add_node("export_results", export_results)
    
    # 定义边
    workflow.add_edge("fetch_cited_papers", "filter_european_papers")
    # 添加错误处理
    workflow.add_conditional_edges(
        "fetch_cited_papers",
        has_errors,
        {
            True: END,
            False: "filter_european_papers"
        }
    )

    workflow.add_edge("filter_european_papers", "export_results")
    workflow.add_edge("export_results", END)
    

    
    # 编译工作流
    return workflow.compile()

# 主函数
def main(paper_id: str, max_papers: int = None, pdf_cache_dir: str = "./pdf_cache"):
    """主函数
    
    Args:
        paper_id: Google Scholar论文ID
        max_papers: 最大处理的引用论文数量，默认处理所有
        pdf_cache_dir: PDF缓存目录
    """
    # 初始化状态
    initial_state = initialize_state(paper_id, pdf_cache_dir)
    
    # 构建工作流
    graph = build_scraper_graph()
    
    # 执行工作流
    for event in graph.stream(initial_state):
        if event["type"] == "node":
            node_name = event["node_name"]
            state = event["state"]
            status = state["status"]
            
            logger.info(f"执行节点: {node_name}, 状态: {status}")
            
            if status == "error":
                logger.error("执行过程中出现错误:")
                for error in state["errors"]:
                    logger.error(f"- {error}")
                    
            # 如果设置了最大处理数量，提前结束
            if max_papers and state["progress"] >= max_papers:
                logger.info(f"已达到设定的最大处理数量 {max_papers}，提前结束")
                break
    
    # 返回最终状态
    return graph.get_state()

# 示例使用
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Google Scholar引用论文欧洲机构筛选器')
    parser.add_argument('--paper_id', type=str, help='Google Scholar论文ID')
    parser.add_argument('--max', type=int, default=1000, help='最大处理的引用论文数量')
    parser.add_argument('--log', type=str, default='info', help='日志级别 (debug, info, warning, error)')
    parser.add_argument('--pdf-cache', type=str, default='./pdf_cache', help='PDF缓存目录')
    
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = getattr(logging, args.log.upper(), logging.INFO)
    logging.basicConfig(level=log_level, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("开始执行Google Scholar引用文章欧洲机构筛选器...")
    final_state = main(args.paper_id, args.max, args.pdf_cache)
    
    print("\n执行结果摘要:")
    print(f"总共处理引用文章: {final_state['total']}")
    print(f"欧洲机构论文数量: {len(final_state['european_papers'])}")
    print(f"执行状态: {final_state['status']}")
    
    if final_state["status"] == "completed":
        print(f"结果已保存到 european_papers_citing_{args.paper_id}.json")
    else:
        print("执行未完成，请检查错误信息")