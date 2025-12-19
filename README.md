# 🕵️‍♂️ Insight: Autonomous Research Agent

> **A "Self-Correcting" AI Agent that plans research strategies, scrapes the web, and performs Gap Analysis to iteratively improve its own reports.**

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![LangChain](https://img.shields.io/badge/LangChain-Enabled-orange)
![Groq](https://img.shields.io/badge/Groq-Llama%203.3-purple)
![Tavily](https://img.shields.io/badge/Tools-Tavily%20Search-green)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red)

## 📖 Overview
**Insight** is not a chatbot. It is an **Agentic System** designed to perform deep research autonomously.

Unlike standard LLM wrappers, this project implements a **Cognitive Architecture** (Plan $\rightarrow$ Act $\rightarrow$ Critique $\rightarrow$ Refine). It uses a "Critic" node to evaluate its own draft reports for missing information (Gap Analysis) and autonomously triggers follow-up searches until the quality threshold is met.

## 🚀 Key Features

### 🧠 1. Metacognitive "Gap Analysis"
* The agent reads its own draft and asks: *"Did I actually answer the user's question?"*
* If specific data (dates, numbers, names) is missing, it rejects the draft and generates a **new search strategy** to find that specific missing piece.

### ⚡ 2. Hyper-Fast Inference (Groq)
* Powered by **Llama-3.3-70b-Versatile** running on Groq's LPUs (Language Processing Units).
* Achieves sub-second reasoning speeds, allowing for multiple "thought loops" without keeping the user waiting.

### 🌍 3. Live Web Access (Tavily)
* Uses the **Tavily Search API**, a search engine optimized for AI agents.
* Scrapes, indexes, and extracts clean text from real-time sources (bypassing the training data cutoff).

### 🔍 4. Transparent "Thought Process" UI
* The Streamlit dashboard visualizes the agent's internal state.
* Users can see exactly when the agent is **Planning**, **Searching**, or **Critiquing** itself.

---

## 🛠️ Tech Stack

* **Orchestration:** LangChain / Custom State Loop
* **LLM Engine:** Llama-3.3-70b-Versatile (via Groq Cloud)
* **Search Tool:** Tavily Search API
* **Frontend:** Streamlit
* **Environment:** Python 3.10+

---

## 📂 Project Structure

```bash
├── app.py               # Main Application (Streamlit UI + Agent Logic)
├── requirements.txt     # Dependencies
├── .env                 # API Keys (Ignored in Git)
└── README.md            # Documentation
