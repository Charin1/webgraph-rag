# WebGraph RAG - A RAG System

![status](https://img.shields.io/badge/status-in_development-yellow)

⚠️ This project is under active development and is **not production-ready**.

This repository provides a complete, production-ready implementation of a Retrieval-Augmented Generation (RAG) system. It is designed to crawl modern websites, build a knowledge graph, and serve a sophisticated chat interface.

The system is built with a robust, asynchronous backend using FastAPI and a modern, interactive frontend using React. It is architected for stability and performance, with all heavy AI models pre-loaded at startup to prevent deadlocks and timeouts.

### Key Features:

*   **Robust Web Crawling:** Uses a Playwright-based crawler capable of rendering JavaScript-heavy sites, with configurable depth and page limits.
*   **Knowledge Graph:** Stores website structure and metadata in a Neo4j graph database.
*   **High-Performance Vector Store:** Uses FAISS for vector search with metadata stored in Redis for fast, non-blocking access.
*   **Advanced RAG Pipeline:** Implements a hybrid retrieval strategy followed by a Cross-Encoder reranker for high-quality, relevant results.
*   **Cloud & Local LLMs:** Configured for Google GenAI (Gemini Flash) by default, with support for OpenAI and local Llama.cpp models.
*   **Interactive UI:** A modern React frontend inspired by NotebookLM, featuring a real-time ingestion dashboard and a responsive chat interface.
*   **Production-Ready:** Includes a full Docker Compose setup, Prometheus monitoring, Grafana dashboards, and a robust architecture that solves common deadlocking issues on macOS.

---

## Quickstart - Prerequisites

*   Docker and Docker Compose (v2+) installed.
*   Git.
*   **For Local Development (Optional):**
    *   A stable Python version like **Python 3.11**. (Using newer versions like 3.12/3.13 may cause segmentation faults with the AI libraries on macOS).
    *   Node.js 18+.

---

## 1) Run with Docker Compose (Highly Recommended)

This is the most stable and reliable way to run the entire application. It avoids all platform-specific issues.

1.  **Set User Permissions:** From your project's root directory, run this command once per terminal session. This ensures files created by Docker have the correct ownership on your machine.
    ```bash
    export UID=$(id -u)
    export GID=$(id -g)
    ```

2.  **Build and Run:**
    ```bash
    docker-compose up --build
    ```
    The first build will take several minutes as it downloads the AI models and browser binaries. Subsequent starts will be much faster.

3.  **Access the Services:**
    *   **Frontend UI:** http://localhost:5173
    *   **Backend API Docs:** http://localhost:8000/docs
    *   **Neo4j Browser:** http://localhost:7474 (user: `neo4j`, pass: `password`)
    *   **Prometheus:** http://localhost:9090
    *   **Grafana:** http://localhost:3001 (user: `admin`, pass: `admin`)

---

## 2) Run Locally (For Active Backend Development)

This method is for when you are actively editing the Python code and need instant feedback.

### CRITICAL NOTE FOR MACOS USERS

Running this stack locally on macOS can be unstable due to low-level conflicts between the Uvicorn web server and the AI libraries. You may encounter **segmentation faults** or **application hangs**. The following steps are the definitive solution.

1.  **Start Databases:** It is still recommended to run the databases in Docker for simplicity.
    ```bash
    docker run -d --name redis-dev -p 6379:6379 redis:7
    docker run -d --name neo4j-dev -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5.12
    ```

2.  **Setup Python Environment:**
    *   Navigate to the `backend/` directory.
    *   **Use a stable Python version.** Create the virtual environment with: `python3.11 -m venv .venv`
    *   Activate it: `source .venv/bin/activate`
    *   Install dependencies: `pip install -r requirements.txt`

3.  **Configure `.env` file:** Create a `backend/.env` file with your API keys and local database connections. A full example is in the repository. Ensure `REDIS_URL` is set:
    ```
    REDIS_URL=redis://localhost:6379
    GOOGLE_API_KEY=your_google_api_key_here
    # etc.
    ```

4.  **Run the Backend Server (Choose One Command):**
    *   **For Active Coding (with auto-reload):**
        ```bash
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ```
    *   **For Stable Testing (NO auto-reload):** This is the most stable command and prevents deadlocks.
        ```bash
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
        ```

5.  **Run the Frontend Server:**
    *   In a new terminal, navigate to `frontend/`.
    *   Run `npm install` and then `npm run dev`.

---

## 3) Basic Usage

1.  **Add a Source:** Navigate to the **Sources** page in the UI. Enter a URL, set your crawl limits, and click "Add Source". Watch the real-time progress as the site is ingested.
2.  **Chat with your Source:** Navigate to the **Chat** page. Ask a question relevant to the content you just ingested.

---

## 4) Troubleshooting

*   **Fatal Python error: Segmentation fault (macOS):** Your local Python environment is unstable. The definitive fix is to run the backend in Docker as described in Method 1. If you must run locally, you must destroy your `.venv` (`rm -rf .venv`) and recreate it with a stable Python version like 3.11.
*   **`socket hang up` or `ECONNREFUSED`:** The backend server is not running or is not reachable from the frontend. Ensure the backend is running (either via Docker or locally) and that your `.env` files are configured correctly.
*   **`attempt to write a readonly database`:** A file permission issue with the vector store files. This is solved by using the `user: "${UID}:${GID}"` directive in the `docker-compose.yml` file. If it happens locally, you may need to manually `sudo chown your_username backend/faiss.*`.
*   **Crawl finds 0 pages:** The target website is likely JavaScript-heavy or has strong anti-bot measures. The Playwright crawler is designed to handle this, but ensure your Docker image was built correctly.

## Roadmap / Status
This project is still in its early stages. Expect breaking changes.