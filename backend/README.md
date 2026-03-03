# CodeAtlas 🚀

**CodeAtlas** is an AI-powered developer assistant designed to help developers write, debug, and understand code using modern AI models. It combines a FastAPI backend with an interactive frontend and supports both local (Ollama) and cloud-based LLMs.

---

## ✨ Features

* 🤖 **AI Code Assistant** – Generate, debug, and optimize code
* 🧠 **Context-Aware Responses** – Understands queries intelligently
* ⚡ **FastAPI Backend** – High-performance API handling
* 💻 **Modern Frontend UI** – Clean and interactive user experience
* 🏠 **Local LLM Support (Ollama)** – No rate limits, privacy-focused
* ☁️ **Hybrid AI Architecture** – Supports both local and API-based models

---

## 🏗️ Project Structure

```
CodeAtlas/
│
├── backend/        # FastAPI backend
│   ├── main.py
│   ├── requirements.txt
│   └── ...
│
├── frontend/       # Frontend (React / UI)
│   ├── src/
│   ├── package.json
│   └── ...
│
├── .gitignore
├── README.md
```

---

## 🚀 Getting Started

### 🔹 Backend Setup (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload
```

---

### 🔹 Frontend Setup

```bash
cd frontend

npm install
npm start
```

---

### 🔹 Ollama Setup (Local AI)

Make sure Ollama is installed and running:

```bash
ollama run gpt-oss:20b
```

---

## 🌐 Deployment

* **Frontend** → Vercel
* **Backend** → Render
* **LLM (Ollama)** → RunPod / Local GPU

---

## 🧠 Tech Stack

* **Backend:** FastAPI, Python
* **Frontend:** React (or your UI framework)
* **AI Models:** Ollama (GPT-OSS), API-based LLMs
* **Deployment:** Vercel, Render

---

## 📌 Future Improvements

* Voice interaction support
* Multi-language support
* Advanced codebase analysis
* Plugin/tool integrations

---

## 🤝 Contributing

Contributions are welcome! Feel free to fork the repo and submit a pull request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

**Abhinav Ashutosh**
