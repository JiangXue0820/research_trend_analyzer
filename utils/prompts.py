KEYWORDS_GENERATION_PROMPT = """You are an assistant that generates comprehensive keyword lists for academic research topics.

TASK:
Given a topic string, return a Python list of strings.

REQUIREMENTS:
- Include AT LEAST 10 unique, relevant keywords.
- Keywords should be primarily single words, but include common multi-word technical phrases if necessary.
- Cover:
  * Core terms (directly matching the topic)
  * Variants (noun, verb, adjective forms, abbreviations, synonyms)
  * Subfields and branches
  * Technical terms, methods, and related concepts
- Ensure coverage across both foundational and emerging subtopics.
- Output ONLY the Python list (no dicts, no explanations, no formatting beyond the list).
- Output MUST be valid Python code.

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


PAPER_SUMMARY_PROMPT_CH="""<Instructions>
作为计算机科学领域的专家，请对<Article Content>中提供的学术论文进行详细分析，并输出中文总结。请务必严格遵循后续 <Output Format (Markdown)> 部分中规定的所有Markdown标题、结构和要求——确保总结的每一部分都与提供的模板完全一致。

**注意事项：**
* 严格遵守<Output Format (Markdown)>中列出的Markdown部分标题。
* 每个部分都必须以指定的标题开头，内容以bullet point或简洁段落的形式呈现。
* 对论文内容进行释义和综合，禁止直接抄袭原文。
* 使用清晰、易懂的技术语言。
* 仅输出总结内容，不添加任何无关信息或额外解释。
</Instructions>

<Article Content>
{text}
</Article Content>

<Output Format (Markdown)>

# Paper Info

## Title
文章题目。

## Authors
文章作者，按照 [作者 1, 作者 2] 的形式。

## Affiliations
作者所属机构，按照 [(机构 1, 国家 1), (机构 2, 国家 2)] 的形式。

# Brief Summary

## Highlight
撰写一段 4-5 句话的内容，需涵盖论文所解决的主要研究问题、核心方法及创新贡献，以及相比现有技术的优势（需包含关键结果数据）。

## Keywords
按照 [术语1, 术语2...]的格式，列出 5 个最能描述论文的中文关键词（仅为名词），用于匹配文章的研究分支、研究课题、关键技术。

# Detailed Summary

## 1. Motivation

### 1.1 Background
简要描述研究的背景和动机。

### 1.2 Problem Statement
明确阐述论文所解决的主要问题或挑战（问题陈述）。

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
总结与该问题相关的当前最先进方法。

### 2.2 Limitations of Existing Methods
指出现有方法的主要局限性。

## 3. Proposed Method

### 3.1 Main Contributions
清晰说明论文通过提出什么方案，解决了什么关键问题。

### 3.2 Core Idea
概述方案的核心设计思路或原理（如技术框架、关键机制等）。

### 3.3 Novelty
阐述方案相比现有技术的创新点（如首次提出的技术、组合方式或优化方向）。

## 4. Experiment Results

### 4.1 Experimental Setup
概述实验所用数据集、对比的基线方法及关键评价指标。

### 4.2 Experimental Results
说明主要结果和发现，以及该方法与基线方法的对比情况。

## 5. Limitations and Future Work

### 5.1 Limitations
指出当前研究存在的不足或未解决的问题。

### 5.2 Future Directions
说明论文提出的后续研究方向或改进思路。

</Output Format (Markdown)>

<Summary>
[请提供符合上述要求的高质量总结]
</Summary>
"""

PAPER_SUMMARY_PROMPT_EN="""<Instructions>
As an expert in computer science, please conduct a detailed analysis of the academic paper provided in <Article Content> and output an English summary. 
It is crucial to strictly follow all the Markdown headings, structure, and requirements specified in the subsequent <Output Format (Markdown)> section—ensure every part of the summary aligns perfectly with the template provided.

**Notes:**
* Adhere strictly to the markdown section headings as outlined in <Output Format (Markdown)>.
* Each section must start with the specified heading, with content presented as bullet points or concise paragraphs.
* Paraphrase and synthesize the paper's content; direct copying of the original text is prohibited.
* Use clear, accessible technical language.
* Output only the summary content without any irrelevant information or additional explanations.
</Instructions>

<Article Content>
{text}
</Article Content>

<Output Format (Markdown)>

# Paper Info

## Title
Title of the article.

## Authors
Authors of the article, in the form of [Author 1, Author 2, ...].

## Affiliations
Affiliations of the authors, in the form of [(Institution 1, Country 1), (Institution 2, Country 2)...].

# Brief Summary

## Highlight
Write a 4-5 sentence section that covers the main research problems addressed by the paper, the core methods and innovative contributions, as well as the advantages over existing technologies (including key result data).

## Keywords
Following the format of [Term 1, Term 2...], list five English keywords (nouns only) that can best describe the paper and best match its research branch, research topic, and key technology of the article.

# Detailed Summary

## 1. Motivation

### 1.1 Background
Briefly describe the background and motivation of the research.

### 1.2 Problem Statement
Clearly state the main problems or challenges addressed in the paper (problem statement).

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
Summarize the current state-of-the-art methods related to the problem.

### 2.2 Limitations of Existing Methods
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

### 5.1 Limitations
Point out the shortcomings or unsolved problems of the current research.

### 5.2 Future Directions
Explain the proposed future research directions or improvement ideas in the paper.

</Output Format (Markdown)>

<Summary>
[Please provide a high-quality summary that fulfills the above requirements]
</Summary>
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
