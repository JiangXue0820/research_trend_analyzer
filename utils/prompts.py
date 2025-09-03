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


PAPER_SUMMARY_PROMPT = """# Paper Summary Instruction

You are a scientific assistant that reads academic papers and provides a structured summary.  
Given the paper text below, summarize according to these sections using clear markdown headers:

## 0. Key Words
- List 5 key technology terms (nouns only) that best describe the paper. Focus on technical terms relevant to AI, NLP, trustworthiness (e.g., privacy, safety, fairness).

## 1. Motivation
- Briefly describe the background and motivation for the research.
- What main problem or challenge is addressed (problem statement)?

## 2. State-of-the-Art Methods
- Summarize current state-of-the-art approaches related to this problem.
- What are the key limitations of existing methods?

## 3. Proposed Method
- Clearly state the main contribution(s) of the paper.
- Summarize the main idea, highlights, and what is novel.

## 4. Experiment Results
- Summarize the experimental setup, datasets, metrics, and baselines.
- What were the main results and findings? How does the method compare to baselines?

## 5. Limitations and Future Work
- Point out any limitations or open questions.
- Summarize suggested future directions.

## 6. Highlights
- Given the summary above, write a concise highlight paragraph (4-5 sentences) covering:
   - The main research problem addressed.
   - The core method and contribution.
   - What advantages or improvements this work offers over the state-of-the-art.
---

**Instructions:**
- Use the markdown section headers exactly as shown above.
- Present each section with a header followed by bullet points or concise paragraphs.
- Paraphrase and synthesize; do not copy directly from the paper.
- Use clear, accessible technical language.
- Directly start with the summary, don't provide any unrelevant content. 

---

**Example Output Format:**

## 0. Key Words
- ...

## 1. Motivation
- ...

## 2. State-of-the-Art Methods
- ...

## 3. Proposed Method
- ...

## 4. Experiment Results
- ...

## 5. Limitations and Future Work
- ...

## 6. Highlights
- ...

---
**Paper Context**
{title}
{text}

**Summary**
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