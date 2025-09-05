KEYWORDS_GENERATION_PROMPT = """You are an assistant that generates comprehensive keyword lists for academic research topics.

TASK:
Given a topic string, return a Python list of strings.

REQUIREMENTS:
- Include at least 10 relevant keywords.
- Cover verb, noun, adjective forms, common phrases, technical terms, subfields, related concepts, and synonyms/abbreviations.
- Include both core terms and popular subtopics.
- Output only the Python list (no dict, no extra text).
- Output must be valid Python code.

OUTPUT FORMAT (strict):
["...", "...", "..."]

EXAMPLES:

Topic="privacy"
Output=["privacy", "private", "anonymity", "anonymous", "data protection", "federated learning"]

Topic="safety"
Output=["safety", "safe", "safety alignment", "robustness", "risk assessment", "safety risk"]

Topic="attack"
Output=["attack", "membership inference", "model inversion", "memorization", "backdoor", "jailbreak", "red-team", "poison"]


Now, do the same for this topic:
Topic="{topic}"
Output=
"""

PAPER_HIGHLIGHT_PROMPT = """## Highlight Summarization
Given the summary of an academic paper, write a concise highlight paragraph (4-5 sentences) covering:

- The main research problem addressed.
- The core method and contribution.
- What advantages or improvements this work offers over the state-of-the-art (novelty and experiment result).

Use clear and direct language. Focus on what distinguishes this paper within its field.
"""

RESEARCH_TREND_PROMPT = """## Research Trend Summarization
You are an AI assistant summarizing the research trend of a specific topic at a given academic conference (and year, if specified). 
Given the highlight summaries of multiple papers from a specific conference and topic, analyze the research trend as follows:

- Group the papers into clusters based on key technology directions or subfields within the topic.
- For each cluster, briefly summarize the common research focus and key advances.
- Identify emerging trends, major breakthroughs, and notable gaps in the field.
- Conclude with an overview of the overall direction and significance of current research in this topic at the conference.

Use clear section headings for each technology direction. Be concise, objective, and insightful.
"""


PAPER_SUMMARY_PROMPT_CH="""作为计算机科学专家，请对我提供的一篇学术论文进行详细分析，并严格遵循下面的格式输出中文总结：

**文章内容**
{text}

**输出格式 (Markdown格式）**

# Paper Info

## Title
文章题目
## Authors
文章作者，按照 [作者 1, 作者 2, ...] 的形式
## Affiliations
作者所属机构，按照 [(机构 1, 国家 1), (机构 2, 国家 2)...] 的形式

# Brief Summary

## Highlight
撰写一段 4-5 句话的内容，需涵盖论文所解决的主要研究问题、核心方法及创新贡献，以及相比现有技术的优势（需包含关键结果数据）。

## Keywords
按照 [术语1, 术语2...]的格式，列出 5 个最能描述论文的关键技术术语（仅为名词），重点聚焦与人工智能、自然语言处理、可信度（如隐私、安全性、公平性）相关的技术术语。

# Detailed Summary

## 1. Motivation
### 1.1 背景
简要描述研究的背景和动机。
### 1.2 问题
明确阐述论文所解决的主要问题或挑战（问题陈述）。

## 2. State-of-the-Art Methods
### 2.1 现有方法
总结与该问题相关的当前最先进方法。
### 2.2 局限性
指出现有方法的主要局限性。

## 3. Proposed Method
### 3.1 主要贡献
清晰说明论文通过提出什么方案，解决了什么关键问题。
### 3.2 核心思想
概述方案的核心设计思路或原理（如技术框架、关键机制等）。
### 3.3 新颖性
阐述方案相比现有技术的创新点（如首次提出的技术、组合方式或优化方向）。

## 4. Experiment Results
### 4.1 实验设置
概述实验所用数据集、对比的基线方法及关键评价指标。
### 4.2 实验结果
说明主要结果和发现，以及该方法与基线方法的对比情况。

## 5. Limitations and Future Work
5.1 局限性
指出当前研究存在的不足或未解决的问题。
5.2 未来方向
说明论文提出的后续研究方向或改进思路。

**注意事项：**
*   严格使用上述所示的 markdown 部分标题。
*   每个部分均以标题开头，后续内容使用 bullet points 或简洁段落呈现。
*   对内容进行释义和综合，不得直接抄袭论文原文。
*   使用清晰、易懂的技术语言。
*   直接输出总结内容，不添加任何无关信息。

**请总结**
"""

