# **Agile Product Requirements Document (PRD)**

## **Document Information**

**Document Title:** GPTPortal - Product Requirements Document  
**Author:** Grace Hoang  
**Creation Date:** 03/04/2025  
**Last Updated:** 03/04/2025  
**Version:** 1.0.0  
**Status:** Draft

*Note: This is a living document that will evolve as we learn more through development iterations.*

---

## **1\. Product Vision and Goals**

### **1.1 Problem Statement**

Users currently struggle with accessing multiple LLMs due to costly subscriptions and lack of interoperability between AI models. GPTPortal aims to solve this by providing a seamless, pay-as-you-go platform where users can query different and multiple LLMs without committing to multiple subscriptions.

### **1.2 Product Vision**

GPTPortal will be the go-to platform for users who want seamless access to multiple LLMs through a micropayment model, allowing them to maximize flexibility and minimize costs.

### **1.3 Business Objectives**

* Enable users to query multiple LLMs without multiple subscriptions.
* Implement Moneta's micropayment system to ensure cost efficiency.
* Provide an intuitive and user-friendly interface.
* Differentiate GPTPortal from existing AI access solutions through superior pricing and ease of use.

### **1.4 Target Users**

* AI enthusiasts and researchers looking for comparative model analysis.
* Business professionals requiring AI-generated insights.
* Developers integrating multiple AI responses into their workflows.
* Students and academics leveraging AI for research and study.

---

## **2\. Product Backlog Overview**

### **2.1 MVP Definition**

**MVP Includes:**

* User authentication via mPass
* Ability to access and chat with all LLMs
* Micropayment processing for queries
* Query history and management
* User dashboard with spending insights
* Ability to obtain user feedback  
* Website analytics

**Post-MVP:**

* Advanced personalization of pricing plans.  
* Understanding of mode-of-use and user persona  
* Dynamic pricing based on user behavior.  
* Multi-step onboarding for selecting optimal LLMs.  
* A/B Testing

### **2.2 Epic Summary**

| Epic | Description | Priority |
| :---- | :---- | :---- |
| User Authentication | Secure login via MPass | Must |
| Model Selection | Users can select from all LLMs | Must |
| Query and response | Users can query and GPTPortal will respond | Must |
| Payment System | Micropayment processing with each query | Must |
| Query Cost and Budget Updating | Calculates token and $ cost of each query and update ledger database.  Updates UI to show remaining budget.  | Must |
| User Feedback | Users can give feedback on their experience | Should |
| Analytics | Website analytics generated to measure success | Should |

### **2.3 User Stories**

#### **2.3.1 Authentication & Access**

| ID | User Story | Priority | Notes |
| :---- | :---- | :---- | :---- |
| US-1.1 | As a user, I want to log in to GPTPortal with mPass so that I can start using the service. | High | Secure authentication is required. |

#### **2.3.2 Model Selection**

| ID | User Story | Priority | Notes |
| :---- | :---- | :---- | :---- |
| US-2.1 | As a user, I want to select from multiple LLMs to run my query so that I can compare responses. | High | Must support all LLMs at launch. |
| US-2.2 | As a user, I want to understand the cost and the benefits of each LLM that I am selecting. | High | Transparent pricing communication |

#### **2.3.3 Query and Response**

| ID | User Story | Priority | Notes |
| :---- | :---- | :---- | :---- |
| US-3.1 | As a user, I want to input a query and receive a response from my selected LLM(s) so that I can get relevant information. | High | Core functionality of the platform. |
| US-3.2 | As a user, I want to receive responses in a clear and readable format so that I can easily understand the AI output. I want to see the responses as a grid of up to 4 expandable columns and n rows. | High | Formatting should be user-friendly. |
| US-3.3 | As a user, I want to be able to modify my query and get updated responses so that I can refine my results. | High | Improves usability and user experience. |

#### **2.3.4 Payment System**

| ID | User Story | Priority | Notes |
| :---- | :---- | :---- | :---- |
| US-4.1 | As a user, I want to have an initial trial to test out the service before I decide to pay | High | User must be able to try without cost |
| US-4.2 | As a user, I want to select from different budget plans so that I can pay for AI queries. | High | Supports multiple budget payment methods. |
| US-4.3 | As a user, I want to be able to update my payment plan | Medium | Changing payment plan capability |

#### **2.3.5 Query Cost and Budget Updating**

