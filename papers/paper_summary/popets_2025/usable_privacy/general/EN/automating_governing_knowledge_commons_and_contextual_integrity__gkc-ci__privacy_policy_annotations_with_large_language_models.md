# Paper Info

## Title
Automating Governing Knowledge Commons and Contextual Integrity (GKC-CI) Privacy Policy Annotations with Large Language Models

## Authors
Jake Chanenson, Madison Pickering, Noah Apthorpe

## Affiliations
(University of Chicago, USA), (Colgate University, USA)

# Brief Summary

## Highlight
This paper addresses the challenge of analyzing complex privacy policies by automating annotations based on the Governing Knowledge Commons and Contextual Integrity (GKC-CI) framework. The core method involves fine-tuning various large language models (LLMs) on a manually annotated dataset to automatically identify eight key GKC-CI parameters within policy texts. The primary contribution is a highly accurate and scalable annotation model that significantly reduces the time and cost associated with manual analysis. The best-performing model, a fine-tuned GPT-3.5 Turbo, achieves a 90.65% accuracy, which is comparable to human experts and far surpasses previous crowdsourcing and classical machine learning approaches, enabling large-scale longitudinal and cross-industry policy analysis.

## Keywords
Privacy Policies, Large Language Models, Contextual Integrity, Text Annotation, Natural Language Processing

# Detailed Summary

## 1. Motivation

### 1.1 Background
Privacy policies are legally significant documents that are notoriously difficult for users to comprehend due to their length and use of "legalese." To make these policies more transparent and analyzable, researchers have adopted annotation techniques. The theory of Contextual Integrity (CI), expanded by the Governing Knowledge Commons (GKC) framework, provides a robust theoretical foundation for this task. The unified GKC-CI framework uses eight specific parameters (e.g., sender, recipient, attribute) to describe information flows, which helps identify ambiguities and potential privacy violations in data handling practices.

### 1.2 Problem Statement
Previous methods for GKC-CI annotation relied on manual effort from experts or crowdworkers. Manual annotation is highly accurate but extremely slow and tedious, making large-scale analysis impractical. Crowdsourcing is faster but suffers from high error rates and significant costs, as multiple workers are needed to achieve reasonable quality. Existing automated privacy policy analysis tools do not use the GKC-CI framework, rendering them unsuitable for research grounded in CI theory. Therefore, there is a need for an automated, accurate, and scalable method to perform GKC-CI annotations.

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
*   **The Usable Privacy Project:** This project used expert and crowdworker annotations to label privacy policies with a custom set of tags (e.g., "first party collection/use"). They later trained classical machine learning models like SVMs and CNNs to automate this specific annotation task.
*   **Manual and Crowdsourced CI Annotation:** Early CI-based policy analysis, pioneered by Shvartzshnaider et al., relied exclusively on manual annotation by experts or a voting-based system with multiple crowdworkers to identify the five original CI parameters in policy excerpts.
*   **Other ML-based Policy Analysis:** Various studies have applied machine learning to privacy policies for tasks such as creating question-answering systems, identifying opt-out statements, or detecting non-compliance with app behavior, but none have focused on GKC-CI parameter extraction.

### 2.2 Limitations of Existing Methods
*   **Lack of Scalability and High Cost:** Manual and crowdsourced methods are inherently unscalable, slow, and expensive, hindering large-scale and longitudinal studies.
*   **Incompatible Annotation Frameworks:** Existing automated tools, like those from the Usable Privacy Project, use annotation tags that are not based on the GKC-CI framework, making their outputs irrelevant for the GKC and CI research communities.
*   **Absence of Automation for GKC-CI:** No prior research has successfully automated the nuanced task of identifying the eight GKC-CI parameters in legal texts.

## 3. Proposed Method

### 3.1 Main Contributions
*   The paper demonstrates that a fine-tuned LLM can automate GKC-CI annotation of privacy policies with an accuracy comparable to that of human experts, substantially improving scalability and reducing costs.
*   It publicly releases the training data, model training scripts, an annotation visualizer, and a large corpus of 456 annotated privacy policies to support future research in this domain.
*   The research includes a large-scale application of the model, conducting both longitudinal and cross-industry analyses of privacy policies to showcase the practical utility of automated GKC-CI annotation.

