# Paper Info

## Title
Adversarially Robust Streaming Algorithms Via Differential Privacy

## Authors
['Avinatan Hassidim', 'Haim Kaplan', 'Yishay Mansour', 'Yossi Matias', 'Uri Stemmer']

## Affiliations
[(Bar-Ilan University, Israel), (Tel Aviv University, Israel), (Google, USA), (Ben-Gurion University, Israel)]

# Brief Summary

## Highlight
This paper addresses the critical challenge of designing adversarially robust streaming algorithms, where data streams are chosen by an adaptive adversary, invalidating the accuracy guarantees of traditional "oblivious" streaming algorithms. The authors establish a novel connection between adversarial robustness and differential privacy, proposing a new methodology that uses differential privacy to protect the internal state and randomness of streaming algorithms. This approach leads to the development of robust streaming algorithms that achieve sublinear space complexity in the general turnstile model—a problem previously largely open—and provide improved space bounds compared to state-of-the-art constructions in the insertion-only model, notably reducing dependency on the "flip number" from linear to square root.

## Keywords
[Streaming Algorithms, Adversarial Robustness, Differential Privacy, Space Complexity, Turnstile Model]

# Detailed Summary

## 1. Motivation

### 1.1 Background
Streaming algorithms are essential for processing vast amounts of data generated sequentially, such as in IP traffic monitoring or web searches, while using limited memory. The majority of existing work on streaming algorithms operates under an "oblivious" setting, assuming the data stream is fixed beforehand or its elements are independent of the algorithm's internal state. This setting allows for efficient space usage, typically logarithmic with the number of queries.

### 1.2 Problem Statement
The core problem arises when the data stream and queries are chosen by an adaptive adversary, where each item depends on previous stream elements, queries, and the algorithm's prior responses. In such adaptive environments, oblivious streaming algorithms fail to provide reliable utility guarantees. The challenge is to design adversarially robust streaming algorithms that maintain provable accuracy against these adaptive adversaries while keeping memory and runtime requirements minimal, especially for the general turnstile model which allows both positive and negative updates.

## 2. State-of-the-Art Methods

### 2.1 Existing Methods
Recent work, notably by Ben-Eliezer et al. [8], introduced a formal model for adversarially robust streaming algorithms. Their generic construction relies on the concept of a "flip number" (λα,m(g)), which represents the maximal number of times a function's value can change by a factor of (1 + α) over a stream of length m. Their approach involves running multiple independent copies of an oblivious streaming algorithm in parallel. Estimates are released from one copy, and if the estimate changes significantly, a new copy is used, effectively 'flipping' to a new algorithm instance. The space overhead is proportional to the flip number.

### 2.2 Limitations of Existing Methods
The techniques of Ben-Eliezer et al. [8] are primarily effective for the insertion-only model (where all updates are positive) and for turnstile streams with a small number of negative updates, where the flip number remains small. For the general turnstile model, which permits a large number of negative updates, the flip number can be substantial, leading to a linear memory blow-up proportional to the number of algorithm copies. Consequently, robust streaming in the general turnstile model with sublinear space remained largely an open problem.

## 3. Proposed Method

### 3.1 Main Contributions
The paper's main conceptual contribution is establishing a connection between adversarial robustness of streaming algorithms and differential privacy. By leveraging differential privacy, the authors design new adversarially robust streaming algorithms that achieve sublinear space in the general turnstile model and outperform existing state-of-the-art constructions for many parameter regimes, including the insertion-only model.

### 3.2 Core Idea
The core idea is to protect the internal state and randomness of the streaming algorithm using differential privacy. The proposed algorithm, `RobustSketch`, runs `k` independent copies of an oblivious streaming algorithm in parallel. When estimates are to be released, the algorithm aggregates responses from these `k` copies. This aggregation process is made differentially private using techniques like the "sparse vector technique" (specifically, the `AboveThreshold` algorithm) to identify when estimates need to be updated, and a differentially private median estimation algorithm (`PrivateMed`) to combine the responses robustly. Differential privacy, in this context, limits the dependency between the algorithm's internal state and the adversary's choice of stream items.

### 3.3 Novelty
The novelty of `RobustSketch` lies in its innovative application of differential privacy as a tool for adversarial robustness, rather than for data privacy. This is a significant conceptual shift. By protecting the algorithm's internal randomness, the approach allows for provable accuracy guarantees even against adaptive adversaries. Quantitatively, the method provides a significant improvement in space complexity compared to prior work, particularly in the general turnstile model. For instance, the space bound grows with the square root of the flip number (`√λ`) instead of linearly (`λ`), coupled with additional logarithmic factors, leading to superior performance in scenarios where `λ` is large.

## 4. Experiment Results

### 4.1 Experimental Setup
The paper demonstrates the effectiveness of the `RobustSketch` algorithm by applying it to the problem of F2 estimation (estimating the second frequency moment of a stream).
*   **Problems**: F2 estimation (∥f (i)∥2^2) in two stream types: τ-bounded deletion streams and insertion-only streams.
*   **Oblivious Algorithms**:
    *   For τ-bounded deletion streams: Uses the oblivious algorithm from [30] with space O(1/α^2 * log^2(m/δ)).
    *   For insertion-only streams: Uses the oblivious algorithm from [10] with space Õ(1/α^2 * log(m) * log(1/δ)).
*   **Evaluation Metric**: Space complexity required to achieve α accuracy with probability 1 − δ for streams of length m.

### 4.2 Experimental Results
The `RobustSketch` algorithm yields the following space complexity bounds for F2 estimation:
*   **For τ-bounded deletion streams**: Achieves a space complexity of O(√τ/α^3 * log^4(m)). This significantly improves upon the O(τ/α^4 * log^3(n)) space used by the algorithm of Ben-Eliezer et al. [8], showing a dependency on √τ instead of τ (at the cost of additional logarithmic factors).
*   **For insertion-only streams**: Achieves a space complexity of Õ(1/α^2.5 * log^4(m)). This improves the dependency on α compared to Ben-Eliezer et al.'s [8] result of Õ(1/α^3 * log^2(m)) (again, with additional logarithmic factors).
These results highlight that the proposed method provides meaningful sublinear space guarantees for the general turnstile model and improved dependency on α and τ for existing models.

## 5. Limitations and Future Work

### 5.1 Limitations
The paper primarily focuses on presenting a new technique and demonstrating its improvements over prior work. It does not explicitly state specific limitations or shortcomings of the `RobustSketch` algorithm itself, beyond acknowledging that its improved bounds sometimes come with additional logarithmic factors compared to other techniques.

### 5.2 Future Directions
The authors suggest that the established connection between differential privacy and adversarial robustness of streaming algorithms is a starting point. They anticipate that ideas from differential privacy will find broader applications in robust streaming and related fields. Specifically, they propose that using differential privacy to protect against adversarial attacks on algorithm randomness could be generalized to other randomized machine learning models exposed to feedback loops or malicious users, fostering future research in these areas.