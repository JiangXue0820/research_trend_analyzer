# Paper Info

## Title
Privacy Settings of Third-Party Libraries in Android Apps: A Study of Facebook SDKs

## Authors
David Rodriguez, Joseph A. Calandrino, Jose M. Del Alamo, Norman Sadeh

## Affiliations
(ETSI Telecomunicación, Universidad Politécnica de Madrid, Spain), (Washington, D.C., USA), (Carnegie Mellon University, USA)

# Brief Summary

## Highlight
This paper investigates how developers configure privacy-related settings in widely used Facebook SDKs for Android, addressing the problem of privacy risks stemming from third-party libraries (TPLs). The authors employ a novel multi-method approach combining static and dynamic analysis on over 6,000 popular apps to get a comprehensive view of runtime configurations, which static analysis alone cannot provide. The key contribution is revealing widespread inconsistencies between app practices and their privacy disclosures, often caused by developers retaining default SDK settings that favor data collection. For instance, 28.75% of apps with Advertising ID collection enabled failed to disclose this practice in their privacy labels, demonstrating a significant compliance gap that this method effectively uncovers.

## Keywords
Privacy Settings, Third-Party Libraries, Dynamic Analysis, Android Applications, Compliance Analysis

# Detailed Summary

## 1. Motivation

### 1.1 Background
Mobile app developers extensively use third-party libraries (TPLs) and Software Development Kits (SDKs) to accelerate development and add functionality like advertising and social media integration. However, these SDKs, often provided for free, frequently collect user data, introducing significant privacy risks. This data collection can lead to non-compliance with regulations like GDPR and CCPA, placing both users and developers at risk.

### 1.2 Problem Statement
There is a poor understanding of how developers interact with the configurable privacy settings offered by TPLs. Prior research suggests developers are often reluctant to change default settings, which typically favor data collection over privacy. This can create a mismatch between an app's actual data practices and what is disclosed in its privacy policy and labels. The paper aims to address this gap by investigating the specific configuration choices developers make when integrating the popular Facebook Android SDK and Audience Network SDK.

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
Previous research has identified privacy risks in TPLs and employed various techniques for analysis.
*   **TPL Detection:** Tools like LibScout are used to identify the presence and version of libraries within Android apps, even with code obfuscation.
*   **Static Analysis:** Tools like FlowDroid examine app code without execution to map potential data flows and identify privacy leaks.
*   **Dynamic Analysis:** This involves running the app to observe its actual behavior. Common techniques include network traffic interception (e.g., using Mitmproxy) to analyze transmitted data and dynamic instrumentation (e.g., using Frida) to trace API calls and attribute behavior to specific libraries.

### 2.2 Limitations of Existing Methods
Existing methods have key limitations in the context of SDK privacy settings.
*   Studies often focus on identifying data leaks without investigating the role of configurable SDK settings as a root cause.
*   Research that has examined privacy settings has typically relied solely on static analysis of the Android Manifest file. This provides an incomplete picture, as settings can also be modified in the app's code at runtime or through external developer platforms, which static analysis cannot detect.

## 3. Proposed Method

### 3.1 Main Contributions
The paper makes four key contributions:
1.  **Compilation of SDK Privacy Settings:** It documents the privacy-related settings, defaults, and their impact for the Facebook Android SDK and Audience Network SDK.
2.  **Static Analysis:** It assesses the integration of Facebook SDKs in apps and analyzes developer choices for settings that can be configured in the Manifest file.
3.  **Dynamic Analysis:** It introduces a method using runtime instrumentation to validate SDK integration, determine the exact version, and accurately identify the final configuration of privacy settings, including those changed via code.
4.  **Compliance Analysis:** It compares the observed app practices (derived from SDK settings) with the disclosures made in the apps' privacy labels and policies to identify discrepancies.

### 3.2 Core Idea
The research is built on a multi-method analysis platform that provides a holistic view of developer practices.
*   **Static Phase:** It uses LibScout to detect the presence of Facebook SDKs and Apktool to parse the Android Manifest file to identify explicit configurations of settings like `AutoLogAppEvents` and `AdvertiserIDCollection`.
*   **Dynamic Phase:** On real devices, it uses the Frida toolkit to instrument running apps. This allows the system to hook into the SDKs' internal methods to read the real-time values of all privacy settings (via "getters") and log any changes made during execution (via "setters"). This phase also uses Mitmproxy to intercept network traffic, linking data transmissions to the Facebook SDKs by analyzing call stacks.
*   **Compliance Phase:** The data gathered from the static and dynamic phases, particularly regarding Advertising ID collection, is cross-referenced with the app's Google Play privacy label and an LLM-based analysis of its privacy policy to detect inconsistencies.

### 3.3 Novelty
The primary innovation is the synergistic use of static and dynamic analysis to achieve a more accurate and complete assessment of SDK privacy configurations. Unlike previous methods that relied only on static Manifest analysis, this approach captures runtime changes made through code or inferred changes made via the Meta Developers Platform. This provides a true picture of an app's behavior and reveals discrepancies between how a setting is declared and how it actually functions, offering deeper insights into compliance gaps.

## 4. Experiment Results

### 4.1 Experimental Setup
*   **Dataset:** The study analyzed 6,203 popular Android apps from the AndroZoo dataset, all with over one million downloads.
*   **Analysis Target:** The privacy-related settings of the Facebook Android SDK (Core module) and the Facebook Audience Network SDK.
*   **Metrics:** The evaluation measured the rate of SDK integration, the frequency of developers modifying default settings, the types of data transmitted by the SDKs, and the rate of non-compliance between observed behavior and privacy disclosures.

### 4.2 Experimental Results
*   **SDK Integration:** A majority of apps (53.68%) integrated at least one of the two Facebook SDKs.
*   **Settings Configuration:** Developers overwhelmingly retained the default, less privacy-friendly settings. For example, the `LimitEventAndDataUsage` setting, which restricts data use for ad targeting, was not enabled by any app. Only 6.79% of apps disabled the default-enabled `AdvertiserIDCollection`.
*   **Data Transfers:** The Facebook SDKs were a top source of personal data transmission, primarily sending the Advertising ID (AdID) and device model.
*   **Compliance Analysis:** There was a significant gap between practices and disclosures. 28.75% of the apps that had AdID collection enabled (either explicitly or by default) failed to declare this in their privacy labels. The study found that nearly 30% of cases where developers left the setting as default were potentially non-compliant, suggesting a lack of awareness of the SDK's behavior.

## 5. Limitations and Future Work

### 5.1 Limitations
*   **Construct Validity:** The app dataset from AndroZoo, while large, may not perfectly mirror the current distribution of apps on the Google Play Store.
*   **Internal Validity:** The dynamic analysis could potentially miss configuration changes that occur before the Frida instrumentation fully attaches, although this is mitigated by cross-checking with Manifest values and repeatedly querying settings. Code obfuscation also remains a challenge, though the tools used are robust.
*   **External Validity:** The findings are specific to two Facebook SDKs on the Android platform. They may not be generalizable to other SDKs, apps, or the iOS ecosystem.

### 5.2 Future Directions
The paper suggests several avenues for future work:
*   Expanding the analysis to include a wider range of popular SDKs to provide a more comprehensive overview of the mobile ecosystem.
*   Analyzing a more diverse set of Android apps, not just the most popular ones, to understand practices across different app categories and developer sizes.
*   Empirically evaluating the effectiveness of proposed mitigation strategies, such as Apple's privacy manifests, in improving developer compliance and transparency.