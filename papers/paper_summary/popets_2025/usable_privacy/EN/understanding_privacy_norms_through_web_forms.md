# Paper Info

## Title
Understanding Privacy Norms through Web Forms 

## Authors
[Hao Cui, Rahmadi Trimananda, Athina Markopoulou]

## Affiliations
[(University of California, Irvine, USA)].

# Brief Summary

## Highlight
This paper addresses the under-studied area of personal information (PI) collection through web forms by conducting a large-scale measurement study. The core methodology involves a custom web crawler to collect 293K web forms from 11,500 popular websites, followed by a novel, cost-efficient annotation pipeline using Large Language Models (LLMs) and active learning to classify form types and PI types. The study's key contribution is a data-driven approach to extracting "privacy norms"—common standards of appropriate data collection—by analyzing widespread practices. Key findings reveal that common collection patterns are often justified by functional or legal needs, deviations from these norms can signal excessive data collection, and there is a significant disconnect between the PI collected in forms and the disclosures made in corresponding privacy policies.

## Keywords
[Web Forms, Privacy Norms, Data Collection, Measurement Study, Privacy Policies]

# Detailed Summary

## 1. Motivation

### 1.1 Background
Websites collect personal information (PI) both implicitly through tracking and explicitly through web forms. While web tracking has been extensively researched, PI collection via web forms remains a relatively unexplored area from a privacy perspective. Unlike tracking, web forms make data collection explicit and contextual: users know what information is being asked for and the specific purpose (e.g., creating an account). For users to trust these forms, the data collection must align with "privacy norms"—socially accepted standards of what information is appropriate to collect in a given context.

### 1.2 Problem Statement
The paper identifies three main challenges:
*   There is a lack of large-scale, empirical understanding of how PI is collected through web forms across different contexts.
*   Privacy norms are often implicit and have primarily been studied through user surveys of hypothetical scenarios, rather than being derived from actual, widespread practices.
*   It is unclear whether legally mandated privacy policies accurately reflect the actual data collection practices observed in web forms.

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
*   **Privacy Norm Research:** Traditionally relies on the Contextual Integrity (CI) framework and uses vignette surveys to gauge user perceptions of appropriateness in hypothetical data-sharing scenarios.
*   **Privacy Policy Analysis:** Legal frameworks like GDPR and CCPA mandate transparent disclosures through privacy policies. Research in this area uses Natural Language Processing (NLP) to analyze policy texts, often uncovering compliance issues, vagueness, and missing information.
*   **Web Data Collection Measurement:** The majority of privacy measurement studies have focused on implicit and often opaque data collection mechanisms like third-party tracking, cookies, and fingerprinting, largely overlooking the explicit collection happening via web forms.

### 2.2 Limitations of Existing Methods
*   Survey-based methods for understanding privacy norms are based on user responses to hypothetical situations, which may not reflect the reality of data collection practices in the wild.
*   Analyses of privacy policies are limited to what companies *claim* to do, which can be overly broad, vague, or disconnected from their actual practices.
*   Existing measurement studies do not capture the explicit, user-initiated, and contextual nature of PI collection that occurs through web forms.

## 3. Proposed Method

### 3.1 Main Contributions
The paper's primary contribution is a novel, measurement-based approach to understanding privacy norms. This is achieved through:
*   The first large-scale measurement study of PI collection via web forms, resulting in an annotated dataset of 293K forms from 11,500 websites.
*   A data-driven methodology for extracting privacy norms by identifying common PI collection patterns and showing they are rooted in functional necessity and legal obligations.
*   A cost-efficient technical methodology for large-scale data annotation, featuring a specialized web crawler and a machine learning system that uses LLMs and active learning.

