# Paper Info

## Title
Privacy Bills of Materials (PriBOM): A Transparent Privacy Information Inventory for Collaborative Privacy Notice Generation in Mobile App Development 

## Authors
Zhen Tao, Shidong Pan, Zhenchang Xing, Xiaoyu Sun, Omar Haggag, John Grundy, Jingjie Li, Liming Zhu

## Affiliations
(CSIRO’s Data61, Australia), (Australian National University, Australia), (Monash University, Australia), (University of Edinburgh, United Kingdom), (UNSW, Australia)

# Brief Summary

## Highlight
本研究针对移动应用开发中隐私通知（如隐私政策或标签）生成与维护的挑战，提出了PriBOM（Privacy Bills of Materials）这一系统性软件工程方法。PriBOM通过构建以UI组件为索引的隐私信息清单，整合开发团队不同角色的信息，以实现隐私信息的透明化、可追溯性和可跟踪性。该方法利用静态分析和隐私通知分析技术进行预填充，并通过包含150名参与者的人工评估，验证了其在增强隐私相关沟通方面的有效性，获得了83.33%的认同，表明PriBOM是移动应用DevOps中隐私支持的重要解决方案。

## Keywords
[Transparency, Usable Privacy, Mobile Applications, Privacy Policy, Privacy Paradox]

# Detailed Summary

## 1. Motivation

### 1.1 Background
*   隐私法规（如GDPR、CCPA、APP）要求开发者为移动应用程序提供真实、全面的隐私通知（如隐私政策或标签），以告知用户其应用程序的隐私实践。
*   当前主流应用商店（如Google Play的Data Safety Sections和Apple App Store的Apple Privacy Labels）也要求应用开发者以隐私标签的形式，提醒用户潜在的隐私数据处理行为。

### 1.2 Problem Statement
*   开发者普遍缺乏隐私法规和法律知识，难以准确理解和撰写符合要求的隐私通知。
*   对于功能复杂、由多角色团队协作开发的移动应用而言，维护隐私通知的准确性和及时性极具挑战性。
*   现有隐私通知生成工具（如在线自动化隐私政策生成器、基于代码的隐私政策生成器、基于代码的IDE插件）通常不适用于复杂应用和大型团队协作场景。
*   开发团队面临隐私知识缺失、技术知识有限（如第三方库数据处理不透明）和不友好的组织环境（如对隐私因素态度消极，缺乏团队支持）等挑战，导致现有隐私通知常常与实际数据实践不符，损害用户信任并可能违反法规。

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
*   **在线自动化隐私政策生成器（APPGs）**: 通常基于问卷调查，依赖开发者提供信息生成隐私政策。
*   **基于代码的隐私政策生成器（CPPGs）**: 通过分析应用程序源代码中的隐私相关功能来生成隐私描述或通知。
*   **基于代码的IDE插件（CIDEPs）**: 集成到集成开发环境（IDE）中，在开发过程中为开发者提供代码隐私注释。

### 2.2 Limitations of Existing Methods
*   APPGs的生成过程与软件开发脱节，质量受开发者设计缺陷和不准确信息的影响。
*   CPPGs面临固有的复杂性和可解释性低的问题，难以确保符合高层级的隐私法规。
*   APPGs、CPPGs和CIDEPs大多为个人开发者或小型团队设计，难以应用于功能复杂、多角色协作的移动应用程序开发场景。
*   现有工具无法解决开发团队面临的隐私知识缺失、技术知识有限和不友好的组织环境等根本性挑战。

## 3. Proposed Method

### 3.1 Main Contributions
*   首次系统性总结了现有的隐私通知生成工具，并指出了其局限性。
*   引入了PriBOM（Privacy Bills of Materials）概念，并提出了一种针对移动应用开发的预填充实现方案。
*   通过人工评估，全面评估了PriBOM的实用性，验证了其在增强隐私相关沟通、促进协作方面的有效性。

### 3.2 Core Idea
*   **PriBOM核心理念**: 受软件物料清单（SBOM）启发，PriBOM是一个系统性的、以UI组件为索引的隐私信息清单，旨在透明化地记录软件隐私信息，并促进多角色开发团队在隐私通知生成上的协作。
*   **PriBOM结构**: PriBOM以表格形式呈现，索引字段为UI组件（Widget），记录以下信息：
    1.  **UI标识符**: 包括Widget ID、Widget Type、Widget Name、Widget Src，作为隐私沟通的枢纽。
    2.  **代码库与权限**: 记录与UI组件相关的事件、处理程序、Android API级别、所需权限、数据类型及权限访问路径。
    3.  **第三方库（TPL）**: 记录与UI组件相关的TPL名称、版本、最新版本及其发布日期。
    4.  **隐私通知披露**: 关联应用程序隐私政策中的相关描述和隐私标签（如Google Play的Data Safety Sections）中的声明。
