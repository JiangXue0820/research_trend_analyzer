# Paper Info

## Title
Privacy Bills of Materials (PriBOM): A Transparent Privacy Information Inventory for Collaborative Privacy Notice Generation in Mobile App Development

## Authors
Zhen Tao, Shidong Pan, Zhenchang Xing, Xiaoyu Sun, Omar Haggag, John Grundy, Jingjie Li, Liming Zhu

## Affiliations
(CSIRO’s Data61 & Australian National University, Australia), (Australian National University, Australia), (Monash University, Australia), (University of Edinburgh, United Kingdom), (CSIRO’s Data61 & UNSW, Australia).

# Brief Summary

## Highlight
Mobile app developers face significant challenges in creating authentic and comprehensive privacy notices due to lack of privacy knowledge, technical opacity of data practices, and unsupportive organizational environments. This paper introduces PriBOM (Privacy Bills of Materials), a systematic software engineering approach that provides a UI-indexed, transparent privacy information inventory to facilitate collaborative privacy notice generation. PriBOM leverages different development team roles, integrating static and privacy notice analysis for pre-filling. A human evaluation with 150 diverse participants demonstrated high perceived usefulness, with 83.33% agreement on PriBOM enhancing privacy-related communication, suggesting its potential as a significant privacy support solution in mobile app DevOps.

## Keywords
[Privacy, Transparency, Mobile Applications, Privacy Notices, Collaboration]

# Detailed Summary

## 1. Motivation