PAPER_SUMMARY_PROMPT_EN="""As an expert in computer science, please conduct a detailed analysis of an academic paper I will provide and output a Chinese summary in strict accordance with the following format:

**Article Content**
{text}

**Output Format (Markdown Format)**

# Paper Info

## Title
Title of the article
## Authors
Authors of the article, in the form of [Author 1, Author 2, ...]
## Affiliations
Affiliations of the authors, in the form of [(Institution 1, Country 1), (Institution 2, Country 2)...]

# Brief Summary

## Highlight
Write a 4-5 sentence section that covers the main research problems addressed by the paper, the core methods and innovative contributions, as well as the advantages over existing technologies (including key result data).

## Keywords
List 5 key technical terms that best describe the paper in the form of [Term 1, Term 2...]. These terms should only be nouns, with a focus on those related to artificial intelligence, natural language processing, and trustworthiness (such as privacy, security, fairness).

# Detailed Summary

## 1. Motivation
### 1.1 Background
Briefly describe the background and motivation of the research.
### 1.2 Problem
Clearly state the main problems or challenges addressed in the paper (problem statement).

## 2. State-of-the-Art Methods
### 2.1 Existing Methods
Summarize the current state-of-the-art methods related to the problem.
### 2.2 Limitations
Point out the main limitations of existing methods.

## 3. Proposed Method
### 3.1 Main Contributions
Clearly explain what solution the paper proposes to solve key problems.
### 3.2 Core Idea
Outline the core design ideas or principles of the solution (such as technical frameworks, key mechanisms, etc.).
### 3.3 Novelty
Elaborate on the innovations of the proposed method compared to existing technologies (such as newly proposed technologies, combination methods, or optimization directions).

## 4. Experiment Results
### 4.1 Experimental Setup
Outline the datasets used in the experiments, the baseline methods for comparison, and key evaluation metrics.
### 4.2 Experimental Results
Explain the main results and findings, as well as the comparison between this method and baseline methods.

## 5. Limitations and Future Work
5.1 Limitations
Point out the shortcomings or unsolved problems of the current research.
5.2 Future Directions
Explain the proposed future research directions or improvement ideas in the paper.

**Notes:**
* Strictly use the markdown section headings as shown above.
* Each section starts with a heading, and the subsequent content is presented using bullet points or concise paragraphs.
* Paraphrase and synthesize the content; do not directly copy the original text of the paper.
* Use clear and understandable technical language.
* Output the summary content directly without adding any irrelevant information.

**Please summarize**
"""


# PAPER_SUMMARY_PROMPT = """# Paper Summary Instruction

# You are a scientific assistant that reads academic papers and provides a structured summary.  
# Given the paper text below, summarize according to these sections using clear markdown headers:

# ## 0. Key Words
# - List 5 key technology terms (nouns only) that best describe the paper. Focus on technical terms relevant to AI, NLP, trustworthiness (e.g., privacy, safety, fairness).

# ## 1. Motivation
# - Briefly describe the background and motivation for the research.
# - What main problem or challenge is addressed (problem statement)?

# ## 2. State-of-the-Art Methods
# - Summarize current state-of-the-art approaches related to this problem.
# - What are the key limitations of existing methods?

# ## 3. Proposed Method
# - Clearly state the main contribution(s) of the paper.
# - Summarize the main idea, highlights, and what is novel.

# ## 4. Experiment Results
# - Summarize the experimental setup, datasets, metrics, and baselines.
# - What were the main results and findings? How does the method compare to baselines?

# ## 5. Limitations and Future Work
# - Point out any limitations or open questions.
# - Summarize suggested future directions.

# ## 6. Highlights
# - Given the summary above, write a concise highlight paragraph (4-5 sentences) covering:
#    - The main research problem addressed.
#    - The core method and contribution.
#    - What advantages or improvements this work offers over the state-of-the-art.
# ---

# **Instructions:**
# - Use the markdown section headers exactly as shown above.
# - Present each section with a header followed by bullet points or concise paragraphs.
# - Paraphrase and synthesize; do not copy directly from the paper.
# - Use clear, accessible technical language.
# - Directly start with the summary, don't provide any unrelevant content. 

# ---

# **Example Output Format:**

# ## 0. Key Words
# - ...

# ## 1. Motivation
# - ...

# ## 2. State-of-the-Art Methods
# - ...

# ## 3. Proposed Method
# - ...

# ## 4. Experiment Results
# - ...

# ## 5. Limitations and Future Work
# - ...

# ## 6. Highlights
# - ...

# ---
# **Paper Context**
# {title}
# {text}

# **Summary**
# """
