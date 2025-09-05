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


PAPER_SUMMARY_PROMPT_CH="""# 请按照以下规定，对学术论文进行分析并输出中文总结，需严格遵循指定格式：

## Paper Info
* 题目： 文章题目
* 作者： 作者清单，按原顺序排列
* 机构： 所有机构的名称，注意去掉上下角标

## 0. Abstract
*   亮点：撰写一段 4-5 句话的内容，需涵盖论文所解决的主要研究问题、核心方法及创新贡献，以及相比现有技术的优势（需包含关键结果数据）。
*   关键词：列出 5 个最能描述论文的关键技术术语（仅为名词），重点聚焦与人工智能、自然语言处理、可信度（如隐私、安全性、公平性）相关的技术术语。

## 1. Motivation
*   简要描述研究的背景和动机。
*   明确阐述论文所解决的主要问题或挑战（问题陈述）。

## 2. State-of-the-Art Methods
*   总结与该问题相关的当前最先进方法。
*   指出现有方法的主要局限性。

## 3. Proposed Method
*   清晰说明论文的主要贡献。
*   总结核心思想、亮点以及创新之处。

## 4. Experiment Results
*   概述实验设置，包括数据集、指标和基线方法。
*   说明主要结果和发现，以及该方法与基线方法的对比情况。

## 5. Limitations and Future Work
*   指出研究存在的局限性或未解决的问题。
*   总结论文提出的未来研究方向。

**注意事项：**
*   严格使用上述所示的 markdown 部分标题。
*   每个部分均以标题开头，后续内容使用 bullet points 或简洁段落呈现。
*   对内容进行释义和综合，不得直接抄袭论文原文。
*   使用清晰、易懂的技术语言。
*   直接输出总结内容，不添加任何无关信息。

# Task
下面，请按照要求，总结这篇文章：
**Paper Context**
{text}

**Summary**
"""

PAPER_SUMMARY_PROMPT_EN="""# Please analyze the academic paper and output a Chinese summary in accordance with the following regulations, strictly adhering to the specified format:

## Paper Info
* Title: Title of the article
* Authors: List of authors, in the original order
* Institutions: Names of all institutions, with superscript/subscript symbols removed

## 0. Abstract
* Highlights: Write a 4-5 sentence content that covers the main research questions addressed by the paper, the core methods and innovative contributions, as well as the advantages compared to existing technologies (including key result data).
* Keywords: List 5 key technical terms that best describe the paper (nouns only), focusing on terms related to artificial intelligence, natural language processing, and trustworthiness (such as privacy, security, fairness).

## 1. Motivation
* Briefly describe the background and motivation of the research.
* Clearly state the main problems or challenges addressed by the paper (problem statement).

## 2. State-of-the-Art Methods
* Summarize the current state-of-the-art methods related to the problem.
* Point out the main limitations of existing methods.

## 3. Proposed Method
* Clearly explain the main contributions of the paper.
* Summarize the core ideas, highlights, and innovations.

## 4. Experiment Results
* Outline the experimental setup, including datasets, metrics, and baseline methods.
* Explain the main results and findings, as well as the comparison between this method and baseline methods.

## 5. Limitations and Future Work
* Identify the limitations of the research or unsolved problems.
* Summarize the future research directions proposed in the paper.

**Notes:**
* Strictly use the markdown section headings shown above.
* Each section starts with a heading, followed by content presented in bullet points or concise paragraphs.
* Paraphrase and synthesize the content; do not directly copy the original text of the paper.
* Use clear and understandable technical language.
* Output the summary content directly without adding any irrelevant information.

# Task
Now, please summarize this article in accordance with the requirements:
**Paper Context**
{text}

**Summary**
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