*   **预填充机制**: 结合静态分析技术（用于提取UI组件、回调方法、调用图、Android权限和权限-数据映射）和隐私通知分析技术（用于隐私政策分段和隐私标签处理）自动填充PriBOM。

### 3.3 Novelty
*   首次将物料清单（BOM）概念应用于隐私领域，提出了PriBOM，作为一种系统化、协作式的隐私信息清单，链接了前端UI、后端代码隐私实践与用户隐私通知。
*   PriBOM以UI组件为中心，作为协调不同开发角色（如前端、后端开发者、UI设计师、法务团队）进行隐私相关沟通和协作的“枢纽”，有效弥补了现有工具在多角色协作场景中的不足。
*   通过提供隐私信息的透明化、可追溯性和可跟踪性，PriBOM能够从根本上解决开发者在生成和维护准确、合规隐私通知时面临的挑战，如隐私知识缺失、技术理解不足以及组织环境不友好的问题。

## 4. Experiment Results

### 4.1 Experimental Setup
*   **实验方法**: 采用在线问卷调查形式进行人工评估。
*   **参与者**: 150名来自不同背景（初级开发者、高级开发者、项目经理、UI设计师、法务团队及其他角色）、团队规模和地域的软件开发人员，通过Prolific平台招募。
*   **问卷设计**: 包含26个基于5点Likert量表的陈述题（涵盖PriBOM的通用设计、各部分设计及可用性/实用性）和4个开放式文本问题，旨在评估PriBOM的感知有用性并收集改进意见。
*   **评价指标**: Likert量表评分的平均分和分布、开放式问题的定性主题分析。

### 4.2 Experimental Results
*   **总体认同度高**: 参与者对PriBOM的通用设计、内容理解和信息相关性普遍持积极态度，设计直观性获得85.33%的认同，内容理解度为72%，信息相关性为78.76%。
*   **增强沟通与协作**: 83.33%的参与者认为PriBOM是不同开发角色之间进行高效隐私相关沟通的实用解决方案。
*   **各部分设计认可**:
    *   UI标识符部分在提供清晰通用术语方面获得83.33%的认同。
    *   代码库与权限部分中包含权限和数据类型字段的必要性获得80.67%的认同，其中权限信息对提升数据透明度的必要性得分最高（4.09）。
    *   第三方库部分在帮助识别不同版本间隐私实践差异方面获得74.67%的认同。
    *   隐私通知披露部分在可追溯性（72%）和可跟踪性（70.67%）方面获得积极反馈。
*   **角色视角差异**: 不同角色对PriBOM的价值感知存在差异，例如，法务团队比UI设计师更看重API级别信息，高级开发者比初级开发者更认同PriBOM在减少隐私查询响应工作量方面的作用。非技术角色（法务团队、UI设计师、项目经理）尤其强调PriBOM在提高效率、实现可追溯性和促进沟通方面的益处。
*   **实践挑战与改进建议**: 参与者提及了实际采纳PriBOM可能面临的挑战，如初始设置复杂性、与现有系统集成问题以及大型团队维护的工作量，并提出了增加PII字段的安全级别、包含TPL项目的GitHub/网页链接等改进建议。

## 5. Limitations and Future Work

### 5.1 Limitations
*   **预填充质量依赖**: PriBOM的预填充质量受限于所使用的静态分析工具的性能。
*   **用户研究偏差**: 用户研究采用问卷调查形式，可能存在社会期望偏差或默认同意偏差，通过深入访谈可进一步改进。
*   **样本偏向性**: 参与者样本可能偏向于小型开发团队，这可能影响结果的普遍性（尽管反映了小型团队占比较大的现实）。
*   **UI中心设计**: 当前设计以UI为中心，可能无法捕获非UI触发的权限使用。

### 5.2 Future Directions
*   **集成非UI分析**: 未来的工作将整合非UI分析方法，以增强PriBOM的完整性，捕获所有敏感行为。
*   **通用化PriBOM概念**: 探索将PriBOM概念推广到任意软件系统，解决异构数据流和软件多样性带来的挑战，例如，利用领域特定隐私枢纽点（如IoT应用的传感器接口）作为隐私相关信息的锚点。
*   **可用性与适应性改进**: 继续改进PriBOM的可用性，降低学习曲线，并根据不同角色的实际需求进行调整和优化。
*   **扩展到ESG合规**: 将PriBOM的结构化方法扩展到隐私语境之外，例如解决ESG（环境、社会和治理）报告和合规性中数据机密性挑战。