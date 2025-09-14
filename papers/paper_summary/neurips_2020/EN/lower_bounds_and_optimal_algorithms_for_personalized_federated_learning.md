# Paper Info

## Title
Lower Bounds And Optimal Algorithms For Personalized Federated Learning

## Authors
['Filip Hanzely', 'Slavomír Hanzely', 'Samuel Horváth', 'Peter Richtarik']

## Affiliations
[('King Abdullah University of Science and Technology (KAUST)', 'Saudi Arabia')]

# Brief Summary

## Highlight
This paper establishes the first lower bounds for communication and local oracle complexity within a specific personalized federated learning (FL) optimization framework. It then introduces several provably optimal algorithms, including accelerated variants of FedProx and a variance-reduced version of FedAvg/Local SGD, that match these lower bounds across various scenarios. These contributions provide crucial theoretical justification for the use of local methods in FL with heterogeneous data, overcoming the previous limitation where optimality was only shown for homogeneous data. Extensive numerical experiments demonstrate the practical superiority of the proposed methods over existing baselines.

## Keywords
[Federated Learning, Personalization, Optimization, Lower Bounds, Optimal Algorithms]

# Detailed Summary

## 1. Motivation

### 1.1 Background
Federated Learning (FL) is a rapidly growing field focusing on training machine learning models on decentralized, heterogeneous data residing on many client devices. Unlike traditional distributed learning, FL faces unique challenges such as significant communication bottlenecks due to geographically dispersed clients and the inherent heterogeneity (non-IID) of local data. While standard FL aims for a single global model, many applications, like next-word prediction, benefit from personalized models, where a global model might not be ideal for individual clients whose data distributions differ significantly from the population average. This necessity has led to the development of personalized FL objectives. This work specifically focuses on a personalized FL formulation introduced by [19], which penalizes the dissimilarity between local models and their average, and has been shown to be related to local SGD and FedAvg.

### 1.2 Problem Statement
The paper addresses two main problems within the context of the personalized FL objective formulation (Eq. 2):
1.  **Lack of Theoretical Lower Bounds:** Before this work, there were no established lower complexity bounds for communication and local computation for this personalized FL formulation. This makes it difficult to assess the fundamental limits of any algorithm.
2.  **Absence of Provably Optimal Algorithms:** Consequently, there were no algorithms proven to be optimal in terms of communication or local computation for solving this personalized FL problem, especially when considering heterogeneous data. Existing local methods were only known to be optimal for homogeneous data settings.

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
Traditional FL aims to minimize a global average loss function (Eq. 1), leading to a single model for all clients. Various strategies have been explored for personalization in FL, including multi-task learning, transfer learning, variational inference, and mixing local and global models. The specific personalized FL formulation (Eq. 2), which introduces a regularization term penalizing local model deviation from the global average, was proposed in [19]. This formulation has been shown to connect local SGD and FedAvg. Existing algorithms like L2GD and L2SGD+ from [19] and variants of Accelerated Proximal Gradient Descent (APGD) from [50] have been applied to similar distributed optimization problems.

### 2.2 Limitations of Existing Methods
*   **Suboptimality in Personalized FL:** For the personalized FL objective (Eq. 2), existing methods had not been proven to be optimal in terms of communication or local computation complexity. Plain PGD/APGD methods, when directly applied, often yield suboptimal rates.
*   **Homogeneous Data Assumption for Optimality:** While local algorithms are widely used in practice for FL with heterogeneous data, their theoretical optimality was previously only established under the strong assumption that all client data are homogeneous (IID). This left a significant gap in the theoretical understanding and justification of common FL practices for non-IID data.
*   **Practicality of Proximal Oracles:** Some advanced methods rely on exact proximal oracle calls, which can be computationally expensive or impractical in real-world scenarios, especially when local objectives have a complex structure (e.g., finite-sum).

## 3. Proposed Method

### 3.1 Main Contributions
The paper makes the following key contributions:
*   It establishes the first comprehensive lower bounds for communication and local oracle complexity (proximal, gradient, and summand gradient) for the personalized FL formulation (Eq. 2) under L-smooth and µ-strongly convex local objectives.
*   It designs and analyzes several novel algorithms that are provably optimal, matching these established lower bounds in almost all relevant regimes.
*   It provides theoretical justification for the optimality of local algorithms when applied to FL problems with heterogeneous data, reinterpreting them as solvers for the personalized FL formulation (2).

### 3.2 Core Idea
The core ideas revolve around two main aspects:
*   **Lower Bound Derivations:** The authors derive lower bounds for communication and local oracle calls (proximal, gradient, summand gradient) by constructing worst-case functions. These derivations rely on a standard assumption that algorithm iterates lie within the span of previously observed oracle queries. The bounds show that communication complexity is at least $O(\sqrt{\min\{L, \lambda\}/\mu} \log(1/\epsilon))$ and local computation depends on the oracle type (e.g., $O(\sqrt{L/\mu} \log(1/\epsilon))$ for gradient calls).
*   **Optimal Algorithm Design:**
    *   **Accelerated Proximal Gradient Descent (APGD):** Two accelerated variants, APGD1 and APGD2, are adapted from [50]. APGD1 is optimal when $\lambda \le L$ (communication $O(\sqrt{\lambda/\mu})$), while APGD2 is optimal when $\lambda \ge L$ (communication $O(\sqrt{L/\mu})$).
    *   **Inexact APGD (IAPGD):** To overcome the impracticality of exact proximal operators, IAPGD is proposed, which uses local sub-solvers to approximate the proximal steps. AGD (for gradient oracle) and Katyusha (for finite-sum objectives with summand gradient oracle) are used as local solvers. This approach achieves optimal communication complexity ($O(\sqrt{\lambda/\mu} \log(1/\epsilon))$) and near-optimal local gradient complexity under certain conditions.
    *   **Accelerated L2SGD+ (AL2SGD+):** This is an accelerated, variance-reduced variant of L2SGD+ from [19]. It directly estimates the gradient of the global objective using non-uniform minibatch sampling. AL2SGD+ is designed to address drawbacks of IAPGD (e.g., extra log factors, boundedness assumptions, suboptimality for $\lambda > L$). It achieves optimal communication complexity $O(\sqrt{\min\{\tilde{L}, \lambda\}/\mu} \log(1/\epsilon))$ and optimal local summand gradient complexity $O(m + \sqrt{m(\tilde{L}+\lambda)/\mu} \log(1/\epsilon))$ when $\lambda \le \tilde{L}$.

