# Paper Info

## Title
Misalignments and Demographic Differences in Expected and Actual Privacy Settings on Facebook

## Authors
Byron M. Lowens, Sean Scarnecchia, Jane Im, Tanisha Afnan, Annie Chen, Yixin Zou, Florian Schaub

## Affiliations
(University of Michigan, USA), (Max Planck Institute for Security and Privacy, Germany)

# Brief Summary

## Highlight
This paper investigates the persistent disconnect between what Facebook users expect their privacy settings to be and what they actually are. Using a custom browser extension to collect real-time data from 195 users' accounts, the study reveals that such misalignments are universal, with 100% of participants having at least one mismatch. Users overwhelmingly and incorrectly believed their settings were more restrictive than they actually were, especially regarding ad targeting, where the average user was targeted by 441 companies. This innovative method provides high ecological validity compared to previous survey-based work. The findings demonstrate that despite years of public scrutiny and platform updates, a concerning gap remains, and becoming aware of this gap significantly erodes users' trust in Facebook.

## Keywords
Privacy, Social Media, User Expectations, Demographics, Facebook

# Detailed Summary

## 1. Motivation

### 1.1 Background
Despite claims by social media companies to prioritize user privacy and control, platforms like Facebook have faced intense public and regulatory scrutiny for their data practices. In response, platforms have introduced numerous privacy settings. However, the effectiveness of this "notice and choice" model is questionable, as many users remain unaware of their actual data exposure and struggle to understand the complex ways their information is used, particularly for targeted advertising.

### 1.2 Problem Statement
The research addresses the gap between users' perceptions and reality regarding their data privacy on Facebook. The study is guided by three main research questions:
*   **RQ1:** To what extent are users' expected privacy settings aligned with their actual settings?
*   **RQ2:** Do demographic factors (e.g., age, gender, ethnicity) correlate with these expectation-setting misalignments?
*   **RQ3:** How concerned are users about these misalignments, and how does awareness impact their trust in Facebook?

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
*   Previous research has explored the "privacy paradox," where users' stated privacy concerns do not align with their online behaviors.
*   Studies have differentiated between interpersonal privacy (controlling visibility to other users) and institutional privacy (managing data use by the platform and third parties).
*   A small number of older studies from the early 2010s investigated mismatches between user expectations and settings on Facebook, finding that users often exposed more information than intended.

### 2.2 Limitations of Existing Methods
*   Much of the closely related research is over a decade old, and Facebook's platform, user base, and privacy controls have changed dramatically since then.
*   Many previous studies relied on self-reported data, hypothetical scenarios, or less diverse samples (e.g., college students), which limits their real-world applicability.
*   Prior work often focused narrowly on interpersonal privacy settings, with less attention paid to the increasingly complex institutional privacy and advertising settings.

## 3. Proposed Method

### 3.1 Main Contributions
The paper provides a comprehensive and contemporary analysis of Facebook privacy setting misalignments through a novel mixed-methods study. Its key contributions include:
*   Empirically demonstrating that substantial mismatches between expected and actual settings are a universal problem among users.
*   Quantifying the extent to which users underestimate their data exposure, particularly revealing the vast scale of ad targeting (e.g., an average of 474 ad topics per user).
*   Providing exploratory evidence that demographic factors like age, gender, and race may correlate with the likelihood of having mismatched settings.
*   Showing that raising user awareness of their actual settings significantly decreases their trust in the platform.

### 3.2 Core Idea
The study's methodology combines a custom browser extension with an online survey involving 195 U.S. Facebook users.
*   **Data Collection:** Participants installed a browser extension that, with their consent, automatically extracted the current values for 18 specific privacy settings across general, timeline, and ad categories, as well as ad profile data (number of ad topics and companies).
*   **Survey Integration:** The collected data was integrated in real-time into an online survey. For each of the 18 settings, a participant was first asked what they *expected* the setting to be. Immediately after, they were shown their *actual* setting and asked to rate their level of concern.
*   **Pre/Post Analysis:** Trust and privacy concern metrics were collected at both the beginning and end of the survey to measure the impact of the intervention.

### 3.3 Novelty
The method is innovative in several ways:
*   **High Ecological Validity:** Unlike survey-only studies, the use of a browser extension to collect *actual* setting data provides a highly accurate and realistic measurement of users' data exposure.
*   **Contemporary Assessment:** The research offers a much-needed update on this issue, reflecting Facebook's current interface and the modern privacy landscape post-Cambridge Analytica.
*   **Comprehensive Scope:** The study analyzes a broader range of 18 settings, covering both interpersonal visibility and institutional advertising controls, offering a more holistic view of user privacy.
*   **Diverse Sample:** By recruiting a more demographically diverse sample, the study enables an exploratory analysis of how mismatches may disproportionately affect different user groups.

## 4. Experiment Results

### 4.1 Experimental Setup
*   **Participants:** Data was collected from 195 demographically diverse U.S. Facebook users recruited through the Prolific platform.
*   **Data:** The dataset included participants' expected and actual values for 18 Facebook settings, their concern ratings, pre- and post-study trust levels, and demographic information.
*   **Analysis:** The study used descriptive statistics to quantify mismatches, regression models to explore correlations with demographic factors, and Wilcoxon Signed-Rank tests to assess changes in trust and concern.

### 4.2 Experimental Results
*   **Mismatches are Pervasive (RQ1):** Every single participant (100%) had at least one mismatch between their expected and actual settings, with an average of 5.74 mismatches out of 18. In most cases, users incorrectly believed their settings were more private than they actually were. The number of ad companies (mean: 441) and ad topics (mean: 474) assigned to users was significantly higher than they expected.
*   **Demographic Differences Emerge (RQ2):** The exploratory analysis indicated that certain demographic groups may be more prone to mismatches. Older participants (Gen X and Baby Boomers), men, Republicans, and participants identifying as Asian, Mixed-Race, or Hispanic were more likely to have mismatches on certain settings.
*   **Awareness Erodes Trust (RQ3):** While participants expressed only moderate concern about individual settings, the overall experience of seeing their actual data led to a statistically significant decline in their trust in Facebook. Their concerns about interpersonal privacy also significantly increased after completing the study.

## 5. Limitations and Future Work

### 5.1 Limitations
*   **Selection Bias:** The study required participants to install a browser extension, which may have attracted a more technically savvy or less risk-averse group of users.
*   **Sample Representativeness:** The sample was recruited from a single platform (Prolific), limited to the U.S., and was more educated on average than the general Facebook user base.
*   **Statistical Power:** The sample size limited the statistical power for the regression analyses, meaning the findings on demographic differences are exploratory and require further validation.
*   **Static View:** The study captured a single point in time and does not reveal how users' expectations or settings evolve.

### 5.2 Future Directions
*   **Confirm Demographic Findings:** Further research with larger, more diverse samples is needed to confirm and understand the root causes of the demographic differences in privacy setting mismatches.
*   **Improve Privacy Design:** The findings call for platforms to design more effective and usable privacy controls that are embedded within the user experience rather than hidden in complex menus.
*   **Enhance Digital Literacy:** There is a need for better public education to help users develop accurate mental models of how platforms use their data and to empower them with online self-defense skills.
*   **Strengthen Public Policy:** The paper suggests that the "notice and choice" framework is failing. It advocates for policy interventions such as mandating privacy-friendly defaults, setting meaningful limits on data processing, and exploring new regulatory models like imposing a fiduciary duty on platforms to act in their users' best interests.