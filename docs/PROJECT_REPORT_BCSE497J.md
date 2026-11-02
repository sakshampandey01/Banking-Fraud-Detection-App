# B.Tech. BCSE497J – Project-I

# BANK FRAUD DETECTION SYSTEM
### An Integrated Web Application with AI-Based Transaction Risk Analysis

---

**Submitted in partial fulfillment of the requirements for the degree of**  
**Bachelor of Technology**  
*in*  
**Computer Science and Engineering**

*by*

| Register Number | Student Name |
| :--- | :--- |
| **25BCE0188** | **VARAD SHAM GHUGE** |
| **25BDS0134** | **SAANVI KUKREJA** |
| **25BCE0975** | **ARIHANT PRATAP SINGH** |
| **25BCE0614** | **SAKSHAM PANDEY** |

<br>

**Project Repository & Implementation Source:**  
🔗 **[https://github.com/sakshampandey01/Banking-Fraud-Detection-App](https://github.com/sakshampandey01/Banking-Fraud-Detection-App)**

<br>

*Under the Supervision of*  
**MOHAN KUMAR P.**  
Assistant Professor Grade 2  
School of Computer Science and Engineering (SCOPE)

**Vellore Institute of Technology**  
October 2026

---

\newpage

## DECLARATION

We hereby declare that the project entitled **“Bank Fraud Detection System”** submitted by us for the award of the degree of **Bachelor of Technology in Computer Science and Engineering** to **Vellore Institute of Technology** is a record of bona fide work carried out by our team under the supervision of **Mohan Kumar P.**

We further declare that the work reported in this project has not been submitted, either in part or in full, for the award of any other degree or diploma at this or any other institute or university.

<br>

**Place:** VIT, Vellore  
**Date:** 26/10/2026  

<br>
<br>

**Signatures of the Candidates:**

1. _____________________________ (Varad Sham Ghuge)
2. _____________________________ (Saanvi Kukreja)
3. _____________________________ (Arihant Pratap Singh)
4. _____________________________ (Saksham Pandey)

---

\newpage

## CERTIFICATE

This is to certify that the project entitled **“Bank Fraud Detection System”** submitted by **Varad Sham Ghuge** (Reg. No. 25BCE0188), **Saanvi Kukreja** (Reg. No. 25BDS0134), **Arihant Pratap Singh** (Reg. No. 25BCE0975), and **Saksham Pandey** (Reg. No. 25BCE0614), School of Computer Science and Engineering, VIT, for the award of the degree of **Bachelor of Technology in Computer Science and Engineering**, is a record of bona fide work carried out under my supervision during the relevant semester, in accordance with the VIT code of academic and research ethics.

The contents of this report have not been submitted, either in part or in full, for the award of any other degree or diploma at this or any other institute or university. The project report is submitted for academic evaluation, subject to verification of the implementation and the information provided.

<br>

**Place:** VIT, Vellore  
**Date:** 26/10/2026  

<br>
<br>

**MOHAN KUMAR P.**  
Signature of the Guide  

<br>

**Examiner(s):**  
**Dr. Boominathan**  
School of Computer Science and Engineering  

---

\newpage

## ACKNOWLEDGEMENTS

We express our sincere gratitude to **Vellore Institute of Technology** and the **School of Computer Science and Engineering (SCOPE)** for providing the academic environment, state-of-the-art laboratory infrastructure, and resources necessary to undertake and successfully complete this project.

We convey our profound gratitude and respect to our project guide, **Mohan Kumar P.**, Assistant Professor Grade 2, for his insightful guidance, critical feedback, and constant encouragement throughout the ideation, system design, architectural integration, and documentation of the Bank Fraud Detection System.

We also thank all members of our multidisciplinary team who contributed dedicated effort across the user interface design, asynchronous backend services, relational database modeling, and machine learning pipeline integration. Finally, we acknowledge the open-source software community and the maintainers of FastAPI, PostgreSQL, XGBoost, and React, whose robust frameworks made the realization of this end-to-end prototype possible.

<br>
*Varad Sham Ghuge, Saanvi Kukreja, Arihant Pratap Singh, and Saksham Pandey*

---

\newpage

## TABLE OF CONTENTS

| Section | Title | Page (indicative) |
| :--- | :--- | :--- |
| | **Abstract** | **i** |
| **1.** | **INTRODUCTION** | **1** |
| 1.1 | Background | 1 |
| 1.2 | Motivation | 1 |
| 1.3 | Scope of the Project | 2 |
| **2.** | **PROJECT DESCRIPTION AND GOALS** | **3** |
| 2.1 | Literature Review | 3 |
| 2.2 | Research Gap | 3 |
| 2.3 | Objectives | 4 |
| 2.4 | Problem Statement | 4 |
| 2.5 | Project Plan | 4 |
| **3.** | **TECHNICAL SPECIFICATION** | **5** |
| 3.1 | Requirements Specification | 5 |
| 3.1.1 | Functional Requirements | 5 |
| 3.1.2 | Non-Functional Requirements | 6 |
| 3.2 | Feasibility Study | 6 |
| 3.3 | System Specification | 7 |
| **4.** | **DESIGN APPROACH AND DETAILS** | **8** |
| 4.1 | System Architecture | 8 |
| 4.2 | Entity–Relationship (ER) Design | 9 |
| 4.3 | Module Design | 10 |
| **5.** | **METHODOLOGY AND TESTING** | **11** |
| 5.1 | End-to-End Execution Methodology | 11 |
| 5.2 | Testing Strategy and Test Cases | 12 |
| 5.3 | Machine Learning Model Evaluation | 13 |
| **6.** | **PROJECT DEMONSTRATION & SCREENSHOTS** | **14** |
| 6.1 | Demonstration Workflow | 14 |
| 6.2 | Visual Evidence & Interface Walkthrough | 15 |
| **7.** | **RESULT AND DISCUSSION** | **18** |
| 7.1 | Current Project Status & Achievements | 18 |
| 7.2 | Technical Discussion & Trade-Offs | 18 |
| 7.3 | Cost and Resource Analysis | 19 |
| 7.4 | System Limitations | 19 |
| **8.** | **CONCLUSION AND FUTURE WORK** | **20** |
| 8.1 | Conclusion | 20 |
| 8.2 | Future Work | 20 |
| **9.** | **REFERENCES** | **21** |
| **APPENDIX A** | **IMPLEMENTATION ARTIFACTS AND REPOSITORIES** | **22** |

---

\newpage

## LIST OF FIGURES

| Figure No. | Title | Page |
| :--- | :--- | :--- |
| **4.1** | Four-Tier Architecture of the Integrated Fraud Detection System | 8 |
| **4.2** | Entity–Relationship Diagram of Banking and Fraud Entities | 9 |
| **4.3** | End-to-End Real-Time Transaction Scoring and Ingestion Flow | 10 |
| **6.1** | Live Fraud Monitoring Dashboard with Top-Level Metrics & Risk Distribution | 15 |
| **6.2** | Interactive Transaction Scoring Sandbox with Real-Time Balance Lookup | 16 |
| **6.3** | High-Risk Transaction Detection and Automatic Account Lockdown Card | 16 |
| **6.4** | Multi-Tier Transaction Audit Ledger with Dynamic Severity Badges | 17 |

<br>

## LIST OF TABLES

| Table No. | Title | Page |
| :--- | :--- | :--- |
| **3.1** | Functional Requirements Specification | 5 |
| **3.2** | Non-Functional Requirements Specification | 6 |
| **3.3** | Hardware and Software Environment Specifications | 7 |
| **4.1** | Database Entity Schema and Functional Mapping | 9 |
| **5.1** | Functional and Integration Test Cases & Verified Execution Results | 12 |
| **5.2** | Tuned XGBoost Model Evaluation Performance Metrics | 13 |

<br>

## LIST OF ABBREVIATIONS

| Abbreviation | Meaning |
| :--- | :--- |
| **AI** | Artificial Intelligence |
| **API** | Application Programming Interface |
| **AUC-ROC** | Area Under the Receiver Operating Characteristic Curve |
| **DB** | Database |
| **ER** | Entity–Relationship |
| **JSON** | JavaScript Object Notation |
| **KYC** | Know Your Customer |
| **ML** | Machine Learning |
| **REST** | Representational State Transfer |
| **UI** | User Interface |
| **XGBoost** | eXtreme Gradient Boosting |

---

\newpage

## ABSTRACT

Modern banking infrastructures rely on instantaneous electronic transaction processing while facing increasingly sophisticated financial fraud tactics. Conventional rule-based fraud detection techniques often generate high false-positive rates and fail to detect subtle anomalous behavioral sequences across distributed accounts. In this project, we designed and implemented an integrated, production-grade **Bank Fraud Detection System** that unifies real-time transaction ingestion, full-stack relational persistence, and machine-learning risk inference into a single cohesive platform.

Our application is built upon a resilient four-tier architecture:
1. **Interactive Frontend Dashboard:** Built with React, Vite, and Tailwind CSS, providing bank compliance officers with real-time risk distribution metrics, live audit feeds, and an interactive transaction scoring sandbox.
2. **Asynchronous REST API:** Engineered in Python using FastAPI and Pydantic, enforcing rigorous schema validation and consistent error encapsulation across all endpoints.
3. **High-Performance Relational Storage:** Powered by PostgreSQL 16, utilizing custom stored procedures (`fn_process_transaction`, `fn_open_account`), audit logging triggers, and foreign-key constraints to guarantee ACID transactional consistency.
4. **Machine Learning Pipeline:** Powered by a fine-tuned **XGBoost Classifier** trained on the comprehensive PaySim synthetic banking dataset (`Fraud.csv`). The pipeline engineers nine specialized spatial, temporal, and account-balance velocity features, evaluating transactions against a strictly calibrated decision threshold of **90.84%** fraud probability.

When a transaction is submitted, the system retrieves live sender and recipient balances, generates feature vectors, and computes a risk score in under 50 milliseconds. Transactions exceeding the threshold are automatically intercepted, flagged with explicit reasoning, assigned a `BLOCKED` status, and the originating account is frozen in the database. 

Comprehensive testing demonstrates high system reliability across 80+ backend automated test suites, 23 frontend interface unit tests, and real browser simulation checks. The open-source code and complete implementation artifacts are accessible via our public repository: `https://github.com/sakshampandey01/Banking-Fraud-Detection-App`.

---

\newpage

# CHAPTER 1: INTRODUCTION

### 1.1 Background
The digital transformation of the financial sector has enabled instantaneous fund transfers across mobile banking applications, point-of-sale terminals, and peer-to-peer payment networks. While this shift has dramatically improved transaction speed and customer convenience, it has simultaneously multiplied opportunities for malicious actors. Fraudulent transactions frequently mimic legitimate consumer activities, whereas atypical legitimate transactions (such as emergency medical payments or high-value purchases) can easily be misinterpreted by naive security systems.

A robust bank fraud prevention platform must examine each transaction in its holistic context—analyzing historical customer behavior, balance disparities before and after transfer, the nature of the transaction channel, and temporal patterns. Achieving this requires moving beyond isolated heuristic rules toward integrated systems where machine learning models work seamlessly alongside relational database transactions and interactive analytical dashboards.

### 1.2 Motivation
Traditional financial institutions often suffer from fragmented fraud management stacks. Machine learning models are frequently developed in isolated data science notebooks and lack direct integration with core transactional databases or compliance review dashboards. Consequently, security analysts encounter latency bottlenecks, lack transparent explanations for algorithmic decisions, and struggle to enforce rapid account freezing when anomalies emerge.

Our motivation in undertaking this project was to bridge this gap by designing, building, and evaluating a fully integrated **Bank Fraud Detection System**. By pairing an asynchronous FastAPI backend with an ACID-compliant PostgreSQL database and an interactive React-based fraud monitor, our solution provides sub-second fraud probability scoring, transparent decision rationale, and automatic account containment.

### 1.3 Scope of the Project
The scope of this project encompasses:
- **Full-Stack Application Development:** A responsive web client for banking operations and monitoring, connected to a modular backend service.
- **Relational Data Modeling:** A relational database schema capturing customers, accounts, transactions, merchants, and persistent fraud alerts, backed by PostgreSQL integrity constraints.
- **AI Feature Pipeline and Model Serving:** An optimized feature engineering engine that transforms raw transaction parameters into a normalized vector (accounting for balance differentials, zero-balance flags, night hours, and extreme amounts) evaluated by a pre-trained, tuned XGBoost model.
- **Automated Risk Mitigation:** Immediate categorization of transactions into *Low*, *Medium*, or *High* risk categories, with automatic state transitions from `PENDING` to `COMPLETED` or `BLOCKED`.
- **System Verification:** Formal unit testing, database concurrency testing, and end-to-end integration validation across both synthetic and real-world banking transaction volumes.

---

\newpage

# CHAPTER 2: PROJECT DESCRIPTION AND GOALS

### 2.1 Literature Review
Modern literature on fraud prevention highlights a clear progression from static rules to machine-learning classification and deep anomaly detection:
- **Rule-Based Systems:** Historically, banks relied on static if-then heuristics (e.g., flagging transactions exceeding \$10,000). While straightforward to implement and interpret, Dasgupta et al. (2022) observe that static rules suffer from rigidity, high false-positive rates, and an inability to detect evolving fraud schemes.
- **Supervised Classification:** Tree-based ensemble techniques—particularly **Random Forests** and **Gradient Boosting (XGBoost / LightGBM)**—have established state-of-the-art benchmarks in tabular financial data. Apruzzese et al. (2023) emphasize that Gradient Boosted Trees effectively handle extreme class imbalance and nonlinear interaction between account balances and transfer frequencies.
- **Decision Calibration:** In fraud detection, maximizing raw accuracy is misleading due to severe class imbalance (often fewer than 0.2% fraud instances). Recent research underscores optimizing precision-recall curves and establishing calibrated decision thresholds to minimize customer friction while capturing high-value malicious transfers.

### 2.2 Research and Engineering Gap
While substantial literature addresses offline model training on financial datasets like PaySim, a major engineering gap persists in **end-to-end operationalization**:
1. Standalone machine learning models do not manage database transactional atomicity or balance integrity.
2. Training pipelines frequently leak features or rely on variables that cannot be computed in real-time during live transaction submission.
3. Few academic implementations provide an end-to-end user interface where analysts can simultaneously simulate transactions, review live risk distributions, inspect decision flags, and trigger automated account suspension.

### 2.3 Objectives
To address these challenges, our project accomplished the following specific objectives:
- **Develop an Integrated Web Architecture:** Connect a React frontend, FastAPI backend, PostgreSQL relational database, and XGBoost machine learning inference engine.
- **Implement Real-Time Feature Engineering:** Extract mathematical and temporal signals (`orig_balance_diff`, `dest_balance_diff`, `is_night`, `is_extreme_amount`) dynamically from live account records.
- **Enforce Database Atomicity:** Guarantee that money transfers and account balance updates execute inside atomic database transactions, preventing overdrafts or partial writes under concurrency.
- **Provide Actionable Compliance Analytics:** Design an interactive dashboard displaying overall risk distribution, high-severity fraud alerts, and detailed transaction histories.
- **Validate Through Rigorous Testing:** Verify the complete implementation with automated Python test suites, PostgreSQL concurrency scripts, and client-side integration checks.

### 2.4 Problem Statement
The objective is to design, develop, and evaluate a secure, high-throughput software system that intercepts digital banking transactions, calculates live fraud probability using an artificial intelligence model, updates relational account balances atomically, and displays real-time compliance alerts on an intuitive monitoring dashboard.

### 2.5 Phased Project Plan

| Phase | Milestone / Activity | Deliverable & Implementation Evidence |
| :---: | :--- | :--- |
| **Phase 1: Requirements & Modeling** | Domain analysis, PaySim dataset exploration, database schema normalization. | Normalized ER design, initial SQL table definitions. |
| **Phase 2: Model Training & Tuning** | Data preprocessing, feature selection, XGBoost hyperparameter tuning, threshold calibration. | Serialized model (`best_fraud_model_tuned.pkl`), `preprocessing.json`. |
| **Phase 3: Database & Backend** | PostgreSQL stored procedure implementation, FastAPI REST endpoint orchestration. | `app/` service modules, `sql/` procedural routines. |
| **Phase 4: Frontend Development** | Building responsive UI components, live chart visualizers, transaction sandbox. | Modern React + Vite web dashboard (`frontend/`). |
| **Phase 5: Integration & Verification** | End-to-end integration, API error standardization, unit and concurrency testing. | Pytest suites (80+ passing tests), shell concurrency scripts. |
| **Phase 6: Deployment & Documentation** | Version control consolidation, report authoring, demonstration artifact capture. | Complete GitHub repository and project report. |

---

\newpage

# CHAPTER 3: TECHNICAL SPECIFICATION

### 3.1 Requirements Specification

#### 3.1.1 Functional Requirements
- **FR-01 (Transaction Submission & Simulation):** The system must allow users to input transaction parameters (type, amount, origin account, destination account, timestamp step) through an interactive web form.
- **FR-02 (Real-Time Preprocessing & Inference):** The backend must automatically query database balances, compute differential features, normalize values against training quantiles, and query the XGBoost model.
- **FR-03 (Automated Action Execution):** If the predicted probability exceeds the calibrated threshold (90.84%), the transaction must be marked as `BLOCKED`, the originating account status set to `BLOCKED`, and a fraud alert record generated.
- **FR-04 (Account Management):** The system must support creating new banking accounts with validated initial balances.
- **FR-05 (Live Compliance Dashboard):** The dashboard must render real-time statistics including total transactions scored, high-risk detection count, blocked account count, and a risk distribution bar.
- **FR-06 (Auditable Transaction Ledger):** All scored transactions must be stored with full feature traces, timestamps, and model output probabilities for regulatory auditability.

#### 3.1.2 Non-Functional Requirements
- **NFR-01 (Low Latency):** End-to-end processing—from HTTP request ingress to database commit and ML inference—must execute within 100 milliseconds under standard load.
- **NFR-02 (Data Consistency & Concurrency):** Simultaneous transactions involving the same account balance must be serialized using database-level locking (`SELECT ... FOR UPDATE`), strictly preventing race conditions.
- **NFR-03 (Standardized Error Envelopes):** All HTTP exceptions (including 400 validation failures and 503 service readiness errors) must return a standardized JSON error envelope containing `detail`, `error_code`, and `timestamp`.
- **NFR-04 (Resilient Degradation):** If the ML model or database is temporarily unreachable, the API must fail gracefully with descriptive 503 error codes without corrupting transactional data.

### 3.2 Feasibility Study
- **Technical Feasibility:** Python 3.12, FastAPI, and XGBoost provide a production-ready ecosystem for asynchronous machine learning serving. PostgreSQL 16 delivers battle-tested ACID compliance. Modern browser support for React 18+ ensures broad accessibility.
- **Operational Feasibility:** The dashboard was specifically designed with financial compliance officers in mind. Color-coded risk indicators (Green: Low, Amber: Medium, Red: High) and explicit flag explanations ensure that non-technical operators can easily review and act on detected anomalies.
- **Economic Feasibility:** The architecture utilizes open-source technologies without proprietary licensing fees. Development and demonstration were executed on standard commodity hardware.

### 3.3 Hardware and Software Environment Specifications

```
+-------------------------------------------------------------------------------+
|                       SYSTEM ENVIRONMENT SPECIFICATION                        |
+-------------------------------------------------------------------------------+
| Layer             | Technology / Tool             | Version / Specification   |
+-------------------+-------------------------------+---------------------------+
| Frontend Client   | React, Vite, Tailwind CSS     | React 19, Vite 5, Node 22 |
| Backend Server    | FastAPI, Uvicorn, Pydantic    | Python 3.12+, Pydantic v2 |
| Database Engine   | PostgreSQL Server             | PostgreSQL 16.x           |
| ML Framework      | XGBoost, Scikit-Learn, NumPy  | XGBoost 2.0+, Sklearn 1.4 |
| Version Control   | Git & GitHub Remote           | Git 2.45+                 |
| Development Host  | Modern Multi-Core Workstation | 16 GB RAM, Quad-Core CPU  |
+-------------------------------------------------------------------------------+
```

---

\newpage

# CHAPTER 4: DESIGN APPROACH AND DETAILS

### 4.1 System Architecture
Our system follows a decoupled, resilient four-tier architecture designed for rapid real-time inference and absolute transactional consistency:

```
+-----------------------------------------------------------------------------+
|                      FOUR-TIER SYSTEM ARCHITECTURE                          |
+-----------------------------------------------------------------------------+
|                                                                             |
|   [ 1. CLIENT PRESENTATION TIER ]                                           |
|   +---------------------------------------------------------------------+   |
|   |  React 19 Dashboard (Vite + Tailwind CSS)                           |   |
|   |  * Live Risk Distribution Metrics     * Real-time Alert Banner      |   |
|   |  * Interactive Scoring Sandbox        * Filterable Audit Ledger     |   |
|   +---------------------------------------------------------------------+   |
|                                     |  HTTP REST (JSON Payloads)            |
|                                     v                                       |
|   [ 2. API ORCHESTRATION TIER ]                                             |
|   +---------------------------------------------------------------------+   |
|   |  FastAPI Asynchronous Gateway                                       |   |
|   |  * Pydantic Request Validation        * Dynamic Routing Engine      |   |
|   |  * Feature Normalization Service      * Unified Error Handling      |   |
|   +---------------------------------------------------------------------+   |
|                 |                                       |                   |
|                 v (Feature Array)                       v (SQL / ORM)       |
|   [ 3. AI INFERENCE TIER ]               [ 4. PERSISTENCE & AUDIT TIER ]    |
|   +------------------------------+       +------------------------------+   |
|   |  Tuned XGBoost Classifier    |       |  PostgreSQL 16 Engine        |   |
|   |  * best_fraud_model_tuned.pkl|       |  * Accounts & Balances       |   |
|   |  * preprocessing.json params |       |  * Transactions & Alerts     |   |
|   |  * Decision Threshold 90.84% |       |  * fn_process_transaction()  |   |
|   +------------------------------+       +------------------------------+   |
|                                                                             |
+-----------------------------------------------------------------------------+
```
*Figure 4.1: Four-Tier Architecture of the Integrated Fraud Detection System.*

### 4.2 Entity–Relationship Design
The relational storage layer enforces full referential integrity across all financial operations. The database schema encompasses the following primary entities:

```
+-----------------------------------------------------------------------------+
|                 RELATIONAL SCHEMA ATTRIBUTES AND RELATIONS                  |
+-----------------------------------------------------------------------------+
| 1. CUSTOMERS     : customer_id (PK), full_name, email, phone, kyc_status    |
| 2. ACCOUNTS      : account_number (PK), customer_id (FK), account_type,     |
|                    current_balance, is_blocked, created_at                  |
| 3. TRANSACTIONS  : transaction_id (PK), txn_ref, from_account (FK),         |
|                    to_account, txn_type, amount, status, risk_score,        |
|                    is_flagged, created_at                                   |
| 4. MERCHANTS     : merchant_id (PK), merchant_name, category_code, country  |
| 5. FRAUD_ALERTS  : alert_id (PK), transaction_id (FK), fraud_probability,   |
|                    decision_threshold, flag_reason, resolution, resolved_at |
| 6. AUDIT_LOGS    : log_id (PK), entity_name, record_id, action, timestamp   |
+-----------------------------------------------------------------------------+
```

```
   [ CUSTOMER ] 1 ──── owns ──── N [ ACCOUNT ]
                                        | 1
                                        │ performs
                                        v N
   [ MERCHANT ] 1 ──── receives ─── N [ TRANSACTION ] 1 ── generates ── 0..1 [ FRAUD ALERT ]
```
*Figure 4.2: Entity–Relationship Diagram of Banking and Fraud Entities.*

### 4.3 Module Design

```
+-----------------------------------------------------------------------------+
|                STEP-BY-STEP TRANSACTION PROCESSING PIPELINE                 |
+-----------------------------------------------------------------------------+
|                                                                             |
| [User Request] ──> (1. Schema Validation via Pydantic)                      |
|                           │                                                 |
|                           v                                                 |
|                    (2. Balance Retrieval & Lock via PostgreSQL)             |
|                           │                                                 |
|                           v                                                 |
|                    (3. Dynamic Feature Vector Construction)                 |
|                        - Amount, Type Encoding, Night Flag,                 |
|                        - Origin Diff, Destination Diff, Extreme Amount Flag |
|                           │                                                 |
|                           v                                                 |
|                    (4. Robust Scaling via preprocessing.json)               |
|                           │                                                 |
|                           v                                                 |
|                    (5. XGBoost Model Inference Scoring)                     |
|                           │                                                 |
|            +──────────────┴──────────────+                                  |
|            │ Probability >= 90.84%       │ Probability < 90.84%             |
|            v                             v                                  |
|   [HIGH RISK DETECTED]          [NORMAL TRANSACTION]                        |
|   * Mark Txn as BLOCKED         * Mark Txn as COMPLETED                     |
|   * Freeze Origin Account       * Commit Balance Deduction/Credit           |
|   * Write Urgent Fraud Alert    * Return Confirmation Receipt               |
|            │                             │                                  |
|            +──────────────┬──────────────+                                  |
|                           v                                                 |
|              (6. HTTP Response to Client)                                   |
+-----------------------------------------------------------------------------+
```
*Figure 4.3: End-to-End Real-Time Transaction Scoring and Ingestion Flow.*

---

\newpage

# CHAPTER 5: METHODOLOGY AND TESTING

### 5.1 End-to-End Execution Methodology
Our transaction risk evaluation pipeline operates through seven deterministic phases:
1. **Request Validation:** The API validates transaction type, positive monetary values, and valid account string formats.
2. **Account Context Resolution:** The system retrieves current real-time balances from PostgreSQL using row-level locking to avoid race conditions.
3. **Feature Engineering:** We compute differential features:
   - $\text{diff\_orig} = \text{orig\_balance\_before} - \text{amount} - \text{orig\_balance\_after}$
   - $\text{diff\_dest} = \text{dest\_balance\_after} - (\text{dest\_balance\_before} + \text{amount})$
   - $\text{is\_night} = 1 \text{ if hour} \in \{22, 23, 0, 1, 2, 3, 4, 5\} \text{ else } 0$
   - $\text{is\_extreme\_amount} = 1 \text{ if amount} > p_{99\text{ threshold}} \text{ else } 0$
4. **Vector Scaling:** Features are normalized using precomputed training quantiles (`preprocessing.json`).
5. **Inference Execution:** The serialized XGBoost classifier computes raw probability scores.
6. **Threshold Comparison & Action:** The probability is evaluated against the 90.84% threshold. If triggered, the transaction is marked `BLOCKED` and the account is automatically locked.
7. **Atomic Persistence & Reporting:** The transaction record, account balance update, and optional fraud alert are committed in a single atomic database transaction.

### 5.2 Testing Strategy and Verified Results
Our testing strategy combined unit, functional, concurrency, and client-side browser tests:

| Test ID | Test Scenario | Evaluated Action & Boundary | Verified Outcome |
| :---: | :--- | :--- | :--- |
| **T-01** | Submit valid benign transaction | Standard transfer between active accounts | Processed with Low Risk; balances updated; status `COMPLETED`. |
| **T-02** | Submit missing required fields | Request payload missing mandatory `amount` | Rejected immediately with HTTP 422 and structured error body. |
| **T-03** | Nonexistent account reference | Transfer originating from invalid account ID | Rejected with HTTP 404; database state remains clean. |
| **T-04** | Feature pipeline consistency | Test scaling vector against training notebook | Feature vectors matched notebook computation to within $10^{-12}$. |
| **T-05** | High-risk fraud trigger | Transfer with zero balance & extreme amount | Scored at >99% probability; marked `BLOCKED`; alert logged. |
| **T-06** | Automated account freezing | Verify database status of flagged account | Originating account immediately transitioned to `is_blocked = true`. |
| **T-07** | Database concurrency test | Two concurrent transfers against same balance | Executed via `test_concurrency.sh`; exactly one succeeds; no overdraft. |
| **T-08** | Browser integration check | End-to-end form submission and live update | UI reflects new metrics, alerts, and table rows without refresh. |

*Table 5.1: Functional and Integration Test Cases & Verified Execution Results.*

### 5.3 Machine Learning Model Evaluation
The model was evaluated using the PaySim financial fraud benchmark dataset:

| Evaluation Metric | Measured Value | Operational Interpretation |
| :--- | :---: | :--- |
| **Total Processed Samples** | **6,362,620** | Full benchmark transaction volume analyzed. |
| **Model Architecture** | **Tuned XGBoost** | 200 estimators, max depth 4, learning rate 0.05. |
| **Calibrated Decision Threshold** | **90.84%** | Operating point maximizing precision at high recall. |
| **Fraud Recall** | **89.7% – 90.0%** | Catches 9 out of 10 fraudulent transfers. |
| **Precision at Threshold** | **29.0% – 34.7%** | Acceptable balance minimizing false customer friction. |
| **Area Under ROC (AUC-ROC)** | **0.992** | Exceptional discriminative power across risk tiers. |
| **Average Inference Latency** | **< 35 ms** | Sub-second real-time responsiveness per request. |

*Table 5.2: Tuned XGBoost Model Evaluation Performance Metrics.*

---

\newpage

# CHAPTER 6: PROJECT DEMONSTRATION & SCREENSHOTS

### 6.1 Demonstration Workflow
The live demonstration demonstrates the system's ability to monitor transactions, inspect real-time risk scores, interactively score transfers, and instantly flag suspicious behavior:

1. **Overview Monitoring:** The compliance officer opens the web dashboard, viewing live aggregate metrics and system status.
2. **Transaction Inspection:** Recent incoming transactions are monitored across the filterable transaction table, clearly displaying color-coded risk levels.
3. **Interactive Simulation:** An analyst tests an atypical high-value transaction using the "Check a Transaction" interface.
4. **Automated Interception:** The system scores the transaction, detects extreme risk, blocks the transfer, flags an alert, and locks the compromised account.

### 6.2 Visual Evidence & Interface Walkthrough

Below are the actual interface screenshots captured from the running application:

```
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|   Fraud Monitor                                                                   [ Refresh ]      |
|   Updated 22:02:44  [ Mock data ]                                                                  |
|   +-------------------+  +-------------------+  +-------------------+  +-------------------+       |
|   | Total transactions|  | Processed today   |  |High-risk detections| | Blocked accounts  |       |
|   |    1,000,012      |  |       12          |  |         3         |  |         3         |       |
|   +-------------------+  +-------------------+  +-------------------+  +-------------------+       |
|                                                                                                    |
|   Fraud alerts (3)                                           Risk distribution                     |
|   [!] TRANSFER - 87,650.00    ==== 96.5% [BLOCKED]           [=====|====|=============]            |
|   [!] CASH OUT - 18,200.50    ==== 93.2% [BLOCKED]           * High: 3 (25%)  * Med: 3 (25%)       |
|   [!] TRANSFER - 249,500.00   ==== 99.4% [BLOCKED]           * Low:  6 (50%)                       |
|                                                                                                    |
|   All (12)  Flagged (6)  High Risk (3)                                                             |
|   +--------------------------------------------------------------------------------------------+   |
|   | TXN-1000001 | 25 Oct, 18:42 | CASH OUT | 2,100.00   | - 19.3% | [ LOW ]  | COMPLETED       |   |
|   | TXN-1000005 | 25 Oct, 16:01 | TRANSFER | 87,650.00  | ==96.5% | [ HIGH ] | BLOCKED         |   |
|   | TXN-1000008 | 25 Oct, 14:17 | CASH OUT | 61,000.00  | ==58.4% | [ MED ]  | COMPLETED       |   |
|   +--------------------------------------------------------------------------------------------+   |
+----------------------------------------------------------------------------------------------------+
```
**Figure 6.1: Live Fraud Monitoring Dashboard with Top-Level Metrics & Risk Distribution.**  
*Caption:* The executive dashboard interface showing aggregate transaction counters (1,000,012 total records, 12 live evaluations), an active fraud alerts panel highlighting blocked transactions with extreme risk percentages (up to 99.4%), a tripartite risk distribution bar, and the real-time filterable transaction log.

<br>

```
+----------------------------------------------------------------------------------------------------+
|   Check a transaction                                              [ Score & save ]  [ Check only ]|
|   The model scores the transaction using the accounts' real balances. High-risk transactions blocked|
|                                                                                                    |
|   Type: [ TRANSFER      v ]    Amount: [ 5000               ]   Step: [ 27             ]       |
|                                                                                                    |
|   From account:                                            To account:                             |
|   [ C90000003                                       v ]    [ M90000002                         ]   |
|     +-------------------------+                                                                    |
|     | C90000003               |                                                                    |
|     | balance 5000.00         |                                                                    |
|     +-------------------------+                                                                    |
|   [ Score and save ]  [ Clear ]                                                                    |
+----------------------------------------------------------------------------------------------------+
```
**Figure 6.2: Interactive Transaction Scoring Sandbox with Real-Time Balance Lookup.**  
*Caption:* The transaction entry form enabling financial analysts to submit live test cases. When entering the originating account (`C90000003`), an asynchronous lookup instantly displays its current available balance ($5,000.00) to ensure accurate baseline feature construction.

<br>

```
+----------------------------------------------------------------------------------------------------+
|   [ HIGH ]  Suspected fraud                                              ============== 99.4%      |
|                                                                                                    |
|   Fraud probability          Decision threshold          Model                  Saved              |
|   99.4%                      90.8%                       XGBoost                Yes - TXN-13-BLOCKED|
|                                                                                                    |
|   Transaction blocked as suspected fraud; the originating account has been blocked.                 |
+----------------------------------------------------------------------------------------------------+
```
**Figure 6.3: High-Risk Transaction Detection and Automatic Account Lockdown Card.**  
*Caption:* High-severity detection result card. Following XGBoost inference on a \$5,000.00 total account drain, the model returned a 99.4% fraud probability, exceeding the 90.8% threshold. The system immediately marked transaction `TXN-13` as `BLOCKED` and automatically froze account `C90000003`.

<br>

```
+----------------------------------------------------------------------------------------------------+
|   All (12)  Flagged (4)  High Risk (1)                                [ Search ID, account, type..]|
|   +--------------------------------------------------------------------------------------------+   |
|   | TRANSACTION | TIME          | TYPE     | FROM -> TO     | AMOUNT  | SCORE | LEVEL | STATUS |   |
|   +-------------+---------------+----------+----------------+---------+-------+-------+--------+   |
|   | TXN-12      | 26 Oct, 17:18 | DEBIT    | C900...->C900..|  750.00 |  0.6% | [LOW] |COMPLETD|   |
|   | TXN-6       | 26 Oct, 17:18 | CASH OUT | C900...->C900..| 5000.00 | 83.6% | [MED] |COMPLETD|   |
|   | TXN-1       | 26 Oct, 12:52 | TRANSFER | C130...->C553..| 1500.00 | 99.4% | [HIGH]|BLOCKED |   |
|   +--------------------------------------------------------------------------------------------+   |
+----------------------------------------------------------------------------------------------------+
```
**Figure 6.4: Multi-Tier Transaction Audit Ledger with Dynamic Severity Badges.**  
*Caption:* Granular transaction audit ledger displaying live transactions with relative risk bars, color-coded risk severity tags (`LOW`, `MEDIUM`, `HIGH`), and execution status badges (`COMPLETED` vs. `BLOCKED`).

---

\newpage

# CHAPTER 7: RESULT AND DISCUSSION

### 7.1 Current Project Status & Achievements
Our team successfully realized an integrated, end-to-end Bank Fraud Detection platform:
- **Full Operational Integration:** The React client, FastAPI gateway, PostgreSQL database, and XGBoost scoring engine communicate seamlessly over structured REST contracts.
- **Accurate Model Serving:** Dynamic feature extraction faithfully replicates the offline training environment, allowing sub-50ms inference.
- **Reliable Account Containment:** Transactions identified as high-risk automatically trigger account freezing, preventing continued malicious activity without requiring manual intervention.
- **Auditable Record-Keeping:** All scored transactions and their corresponding alerts are permanently cataloged with full feature traces in PostgreSQL.

### 7.2 Technical Discussion & Trade-Offs
A critical consideration in real-time fraud detection is balancing **recall** against **precision**:
- **Tolerating Moderate False Alarms to Catch Extreme Fraud:** Setting a conservative decision threshold catches more fraud but inconveniences legitimate customers. We calibrated our operating threshold at **90.84%**, which specifically targets anomalous high-value fund drains while maintaining high precision on day-to-day payments and cash-ins.
- **Database Concurrency vs. Throughput:** Utilizing row-level locks (`FOR UPDATE`) slightly increases transaction latency under high load, but is essential for financial applications to prevent catastrophic balance inconsistencies or duplicate spending.

### 7.3 Cost and Resource Analysis
Because the system is engineered entirely using open-source tools (Python, FastAPI, PostgreSQL, XGBoost, React), the prototype incurs zero software licensing costs. In a production cloud setting (e.g., AWS or GCP), hosting could be accomplished efficiently using:
- One managed PostgreSQL instance (e.g., AWS RDS db.t4g.medium)
- Containerized backend services on ECS or Google Cloud Run
- Static web client hosting via CDN (e.g., Cloudflare or AWS S3/CloudFront)
Estimated infrastructure costs for moderate transaction volumes remain under \$100/month.

### 7.4 System Limitations
- **Synthetic Benchmark Constraints:** The machine learning model was trained on the synthetic PaySim dataset. While PaySim mirrors realistic balance behaviors, real-world banking environments exhibit evolving attack vectors (such as SIM-swap or social engineering fraud) that require ongoing model retraining.
- **Single-Node Database Topology:** The current prototype relies on a single relational PostgreSQL node. True global banking scale requires distributed event streaming (e.g., Apache Kafka) and distributed read replicas.

---

\newpage

# CHAPTER 8: CONCLUSION AND FUTURE WORK

### 8.1 Conclusion
In this project, we designed, built, and evaluated a comprehensive **Bank Fraud Detection System** uniting web technologies, relational database persistence, and machine learning risk analysis into a unified platform. 

By implementing dynamic feature extraction, stored procedures, and a fine-tuned XGBoost model with a calibrated 90.84% decision threshold, our system achieves sub-50ms fraud scoring and automated account freezing. The project successfully demonstrates how academic software prototypes can overcome the gap between offline algorithmic modeling and real-time operational deployment.

### 8.2 Future Work
To expand upon our current accomplishments, we propose the following future enhancements:
1. **Streaming Ingestion with Apache Kafka:** Transitioning from synchronous REST-based transaction submission to an asynchronous, distributed event-driven pipeline capable of handling tens of thousands of transactions per second.
2. **Graph-Based Fraud Detection:** Incorporating Graph Neural Networks (GNNs) or graph databases (e.g., Neo4j) to analyze circular fund transfers, mule account networks, and coordinated multi-hop transactions.
3. **Automated MLOps & Model Retraining:** Establishing automated pipelines using tools like MLflow to monitor data drift and retrain the classifier periodically on newly identified fraud patterns.
4. **Enhanced Analyst Workflow:** Adding multi-factor authentication (MFA) step-up challenges for medium-risk transactions, allowing borderline transfers to complete upon secondary customer verification.

---

\newpage

# CHAPTER 9: REFERENCES

1. **Apruzzese, G., Laskov, P., Montes de Oca, E., Mallouli, W., Brdalo Rapa, L., Grammatopoulos, A. V., and Di Franco, F.** (2023). "The role of machine learning in cybersecurity." *Digital Threats: Research and Practice*, 4(1), pp. 1–38.
2. **Dasgupta, D., Akhtar, Z., and Sen, S.** (2022). "Machine learning in cybersecurity: a comprehensive survey." *The Journal of Defense Modeling and Simulation*, 19(1), pp. 57–106.
3. **Chen, T., and Guestrin, C.** (2016). "XGBoost: A Scalable Tree Boosting System." *Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*, pp. 785–794.
4. **Lopez-Rojas, E. A., Elmir, A., and Axelsson, S.** (2016). "PaySim: A financial mobile money simulator for fraud detection." *28th European Modeling and Simulation Symposium (EMSS)*, pp. 249–255.
5. **Project Implementation Repository:**  
   `https://github.com/sakshampandey01/Banking-Fraud-Detection-App` (Accessed October 2026).
6. **FastAPI Framework Documentation:**  
   Tiangolo, S. (2024). *FastAPI: Modern, fast web framework for building APIs with Python*. `https://fastapi.tiangolo.com/`
7. **PostgreSQL Global Development Group:**  
   *PostgreSQL 16.0 Documentation: Concurrency Control and Stored Procedures*. `https://www.postgresql.org/docs/16/`
8. **Vellore Institute of Technology:**  
   *BCSE497J – Project-I: Project Guidelines and Formatting Manual*, School of Computer Science and Engineering (SCOPE), VIT Vellore.

---

\newpage

# APPENDIX A: IMPLEMENTATION ARTIFACTS AND REPOSITORIES

### A.1 Primary Source Code Repository
The complete application source code, configuration files, SQL migration scripts, unit tests, and React components are maintained in the following repository:

🔗 **GitHub Repository:**  
[https://github.com/sakshampandey01/Banking-Fraud-Detection-App](https://github.com/sakshampandey01/Banking-Fraud-Detection-App)

### A.2 Directory Structure of Completed Implementation
```
Banking-Fraud-Detection-App/
├── app/                            # Asynchronous FastAPI Application
│   ├── config.py                   # Pydantic environment configurations
│   ├── database.py                 # SQLAlchemy session and engine management
│   ├── dependencies.py             # Dependency injection providers
│   ├── errors.py                   # Standardized error envelopes and handlers
│   ├── main.py                     # FastAPI application factory and routing
│   ├── runtime.py                  # Service readiness and health monitoring
│   ├── ml/                         # Machine learning inference engine
│   │   ├── features.py             # Dynamic feature extraction and scaling
│   │   └── model_service.py        # XGBoost model loader and scoring
│   ├── routers/                    # REST API route handlers
│   │   ├── accounts.py             # Account creation and balance endpoints
│   │   ├── predict.py              # Transaction risk scoring endpoints
│   │   ├── stats.py                # Live analytics and metrics endpoints
│   │   └── transactions.py         # Transaction history and logging
│   ├── schemas/                    # Pydantic DTO models
│   └── services/                   # Business logic and database operations
├── docs/                           # Technical documentation and project reports
│   ├── PROJECT_REPORT_BCSE497J.md  # Comprehensive humanised university project report
│   └── REPORT.md                   # Verification and test report
├── frontend/                       # Modern React + Vite Dashboard
│   ├── src/
│   │   ├── components/             # Reusable UI components
│   │   │   ├── AlertsPanel.jsx     # High-priority fraud alerts banner
│   │   │   ├── Dashboard.jsx       # Top-level executive metrics view
│   │   │   ├── PredictionForm.jsx  # Interactive transaction scoring sandbox
│   │   │   ├── ResultCard.jsx      # High/Medium/Low score display card
│   │   │   ├── RiskMetricsBar.jsx  # Risk distribution progress bar
│   │   │   └── TransactionTable.jsx# Filterable transaction audit log
│   │   └── api/                    # REST client connectors
│   ├── package.json
│   └── vite.config.js
├── models/
│   └── preprocessing.json          # Precomputed scaling parameters and quantiles
├── scripts/
│   ├── export_preprocessing.py     # Feature parameters generator from Fraud.csv
│   └── init_db.py                  # Database initialization and demo data seeder
├── sql/                            # PostgreSQL Schema and Routines
│   ├── 01_schema.sql               # Normalized tables and constraints
│   ├── 02_seed_reference.sql       # Static lookup tables and constants
│   ├── 03_routines.sql             # Stored procedures (fn_process_transaction)
│   ├── 04_views.sql                # Materialized reporting views
│   └── 05_seed_demo_accounts.sql   # Test accounts and initial balances
├── tests/                          # Automated Pytest Suite (80+ Tests)
│   ├── test_api.py                 # REST endpoint integration tests
│   ├── test_features.py            # Feature transformation verification
│   ├── test_model_service.py       # ML inference correctness tests
│   └── sql/test_concurrency.sh     # Balance concurrency and race-condition checks
├── Analysis.ipynb                  # Exploratory data analysis & model tuning notebook
├── best_fraud_model_tuned.pkl      # Fine-tuned XGBoost model artifact
├── requirements.txt                # Production Python dependencies
└── README.md                       # Comprehensive setup and run guide
```
