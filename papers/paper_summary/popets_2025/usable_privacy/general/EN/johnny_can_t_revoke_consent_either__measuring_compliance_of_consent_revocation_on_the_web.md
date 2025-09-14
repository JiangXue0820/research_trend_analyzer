# Paper Info

## Title
Johnny Can’t Revoke Consent Either: Measuring Compliance of Consent Revocation on the Web

## Authors
Gayatri Priyadarsini Kancherla, Nataliia Bielova, Cristiana Santos, Abhishek Bichhawat

## Affiliations
(Indian Institute of Technology Gandhinagar, India), (Inria Centre at University Côte d’Azur, France), (Utrecht University, Netherlands)

# Brief Summary

## Highlight
This paper presents the first large-scale study on the compliance of consent revocation mechanisms on the web, as required by the EU's GDPR. The authors developed a semi-automated framework to analyze the user interfaces, cookie management, and backend consent communication on top-ranked websites, including those using major Consent Management Platforms (CMPs) like IAB TCF and OneTrust. The research reveals widespread non-compliance, finding that many websites make revocation significantly harder than acceptance (20.5%), fail to delete tracking cookies after revocation (57.5%), and incorrectly store a positive consent decision. A critical finding is that 74.2% of analyzed websites using the IAB framework do not inform third parties when a user revokes consent, leading to continued and illegal data processing.

## Keywords
[Consent Revocation, GDPR, Web Privacy, Compliance, Cookies]

# Detailed Summary

## 1. Motivation

### 1.1 Background
The EU's General Data Protection Regulation (GDPR) and ePrivacy Directive mandate that user consent for data processing and tracking must be freely given, informed, and easily revocable. While numerous studies have analyzed how websites obtain consent through banners, the critical aspect of consent revocation—the user's right to withdraw their permission at any time—has been largely overlooked by researchers and regulators. This right is fundamental, and its improper implementation can lead to illegal data processing.

### 1.2 Problem Statement
The paper addresses the gap in understanding how consent revocation is implemented and whether current practices comply with legal requirements. The core research questions are:
*   Are the user interfaces for revoking consent compliant with EU law in terms of ease and accessibility?
*   Do websites stop data processing by deleting advertising and analytics (AA) cookies after a user revokes consent?
*   Is the revoked consent choice correctly and consistently stored across different browser storage mechanisms and APIs provided by CMPs?
*   Are third parties, who were initially notified of user consent, also informed when that consent is revoked?

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
Prior research in this area has focused on:
*   **Consent Banner Compliance:** Studies have analyzed the design of consent banners, the presence of "reject" buttons, and the use of dark patterns to influence user choice.
*   **IAB TCF Analysis:** Several works have examined the implementation of the IAB Europe Transparency and Consent Framework (TCF), focusing on how consent choices are obtained and stored.
*   **Opt-Out Mechanisms:** Research has also explored the implementation of "opt-out" links under U.S. regulations like the CCPA/CPRA, but this is legally distinct from the GDPR's right to revoke prior consent.

### 2.2 Limitations of Existing Methods
The primary limitation of existing work is its narrow focus on the initial consent-gathering process. No previous study has systematically measured the compliance of consent *revocation* on the web under the GDPR framework. Consequently, there is no comprehensive understanding of whether websites correctly implement revocation interfaces, stop subsequent data processing, and properly communicate the updated consent status to third parties.

## 3. Proposed Method

### 3.1 Main Contributions
The paper's main contributions are:
*   A detailed legal analysis of GDPR requirements for consent revocation, distilled into six operational criteria for auditing compliance.
*   A novel, semi-automated methodology to audit revocation interfaces, cookie behavior, consent storage, and communication to third parties.
*   The first large-scale empirical study measuring consent revocation compliance on top websites.
*   A specific analysis of websites using IAB TCF and OneTrust CMPs, revealing systemic failures in storing and communicating revoked consent.