### 3.2 Core Idea
The core of the proposed method is to fine-tune LLMs for a text-tagging task. The researchers created a ground-truth dataset by manually annotating 16 privacy policies with the eight GKC-CI parameters. This data was then formatted into training examples, where each example consists of a single sentence from a policy, a target parameter to identify, and the corresponding text snippet (or "N/A" if absent). The study systematically trained and evaluated 50 different LLMs—spanning open-source and proprietary families like Flan-T5, Llama2, and GPT—to find the most effective model for this specific task.

### 3.3 Novelty
*   **First Automation of GKC-CI:** This is the first study to successfully automate the annotation of privacy policies using the theoretically grounded GKC-CI framework, a task previously performed only by humans.
*   **Application of Modern LLMs:** The work leverages the advanced capabilities of modern LLMs for a nuanced legal text analysis task, demonstrating their superiority over both classical NLP models and prompted, non-fine-tuned LLMs.
*   **Enabling Large-Scale Normative Analysis:** The developed method enables GKC-CI analysis at an unprecedented scale, making longitudinal and broad cross-industry studies feasible for the first time.

## 4. Experiment Results

### 4.1 Experimental Setup
*   **Dataset:** The study used a dataset of 21,588 human-annotated GKC-CI parameters extracted from 16 privacy policies, split into a 70% training set and a 30% testing set.
*   **Baselines:** The performance of fine-tuned LLMs was compared against two baselines: a classical recurrent neural network (RNN) and several non-fine-tuned LLMs (e.g., GPT-4) using few-shot prompting.
*   **Evaluation Metrics:** The primary metric was accuracy, defined as an exact string match between the model's generated annotation and the ground-truth text. A qualitative error analysis was also conducted to understand the nature of model mistakes.

### 4.2 Experimental Results
*   **Superiority of Fine-Tuned LLMs:** The fine-tuned LLMs drastically outperformed the baselines. The RNN achieved only 6% accuracy, while the best-prompted LLM scored under 20%.
*   **Top Model Performance:** The best-performing model, a prompt-engineered version of GPT-3.5 Turbo fine-tuned for 25 epochs (GPT 3.5TPE_25ep), achieved an accuracy of 90.65% on the test set.
*   **Human-Level Accuracy:** A review of the training data revealed a 90.57% inter-annotator agreement rate among human experts. The model's accuracy of 90.65% suggests it performs the task at a level comparable to trained human annotators.
*   **Qualitative Analysis:** A manual analysis of the model's errors revealed that over half were not true mistakes but either semantically equivalent answers or instances where the model's annotation was more precise than the original human label. This indicates the 90.65% accuracy is a conservative estimate of the model's true performance.

## 5. Limitations and Future Work

### 5.1 Limitations
*   **Framework Mismatch:** Privacy policies are not written with the GKC-CI framework in mind, which means a perfect mapping from text to parameters is not always possible.
*   **Limited Context:** The model operates on a sentence-by-sentence basis and lacks a holistic understanding of the entire document, unlike a human analyst who can use broader context.
*   **No Coreference Resolution:** The system does not identify when different text segments refer to the same entity (e.g., multiple mentions of "the user"). This task is considered out of scope and left for future work.

### 5.2 Future Directions
*   **Automated Privacy Audits:** The annotation model can serve as the initial step in an automated pipeline to audit data practices. Extracted parameters could be used to generate surveys that assess whether a company's data practices align with societal norms.
*   **Broader Document Analysis:** The method could be extended beyond privacy policies to analyze information flows described in other documents, such as academic papers, media reports, or internal corporate documents.
*   **Enhanced Policy Review Tools:** The developed annotation visualizer and the large annotated corpus can be used to build tools that help researchers, regulators, and consumers quickly identify and understand significant changes in privacy policy updates.