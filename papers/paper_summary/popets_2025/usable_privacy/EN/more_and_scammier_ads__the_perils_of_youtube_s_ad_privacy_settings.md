# Paper Info

## Title
More and Scammier Ads: The Perils of YouTube's Ad Privacy Settings

## Authors
Cat Mai, Bruno Coelho, Julia Kieserman, Lexie Matsumoto, Kyle Spinelli, Eric Yang, Athanasios Andreou, Rachel Greenstadt, Tobias Lauinger, Damon McCoy

## Affiliations
(New York University, United States), (SUNY Buffalo, United States)

# Brief Summary

## Highlight
This paper investigates the unintended consequences of enabling stronger ad privacy settings on YouTube. Through a series of large-scale, controlled experiments using emulated user accounts across five countries, the research measures the impact of disabling ad personalization on both the quantity and quality of pre-roll ads. The study's main contribution is quantifying a significant and previously unexamined trade-off between user privacy and online safety. The key findings reveal that users with the strictest privacy settings are shown **1.30 times more** ads and a **2.69 times higher** proportion of predatory or scam ads compared to users with default settings, highlighting a critical flaw in how privacy controls are implemented.

## Keywords
YouTube, Targeted Advertising, Privacy Settings, Predatory Ads, Algorithm Auditing

# Detailed Summary

## 1. Motivation

### 1.1 Background
Online platforms like YouTube offer users privacy controls to limit the use of their personal data for ad personalization. While platforms typically warn that this may lead to "less relevant" ads, the full scope of the trade-offs is not well understood. It is hypothesized that high-quality advertisers may rely on targeting mechanisms unavailable for privacy-conscious users, potentially exposing these users to lower-quality or even harmful advertising.

### 1.2 Problem Statement
The research addresses whether strengthening ad privacy settings on YouTube affects not only ad relevance but also ad safety. It investigates two primary research questions:
*   Does altering ad privacy settings change the **ad load**, i.e., the total number of ads a user is shown?
*   Does it impact the **predatory ad rate**, i.e., the proportion of scam and predatory ads served to the user?

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
Previous research in this area has focused on several related topics:
*   **Algorithm Audits:** Measuring personalization effects and disparities in content delivery systems like video recommendations and search results.
*   **Problematic Ads:** Investigating the prevalence of harmful ads (e.g., fraud, misinformation, malware) and their distribution across different user demographics.
*   **Privacy vs. Utility:** Analyzing the trade-off where more precise ad targeting (higher utility for advertisers and users) comes at the cost of user privacy.

### 2.2 Limitations of Existing Methods
Existing literature primarily frames the ad personalization debate as a trade-off between privacy and utility (ad relevance). There is a lack of research measuring the direct impact of user-selected privacy settings on exposure to dangerous or predatory content. No prior work has systematically quantified a potential trade-off between privacy and ad safety.

## 3. Proposed Method

### 3.1 Main Contributions
The paper proposes a robust experimental methodology to isolate and measure the causal effects of YouTube's ad privacy settings on both the quantity and the predatory nature of ads. This approach provides empirical evidence of an unforeseen risk associated with enabling privacy-enhancing features.

### 3.2 Core Idea
The core of the methodology is a controlled experiment using "sock puppet" accounts. The setup involves:
*   **Parallel Emulation:** Three browser instances run simultaneously on a virtual machine, each logged into a Google account with a different privacy configuration (default, personalization on/activity off, personalization off).
*   **Controlled Variables:** All three accounts watch the exact same sequence of 400 videos in parallel, controlling for confounding factors like time of day, user location, and video content.
*   **Diverse Conditions:** The experiment was conducted across five countries (Australia, Canada, Ireland, UK, US) and five distinct video categories (Conspiracy, Popular, News, Kids, Science).
*   **Manual Annotation:** All collected pre-roll ads were manually analyzed and labeled as either predatory or non-predatory based on a detailed codebook and inter-rater agreement checks.

### 3.3 Novelty
The innovation of this work lies in its rigorous experimental design, which successfully isolates the effect of privacy settings. It is the first study to empirically demonstrate and quantify that choosing stronger privacy controls can lead to increased exposure to both a higher volume of ads and a higher proportion of dangerous, predatory advertising, thus identifying a new dimension in the privacy debate: privacy versus safety.

## 4. Experiment Results

### 4.1 Experimental Setup
*   **Dataset:** The primary dataset consists of 38,851 ad impressions from 450 watch sequences, resulting in 10,628 unique pre-roll ads. Of these, 602 unique ads (2,610 impressions) were labeled as predatory.
*   **Baseline:** The default privacy setting (ad personalization on, activity history on) served as the baseline for comparison against two stronger privacy settings.
*   **Metrics:** The key evaluation metrics were **Ad Load** (the average number of pre-roll ads per video watched) and **Predatory Ad Rate** (the percentage of ads classified as predatory).

### 4.2 Experimental Results
*   **Increased Ad Load:** Enabling stronger privacy settings resulted in a statistically significant increase in the number of ads shown. Disabling ad personalization led to an average of **1.30 times more** pre-roll ads compared to the default setting. This effect was consistent across all tested countries and video categories.
*   **Increased Predatory Ad Rate:** More alarmingly, stronger privacy settings led to a dramatic increase in exposure to harmful ads. The proportion of predatory ads rose from **2.5%** in the default setting to **8.7%** when ad personalization was disabled—a **2.69-fold increase**.
*   **Role of Ad Delivery System:** Analysis of Google's ad targeting explanations revealed that when personalization was off, ads were not explicitly targeted based on the video being watched. However, the predatory ad rate still varied significantly by video category. This suggests that YouTube's ad delivery optimization algorithm—not the advertisers themselves—is a key factor in routing more predatory ads to privacy-conscious users based on video context.

## 5. Limitations and Future Work

### 5.1 Limitations
*   The main experiments used a single, fixed persona (34-year-old male), which may not generalize to all demographics, although a smaller validation experiment with a female persona confirmed the main trends.
*   The definition and labeling of "predatory" ads are inherently subjective, though the study used a conservative approach and cross-validation to ensure reliability.
*   The study captures a snapshot in time and does not measure the long-term effects of an extended activity history on ad delivery.
*   The findings are specific to YouTube's pre-roll ads and may not apply to other platforms or ad formats.

### 5.2 Future Directions
*   Extend the research to other platforms (e.g., Facebook, TikTok) and different types of ad systems.
*   Investigate the impact of other user demographics (e.g., age, location) and long-term user history on ad quality.
*   Examine how ad platforms can implement privacy controls more safely, without inadvertently increasing users' exposure to harmful content.
*   Further probe the incompleteness of ad explanations, which may have regulatory implications under laws like the EU's Digital Services Act.