### 3.2 Core Idea
The methodology is based on a multi-stage, semi-automated data collection process using a Selenium-instrumented browser to simulate user interaction.
1.  **Interface Analysis:** The crawler visits websites and follows a manual process to find and interact with revocation options. It collects screenshots and records the number of steps required, comparing the effort to revoke with the effort to accept.
2.  **Cookie Analysis:** At each stage (initial visit, after acceptance, after revocation, after rejection), the framework collects all browser cookies. These are classified to identify advertising and analytics (AA) cookies that require consent, measuring whether they are deleted upon revocation.
3.  **CMP Analysis:** For websites using IAB TCF or OneTrust, the framework injects scripts to query consent APIs (`__tcfapi`, `OneTrustActiveGroups`) and inspects browser storage (cookies, localStorage) and network traffic (HTTP requests/responses) to track how consent strings are stored and shared with third parties.

### 3.3 Novelty
This work is novel as it provides the first end-to-end analysis of consent revocation. Its innovations include:
*   **Holistic Framework:** It uniquely combines legal analysis with technical measurements across the user interface, browser storage, and network communication layers.
*   **Beyond Initial Consent:** It moves beyond the well-studied topic of consent acquisition to the unexamined area of revocation.
*   **Advanced Network Analysis:** It improves upon prior methods by analyzing not just specific URL parameters but also POST request data and HTTP responses to detect how consent strings are shared, revealing inconsistencies and failures to notify third parties.

## 4. Experiment Results

### 4.1 Experimental Setup
*   **Datasets:** The study used the Tranco list to select websites. For interface and cookie analysis, 158 reachable domains from the top 200 were analyzed. For the deeper technical analysis of CMPs, a set of 281 websites from the top 5,000 known to use IAB TCF or OneTrust was used.
*   **Baseline Methods:** As the first study of its kind, there are no direct baseline methods. Compliance was evaluated against the six legal requirements derived from GDPR.
*   **Evaluation Metrics:** Key metrics included the prevalence of non-compliant interface designs, the number and change in AA cookies after revocation, the frequency of incorrect (positive) consent storage, and the percentage of third parties not informed of revocation.

### 4.2 Experimental Results
The study uncovered significant and widespread non-compliance:
*   **Interface Violations:** 19.87% of websites offered revocation through a different, more complex interface (e.g., browser settings), 20.5% required more steps to revoke than to accept, and 2.48% provided no revocation option at all.
*   **Failure to Stop Processing:** 57.5% of websites failed to delete AA cookies after consent was revoked, indicating that data processing likely continued illegally.
*   **Incorrect Consent Storage:** On sites with CMPs, many stored positive consent after revocation (16.17% for TCF `__tcfapi` and 14.47% for OneTrust `OTAG`). The study also found inconsistencies between consent values stored in cookies and those provided by APIs.
*   **Failure to Communicate Revocation:** The most striking finding was that on 74.2% of websites using the IAB TCF, third parties (like `doubleclick.net` and `criteo.com`) that received a positive consent signal were not informed via HTTP requests when the user later revoked it.

## 5. Limitations and Future Work

### 5.1 Limitations
The authors acknowledge several limitations:
*   The accuracy of classifying cookies as "Advertising" or "Analytics" depends on the CookieBlock tool, which may have errors.
*   The semi-automated approach for interface analysis is not scalable and may miss some network logs during navigation.
*   The framework cannot fully capture all API access, particularly through non-standard event listeners used to communicate consent changes.
*   The analysis of OneTrust is constrained by its proprietary and undocumented format for consent strings.

### 5.2 Future Work
The paper proposes several directions for future work and provides recommendations for regulators:
*   **Standardization:** Regulators should unify requirements for revocation interfaces (e.g., location, wording) and standardize technical mechanisms for consent storage and communication to prevent inconsistencies.
*   **Event Listeners:** Standard-setting bodies like IAB Europe should standardize the implementation of event listeners so third parties have a reliable way to be notified of consent changes.
*   **Automation:** Future research could focus on developing fully automated tools to detect and interact with the highly heterogeneous revocation interfaces found on the web.
*   **Accountability:** Regulators should clarify how websites must inform third parties of revocation to ensure accountability throughout the ad-tech ecosystem.