| ID | User Story | Priority | Notes |
| :---- | :---- | :---- | :---- |
| US-5.1 | As a user, I want my remaining budget to be updated after each query so that I can track my available balance. | High | Ensures transparency in spending. |
| US-5.2 | As a user, I want to be able to view my previous queries and their costs to manage my spending effectively via a ledger | High | Ensure transparency in spending |
| US-5.3 | As a user, I want to view my previous sessions/queries so that I can reference past conversations. | Medium | Query history is stored securely. |
| US-5.4 | As an admin, I want to take into account the 20% margin into the pricing so that GPTPortal can support its operations | High | Debate between transparency and user expectation |
| US-5.5 | As a user, I want to delete past queries so that I can manage my data privacy. | Low | Users should have control over their data. |

#### **2.3.6 User Feedback**

| ID | User Story | Priority | Notes |
| :---- | :---- | :---- | :---- |
| US-6.1 | As a user, I want to provide feedback on my experience so that the service can improve. | Medium | Feedback collection integrated into UI. |

#### **2.3.7 Website Analytics**

| ID | User Story | Priority | Notes |
| :---- | :---- | :---- | :---- |
| US-7.1 | As an admin, I want to track user behavior on the platform so that I can improve the product, the user experience, and add features. | High | Data collection complies with privacy laws. |

## **3\. Non-functional requirements (Engineering Team input)**

### **3.1 Performance**

* AI response time should be under 3 seconds.

### **3.2 Security & Compliance**

* User data should be encrypted at rest and in transit.

### **3.3 Scalability**

* Platform should support up to 100,000 concurrent users.

### **3.4 Accessibility**

* Meets WCAG 2.1 AA standards.

### **3.5 Browser/Device Support**

* Chrome, Firefox, Edge, Safari

---

## **4\. Technical Considerations (Engineering Team input)**

### **4.1 System Dependencies**

* mPass for authentication and payment  
* Company  
  * Standard model  
  * Value model  
  * Pro model  
* OpenAI  
  * GPT 4o  
  * GPT 4o-mini  
  * GPT-4.5  
* Google  
  * Gemini 2.0 Flash  
  * Gemini 2.0 Flash Lite  
  * Gemini 2.0 Pro  
* Anthropic  
  * Claude 3.7 Sonnet  
  * Claude 3.5 Haiku  
  * Claude 3 Opus  
* META  
  * Llama 3.1 70B (META)  
  * Llama 3.2 11B  
  * Llama 3.1 405B  
* Perplexity  
  * Sonar Pro  
  * Sonar  
  * Sonar Reasoning Pro  
* DeepSeek  
  * DeepSeek V3  
  * DeepSeek-R1  
* XAI  
  * Grok 2-Vision (XAI)  
  * Grok Vision Beta

### **4.2 Architecture Overview**

* Microservices-based backend

### **4.3 Data Requirements**

* User profiles, transaction history, and query logs

---

## **5\. Assumptions and Constraints**

### **5.1 Assumptions**

* Users are comfortable with micropayments.
* Partnered LLMs provide API access without major delays.

### **5.2 Constraints**

* LLM API availability and pricing fluctuations.
* Compliance with payment processor regulations.
* Scalability for increased query demand.

---

## **6\. Success Metrics**

| Event | Description | Purpose |
| :---- | :---- | :---- |
| User adoption | Number of new users per month | Measures adoption |
| Query volume | Number of AI queries processed | Indicates engagement |
| Payment transactions | Total revenue from micropayments | Evaluates monetization success |
| User conversion | Number of users who go from trial to payment plan | Measures adoption |
| Top LLMs Used | Which LLMs are used most for which use cases | Help drive next version when we add query-mode feature |
| Average session duration | How long each session is lasting | Measures user engagement |
| Churn | How many users stop using the service | Measures user dissatisfaction |
| Number of times users configure LLMs | The amount of users that want to change/learn about LLM offerings | Understand usage behavior |
| Number of times users check query budget | The amount of users that want to track their spending | Helps us generate additional budget plans/pricing plans |
| Average histograms/Average revenue per user | The amount of money we make per user | Helps us understand different user usages |

---

## **7\. Appendix**

### **7.1 Glossary**

| Term | Definition |
| :---- | :---- |
| mPass | A secure authentication method. |
| LLM | Large Language Model, an AI system capable of generating text. |
| Micropayments | Small transactions used to pay for individual queries. |

### **7.2 References**

* OpenAI API Documentation