# 🏥 Post-Discharge Medical AI Assistant (POC)

**A Multi-Agent Generative AI System for Post-Discharge Patient Care**

This repository contains the Proof of Concept (POC) for a **Post-Discharge Medical AI Assistant**, developed as part of the **DataSmith AI – GenAI Intern Assignment**.  
The project demonstrates the integration of **LangChain**, **Groq LLMs**, **Retrieval-Augmented Generation (RAG)**, and **multi-agent orchestration** using **Streamlit** and **FastAPI**.

---

## 🚀 Overview

The **Post-Discharge Medical AI Assistant** assists patients after hospital discharge by:

- Managing patient records and discharge summaries  
- Answering follow-up and symptom-related queries  
- Routing medical questions between AI agents  
- Generating medically-grounded responses using **RAG** over nephrology references  
- Logging and tracking all agent interactions  

---

## 🧠 System Architecture

This system follows a **multi-agent architecture** built with **LangChain** and **Groq** for efficient LLM-based reasoning.

### 🧾 1. Receptionist Agent
- Greets patients and collects their name.  
- Retrieves their discharge summary from the local database (JSON/SQLite).  
- Handles general or administrative queries.  
- Routes medical or complex questions to the **Clinical Agent**.

### ⚕️ 2. Clinical AI Agent
- Specializes in nephrology-related queries.  
- Uses **RAG (Retrieval-Augmented Generation)** to fetch relevant reference chunks.  
- Integrates a **web search fallback** (Tavily / DuckDuckGo) for out-of-scope topics.  
- Provides **contextual and cited medical responses**.  

---

## 🧩 Core Features

| Feature | Description |
|----------|-------------|
| **LangChain + Groq Integration** | Orchestrates multi-agent LLM workflows using Groq for faster inference. |
| **Multi-Agent System** | Receptionist and Clinical agents coordinate through LangChain agent framework. |
| **RAG Pipeline** | Uses vector embeddings (ChromaDB) for semantic retrieval over nephrology data. |
| **Web Search Tool** | Fetches the latest information when not found in internal documents. |
| **Patient Data Tool** | Retrieves discharge data securely from JSON/SQLite. |
| **Comprehensive Logging** | Logs every agent handoff, tool call, and response. |
| **Streamlit Frontend** | Simple chat interface for patient interaction. |
| **FastAPI Backend** | Handles API orchestration and backend communication. |

---

## 🗂️ Project Structure

Post-Discharge-Medical-AI-Assistant/
│
├── data/
│ ├── patients/ # 25+ dummy discharge reports (JSON)
│ ├── reference/ # Nephrology reference materials (PDF/Text)
│ └── db.sqlite # Optional SQLite DB for patient data
│
├── agents/
│ ├── receptionist_agent.py # Handles greetings, routing, and admin queries
│ ├── clinical_agent.py # Uses RAG for medical responses
│
├── tools/
│ ├── rag_pipeline.py # Chunking, embeddings, retrieval, and generation
│ ├── web_search_tool.py # External search for latest nephrology info
│ ├── patient_data_tool.py # Fetches discharge info by patient name
│ ├── logger.py # Logs all system events and interactions
│
├── backend/
│ ├── api.py # FastAPI routes and endpoints
│ └── utils.py # Helper functions for agent orchestration
│
├── ui/
│ ├── app.py # Streamlit-based user chat interface
│
├── requirements.txt
├── README.md
└── LICENSE

yaml
Copy code

---

## ⚙️ Setup & Installation

### 1. Clone Repository
```bash
git clone https://github.com/Shaileja06/Post-Discharge-Medical-AI-Assistant.git
cd Post-Discharge-Medical-AI-Assistant
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate      # (Linux/Mac)
venv\Scripts\activate         # (Windows)
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Variables
Create a `.env` file in the root directory with:
```ini
OPENAI_API_KEY=your_openai_api_key
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key  # optional
```

### 5. Data Setup
- Add 25+ dummy discharge reports to `data/patients/`
- Place nephrology reference PDF/text in `data/reference/`
- Optionally initialize `db.sqlite` with patient records

### 6. Run Application
```bash
# Streamlit Frontend
streamlit run ui/app.py

# FastAPI Backend
uvicorn backend.api:app --reload
```

## 🧮 Example Workflow

### Step 1 — Initial Interaction
```
System: Hello! I'm your post-discharge care assistant. What's your name?
User: John Smith
Receptionist: Hi John! I found your discharge report from Jan 15th for Chronic Kidney Disease. 
              How are you feeling today?
```

### Step 2 — Medical Query Routing
```
User: I'm having swelling in my legs. Should I be worried?
Receptionist: This sounds like a medical concern. Let me connect you with our Clinical Agent.
Clinical Agent: Based on your CKD diagnosis and nephrology reference, leg swelling may 
                indicate fluid retention...
```

### Step 3 — Web Search Fallback
```
User: What's the latest research on SGLT2 inhibitors for kidney disease?
Clinical Agent: This information requires recent data. Let me look that up... 
                [Web search results with citations]
```

## 📘 Tech Stack

| Component | Technology |
|-----------|-----------|
| **LLM Provider** | Groq (LLM inference via LangChain) |
| **Framework** | LangChain |
| **Frontend** | Streamlit |
| **Backend** | FastAPI |
| **Vector Database** | ChromaDB |
| **Embeddings** | SentenceTransformers / HuggingFace |
| **Data Storage** | SQLite / JSON |
| **Web Search API** | Tavily / DuckDuckGo Search |
| **Logging** | Python logging module |
| **Environment** | Python 3.10+ |

## 🧱 Architecture Justification

| Component | Choice | Reason |
|-----------|--------|--------|
| **LLM** | Groq | Low-latency inference with high reasoning performance |
| **Framework** | LangChain | Simplifies agent orchestration and tool integration |
| **Vector DB** | ChromaDB | Lightweight and fast for RAG retrieval |
| **Frontend** | Streamlit | Quick and interactive UI for demo purposes |
| **Backend** | FastAPI | Async API layer for modular and scalable architecture |
| **Search Tool** | Tavily API | Ensures access to latest medical knowledge |
| **Storage** | JSON + SQLite | Simple yet effective data retrieval system |
| **Logging** | Custom Python logs | Provides end-to-end traceability |

## 🩺 Disclaimer

> ⚠️ **Disclaimer:**  
> This system is for **educational and demonstrative purposes only**.  
> It is **not a medical diagnostic or treatment tool**.  
> Always consult a **licensed healthcare professional** for real medical advice.

## ✅ Deliverables Checklist

- ✅ 25+ dummy patient reports
- ✅ Nephrology reference material processed
- ✅ Receptionist & Clinical AI Agents implemented
- ✅ RAG pipeline with vector search
- ✅ Web search fallback integrated
- ✅ Comprehensive logging
- ✅ Streamlit UI and FastAPI backend
- ✅ Clean, modular, and documented code
- ✅ Architecture justification & report