### 3.3 Novelty
The primary novelty lies in:
*   **First Lower Bounds:** Providing the first theoretical lower bounds for the communication and local computation complexity of the personalized FL formulation (2). This sets a benchmark for all subsequent algorithm development in this domain.
*   **Provably Optimal Algorithms:** Developing a suite of algorithms (APGD1, APGD2, IAPGD with AGD/Katyusha, AL2SGD+) that are mathematically proven to match these new lower bounds, making them the first provably optimal methods for personalized FL.
*   **Theoretical Justification for Heterogeneous Data FL:** Crucially, the paper demonstrates the optimality of local algorithms for FL with *heterogeneous* data, by viewing them as solvers for the personalized FL objective. This is a significant theoretical advancement, as previous optimality results for local methods were largely restricted to homogeneous (IID) data settings. This directly justifies a widely used practical approach in FL.
*   **AL2SGD+ as a Robust Optimal Method:** AL2SGD+ represents a novel accelerated, variance-reduced approach that overcomes several practical and theoretical limitations of prior inexact methods, offering broader applicability and improved performance guarantees.

## 4. Experiment Results

### 4.1 Experimental Setup
The experiments are conducted to empirically validate the theoretical claims regarding communication and local computation complexities.
*   **Datasets:** LIBSVM datasets (e.g., madelon, a1a, mushrooms, duke) are used for logistic regression problems. Each client is assigned a random, mutually disjoint subset of the full dataset to simulate data heterogeneity.
*   **Baselines:** The proposed algorithms (IAPGD+Katyusha, AL2SGD+, APGD1, APGD2) are compared against L2SGD+ [19], which serves as a baseline for personalized FL.
*   **Evaluation Metrics:** The primary metrics are "Relative suboptimality" (how close the current solution is to the optimum) plotted against "Communication rounds" and "Gradients of local summands" (local computation).
*   **APGD Variants:** A synthetic quadratic objective with varying $\lambda$ and fixed $L, \mu$ is used to compare APGD1 and APGD2.

### 4.2 Experimental Results
*   **Comparison of IAPGD+Katyusha, AL2SGD+, and L2SGD+:**
    *   **Communication Complexity:** Both AL2SGD+ and IAPGD+Katyusha significantly outperform the baseline L2SGD+ in terms of communication rounds required to reach a certain suboptimality level. This confirms the theoretical prediction of their superior communication efficiency.
    *   **Local Computation Complexity:** AL2SGD+ demonstrates the best performance in terms of local computation (gradients of local summands). Interestingly, IAPGD+Katyusha falls behind L2SGD+, which the authors attribute to large constant and log factors present in its theoretical local complexity bounds.
*   **Effect of $\lambda$ on APGD1 and APGD2:**
    *   Experiments on a quadratic objective confirm that APGD1 is favorable when $\lambda \le L$, and its convergence rate depends on $\sqrt{\lambda}$.
    *   APGD2 is the algorithm of choice for $\lambda > L$, and its rate is less influenced by changes in $\lambda$. These empirical findings align perfectly with the theoretical predictions for the APGD variants.

## 5. Limitations and Future Work

### 5.1 Limitations
*   **Inexact Oracle Matching:** For the local summand gradient oracle, the upper and lower complexity bounds do not always match, especially when $\lambda > \tilde{L}$ (recovering the classical FL setup when $\lambda = \infty$).
*   **IAPGD Drawbacks:** The IAPGD+Katyusha algorithm has several practical drawbacks: it introduces extra logarithmic factors in its local gradient complexity, requires an assumption about the boundedness of algorithm iterates, and its communication complexity is suboptimal when $\lambda > L$.
*   **AL2SGD+ Dual Optimality:** While AL2SGD+ offers significant improvements, it may require slightly different parameter setups to achieve optimality in communication versus local computation simultaneously.

### 5.2 Future Directions
The paper does not explicitly list "future directions" in a dedicated section. However, based on the identified limitations and the discussion, potential future research could include:
*   Developing new algorithms or refining existing ones to achieve simultaneous optimality in both communication and local computation across all parameter regimes (e.g., for AL2SGD+).
*   Bridging the gap between upper and lower bounds for the local summand gradient oracle, especially in cases where they do not currently match (e.g., when $\lambda > \tilde{L}$).
*   Designing robust inexact methods that do not rely on boundedness assumptions and avoid large constant or logarithmic factors in practice, improving upon the practical performance of methods like IAPGD+Katyusha.