### 1.1 Background
Privacy regulations like GDPR, CCPA, and APP mandate that mobile application developers provide accurate and understandable privacy notices, such as privacy policies and privacy labels (e.g., Google Play's Data Safety Sections, Apple Privacy Labels), to inform users about data collection and usage. However, existing privacy notices are often problematic, failing to align with actual data practices, leading to user distrust and regulatory violations.

### 1.2 Problem Statement
Developers struggle with creating authoritative privacy notices due to several challenges:
*   **Privacy Knowledge Absence:** Developers frequently lack training and knowledge in privacy and legal fields, leading to misunderstandings of privacy terms and difficulties in keeping up with evolving platform and legal requirements.
*   **Limited Technical Knowledge:** There is opacity regarding data handling practices, particularly with Third-Party Libraries (TPLs), making it hard to ensure data minimization or be aware of privacy-preserving alternatives. Existing tools offer limited support in understanding actual data practices.
*   **Unfriendly Organizational Environment:** Developers often hold negative or demotivated attitudes towards privacy, which is often considered a non-functional requirement. There is a lack of clear ownership for privacy responsibilities and insufficient team or organizational support, leaving legal teams feeling isolated. Existing privacy notice generation tools are not designed for the complexity of sophisticated mobile apps or the collaborative needs of large development teams.

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
Current approaches to assist privacy notice generation can be categorized into three main types:
*   **Online Automated Privacy Policy Generators (APPGs):** These are typically questionnaire-based online tools that generate policies based on developer-provided information.
*   **Code-based Privacy Policy Generators (CPPGs):** Tools that analyze an application's source code (e.g., Android/iOS) to identify privacy-related features and generate privacy descriptions or notices.
*   **Code-based IDE Plugins (CIDEPs):** Integrated into Integrated Development Environments, these tools provide privacy annotations for code during development to guide developers and ease notice creation.

### 2.2 Limitations of Existing Methods
While useful, existing tools have significant limitations, especially for complex mobile applications developed by multi-role teams:
*   **Lack of Collaboration Support:** Most tools are tailored for citizen developers or small teams, not facilitating the multi-role collaboration required for sophisticated apps. Legal teams often operate in silos.
*   **Disconnection from Development Lifecycle:** APPGs are often disconnected from the software development process, leading to inaccuracies. Small code changes require significant effort to update notices.
*   **Technical Complexity and Explainability:** CPPGs suffer from inherent complexity and low explainability, hindering adoption and effectiveness, and often fail to ensure compliance with high-level privacy regulations.
*   **Insufficient Knowledge Bridging:** CIDEPs can provide technical support but do not fundamentally improve developers' lack of privacy knowledge or address organizational environment issues.
*   **Inability to Track Changes Systematically:** None of the existing tools can systematically track privacy practice changes over time across thousands of modifications, leading to problematic privacy notices and increased risk of non-compliance.

## 3. Proposed Method

### 3.1 Main Contributions
The paper's key contributions are:
*   Systematically summarizing existing privacy notice generation tools for mobile applications.
*   Introducing the novel concept of PriBOM (Privacy Bills of Materials) and proposing a pre-fill mechanism tailored for mobile app development.
*   Conducting a comprehensive human evaluation to assess the perceived usefulness and gather insights on PriBOM.

### 3.2 Core Idea
The paper proposes PriBOM, a systematic software engineering approach inspired by Software Bills of Materials (SBOMs), designed as a transparent privacy information inventory. PriBOM is a table-like structure indexed by UI widgets, acting as a central platform for collaborative privacy notice generation. UI widgets are chosen as the pivot point due to their dual role as visual elements and key components in functionality and data handling, facilitating communication across diverse roles (front-end/back-end developers, UI designers, legal teams).

PriBOM comprises four main sections:
*   **UI Widget Identifier:** Documents unique IDs, types, names, and source references for each UI component, providing a common reference point.
*   **Codebase and Permission:** Details events, handlers, Android API levels, required permissions, method locations, and associated data types, linking UI interactions to backend privacy practices.
*   **Third-Party Library (TPL):** Records information about TPLs involved with a widget, including name, current version, latest version, and publish dates, crucial for managing TPL-related privacy risks.
*   **Privacy Notice Disclosure:** Links the widget's data practices to corresponding sections in the app's privacy policy and privacy label declarations, ensuring alignment between technical implementation and public disclosures.

The paper also presents a pre-fill mechanism for PriBOM using static analysis techniques (to extract widget details, callback methods, construct call graphs, identify permissions, and map to data types) and privacy notice analysis techniques (to segment privacy policies and process privacy label declarations).

### 3.3 Novelty
The novelty of PriBOM lies in its systematic, collaborative, and UI-centric approach to privacy information management, addressing limitations of existing tools:
*   **Collaborative Multi-Role Platform:** Unlike single-user or technically-focused tools, PriBOM is designed as a communication platform that brings all development roles (technical and non-technical) onto the same page regarding privacy, fostering a shared understanding and accountability.
*   **UI-Indexed Transparency:** By indexing privacy information by UI widgets, PriBOM provides an intuitive and accessible entry point for understanding data practices, even for non-technical stakeholders, directly addressing the opacity challenge. This bridges the gap between user interaction and backend code.
*   **Enhanced Traceability and Trackability:** PriBOM uniquely connects UI components, underlying code practices, and privacy notices, enabling developers to trace privacy issues back to their source and track the impact of code changes on privacy disclosures. This directly contributes to better maintenance and compliance.
*   **Systematic Inventory for Evolving Regulations:** Inspired by SBOMs, PriBOM serves as a structured, evolving inventory that can adapt to changing privacy regulations, providing a standardized mechanism for documenting privacy duties beyond fragmented existing documentation.
*   **Pre-fill Mechanism for Practicality:** The integration of static analysis and privacy notice analysis for pre-filling PriBOM demonstrates its practical feasibility, reducing the initial burden on developers while maintaining a collaborative core.

## 4. Experiment Results

### 4.1 Experimental Setup
*   **Study Type:** A human evaluation was conducted through an online survey.
*   **Participants:** 150 diverse participants with varying software development roles (junior/senior developers, project managers, UI designers, legal team members, others), team sizes, genders, and continents. Recruitment was done via Prolific.
*   **Questionnaire:** The survey consisted of 26 statements rated on a 5-point Likert scale (1=strongly disagree to 5=strongly agree), covering six perspectives: General Design, Widget Identifier, Codebase and Permission, TPL, Privacy Notice Disclosure, and Usability and Practicality. Four free-text open-ended questions were also included to gather deeper insights.
*   **Key Evaluation Metrics:** Average agreement scores for Likert scale statements and thematic analysis for open-ended responses.

### 4.2 Experimental Results
*   **Overall Positive Reception:** Participants generally showed strong agreement with the usefulness of PriBOM. For instance, the intuitiveness of PriBOM's design received 85.33% agreement. PriBOM's role in enhancing privacy-related communication was highly praised with 83.33% agreement, indicating its high usability.
*   **Design Perceptions:**
    *   **Widget Identification:** Perceived as precise and helpful for providing clear terminology (83.33% agreement).
    *   **Codebase & Permission:** The inclusion of 'Permission' and 'Data Type' fields was strongly supported (80.67% agreement), with 'Permission' transparency receiving the highest average score (4.09). Participants believed PriBOM helps create accurate privacy policies.
    *   **TPL Section:** Documenting TPL versions was seen as beneficial for identifying privacy practice discrepancies (74.67% agreement) and maintaining records of privacy-related updates.
    *   **Privacy Notice Disclosure:** Highly valued for its traceability (72%) and trackability (70.67%) in linking data practices to privacy policy descriptions and ensuring regulatory compliance.
*   **Usability and Practicality:** PriBOM was recognized for streamlining privacy notice generation (3.92 average score), improving alignment between disclosures and app behavior (4.02), enhancing transparency (4.03), and boosting privacy awareness (3.99).
*   **Differences Across Roles:**
    *   Legal teams showed significantly higher agreement on the necessity of API-level information for privacy management and PriBOM's impact on privacy awareness compared to UI designers.
    *   Project managers had higher agreement than UI designers on PriBOM's efficacy in aligning privacy disclosures with actual behaviors.
    *   Senior developers valued PriBOM more than UI designers for maintaining records of privacy-related updates.
    *   Legal teams rated PriBOM higher than senior developers for aiding in identifying user-consent-required data collection practices.
    *   Senior developers agreed more than junior developers that PriBOM could reduce effort in responding to privacy inquiries.
*   **Non-technical Role Perspectives:** Non-technical roles (legal team, UI designers, project managers) highlighted PriBOM's efficiency in streamlining workflows, speeding up compliance, and facilitating knowledge transfer in teams with high turnover. They also emphasized its benefits for traceability, root cause analysis, and fostering a common language for communication and responsibility assignment.

## 5. Limitations and Future Work

### 5.1 Limitations
*   **Static Analysis Dependence:** The quality of PriBOM's pre-fill mechanism is inherently dependent on the performance and coverage of the underlying static analysis tools.
*   **User Study Biases:** The human evaluation, being an online survey, might be susceptible to social desirability or acquiescence biases.
*   **Sample Skew:** The study sample was skewed towards participants from smaller development teams, which might affect the generalizability of some results, though it reflects a common industry demographic.
*   **UI-Centric Focus:** The current design is primarily UI-centric, meaning it may miss privacy-relevant data practices that are not directly triggered by or associated with UI interactions.
*   **Practicality Verification:** While promising, the real-world practicality of PriBOM in diverse organizational contexts still requires further verification.

### 5.2 Future Directions
*   **Non-UI Analysis Integration:** Future work will incorporate non-UI analyses, such as taint tracking and network monitoring, to enhance the completeness of PriBOM in capturing all sensitive behaviors and permissions.
*   **Usability Refinements:** Continuous improvement of PriBOM's usability and reduction of the learning curve are needed to ensure practical adoption, especially for experienced employees.
*   **Generalization to Other Software:** The concept of PriBOM can be extended to other software development contexts beyond mobile apps, potentially utilizing domain-specific privacy pivot points (e.g., sensor interfaces for IoT applications).
*   **Regulatory and Platform Integration:** Future enhancements include incorporating specific regulatory requirements (e.g., linking GDPR data rights) and app store guidelines (e.g., Google Play's Data Safety section fulfillment) to make PriBOM more comprehensive.
*   **Advanced Information Fields:** Potential inclusion of additional information like security levels for PII fields or direct links to TPL GitHub/web pages could further enhance its utility.
*   **ESG Reporting and Compliance:** PriBOM's structured approach could be extended to address data confidentiality challenges relevant to Environmental, Social, and Governance (ESG) reporting and compliance.