### 3.2 Core Idea
The core idea is to infer de facto privacy norms by observing the aggregate data collection behaviors of popular websites. The methodology consists of four key stages:
1.  **Web Form Collection:** A custom browser-based crawler is built to navigate popular websites, simulate user clicks, and discover and download both static and dynamic web forms.
2.  **Dataset Annotation:** A machine learning system is developed to annotate the collected forms. To manage costs, it uses knowledge distillation, where a powerful LLM (GPT-3.5) generates labels for a small subset of data, which is then used to train smaller, efficient classifiers for form type and PI type. Active learning is used to intelligently select samples for the LLM to label, improving model performance on rare categories.
3.  **Web Form Analysis:** The annotated dataset is statistically analyzed to identify common patterns of PI collection within specific contexts, defined by website category (e.g., "Health") and form type (e.g., "Account Registration").
4.  **Privacy Policy Analysis:** The privacy policies associated with the websites are analyzed using an existing NLP tool (PoliGraph-er) to compare disclosed collection practices with the observed practices.

### 3.3 Novelty
*   **Data-Driven Norm Extraction:** It moves beyond hypothetical surveys by using empirical data from actual web forms to discover and define privacy norms.
*   **Focus on Web Forms:** It is the first study to conduct a large-scale analysis of first-party PI collection through web forms, an important but neglected area.
*   **Efficient Annotation Pipeline:** It introduces a practical and cost-effective method for annotating a massive dataset of semi-structured web content by combining knowledge distillation from an LLM with active learning, making such large-scale studies feasible.

## 4. Experiment Results

### 4.1 Experimental Setup
*   **Dataset:** The study created a new dataset of 292,655 web forms collected from 11,500 top English-language websites on the Tranco list. Forms were annotated with one of 10 form types (e.g., `Payment`, `Subscription`) and any of 16 PI types (e.g., `Email Address`, `Date of Birth`).
*   **Baseline Methods:** The work is foundational and does not compare against a direct baseline for norm extraction. The evaluation of its findings is qualitative and based on statistical analysis of the dataset.
*   **Evaluation Metrics:** The analysis primarily uses the "collection rate"—the percentage of websites in a given context that collect a specific PI type. Classifier performance was validated using precision against manual annotations (85.6% for form types, 93.5% for PI types).

### 4.2 Experimental Results
*   **Common Patterns as Norms:** The analysis revealed distinct patterns that reflect privacy norms. For instance, `Email Address` is collected almost universally, while `Phone Number` and `Address` are more common on sites with real-world services (e.g., Health, Finance). The collection of `Date of Birth` during account registration is a widespread norm, likely driven by compliance with children's privacy laws (COPPA).
*   **Deviations from Norms:** Cases that deviated from common patterns often pointed to excessive or unnecessary data collection. For example, a small number of e-commerce sites requested a user's birth date for a simple newsletter subscription, a practice not common for that form type.
*   **Disconnect with Privacy Policies:** The analysis found a significant gap between observed practices and policy disclosures. Many websites either failed to disclose PI types they collected (omission) or used "blanket" disclosures, claiming to collect sensitive PI (like Social Security Numbers) that was never observed in their forms and was contextually inappropriate. The statistical association between collection and disclosure was weak across all PI types.

## 5. Limitations and Future Work

### 5.1 Limitations
*   **Limited Coverage:** The crawler cannot access forms behind logins or on subsequent pages of a multi-page form, which may lead to an underestimation of PI collection. The study is also limited to English websites crawled from a U.S. location, making the findings U.S.-centric.
*   **Coarse Context Definition:** The definitions for website category and form type are high-level and may not fully capture the specific purpose of data collection, limiting the granularity of the analysis.
*   **NLP and Classifier Errors:** The machine learning models used for annotation are not perfect, and classification errors could affect the aggregate statistics.
*   **Not an Auditing Tool:** The methodology is designed to identify broad trends and norms, not to serve as an automated tool for auditing individual websites for privacy violations, due to the aforementioned limitations.

### 5.2 Future Directions
*   **Privacy Risk Assessment Tools:** The extracted norms could be used as a baseline to develop browser extensions or other tools that warn users when a website's data request deviates from common practice, indicating a potential privacy risk.
*   **Comparison with User Perceptions:** An interesting avenue for future research is to compare the data-driven norms identified in this study with user expectations gathered through traditional surveys to identify areas of misalignment.
*   **Deeper Contextual Analysis:** Future work could perform a more in-depth analysis of specific contexts, such as how web forms adapt their data collection practices based on user-disclosed age to comply with regulations like COPPA.