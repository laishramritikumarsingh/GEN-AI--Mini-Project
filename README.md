# Local GitHub Repository Code Explainer

**RepoLens AI** is a college mini-project that takes a public GitHub repository URL, selects useful files, and uses a Qwen 2.5 0.5B language model to generate a simple explanation of the codebase.

## 1. Project Overview

Many students find it difficult to understand an unfamiliar code repository. RepoLens AI reduces the initial learning effort by summarizing the project structure, technologies, important files, workflow, and main purpose using an LLM.

## 2. Problem Statement

Understanding an existing codebase takes time, especially for beginners who do not know where the entry point or important modules are located.

## 3. Objective

Build a simple web application that analyzes a public GitHub repository and produces an explanation based on the repository's actual README and source files. Explanations are generated dynamically by the model, not stored as hard-coded answers.

## 4. Features

- Public GitHub repository URL validation.
- Shallow clone into a temporary folder.
- Ignores common generated/dependency folders and many test files.
- Prioritizes README, entry-point files, dependency files, and source code.
- Bounds the number and size of files sent to the model.
- Tries local Ollama first and falls back to Hugging Face Transformers.
- Streamlit UI with metrics, important-file list, repository structure, and downloadable Markdown explanation.
- FastAPI endpoints for health checks and repository explanation.
- Removes the temporary repository after processing, including when an error occurs.

## 5. Architecture

```text
GitHub Repository
       ↓
Repository URL Input
       ↓
Repository Cloning
       ↓
Code Processing
       ↓
Relevant File Selection
       ↓
Repository Context
       ↓
Qwen 2.5 0.5B (Ollama locally / Transformers online)
       ↓
Generated Explanation
       ↓
Streamlit UI
```

## 6. Technology Stack

- **Python:** main programming language.
- **Streamlit:** interactive web interface.
- **GitPython:** clones public Git repositories.
- **FastAPI / Uvicorn / Pydantic:** optional local API.
- **Requests:** calls the Ollama HTTP endpoint.
- **Ollama:** runs `qwen2.5:0.5b` locally.
- **Hugging Face Transformers:** loads `Qwen/Qwen2.5-0.5B-Instruct` when Ollama is unavailable.
- **PyTorch / Accelerate / Safetensors:** model inference and model-file support.

## 7. Project Structure

```text
github-code-explainer/
├── backend/
│   ├── __init__.py
│   ├── repository.py
│   ├── code_processor.py
│   ├── llm.py
│   └── main.py
├── frontend/
│   └── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── run_backend.bat
└── run_frontend.bat
```

## 8. How It Works

1. The user enters a public repository URL.
2. `repository.py` validates the URL and clones it into a temporary directory.
3. `code_processor.py` ignores common generated folders, prioritizes relevant files, and limits the context size.
4. `llm.py` builds a prompt containing the repository's real file contents.
5. The app tries Ollama first. If it is unavailable, it tries Hugging Face Transformers.
6. Streamlit displays the generated Markdown and metadata.
7. A `finally` block removes the temporary clone.

The model only sees the files selected by the processor. It may miss functionality in files that were excluded or truncated.

## 9. Local Installation (Windows)

Install **Python 3.10 or newer**, Git for Windows, and a working internet connection.

Open a terminal in the project folder:

```bat
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the UI:

```bat
python -m streamlit run frontend/app.py
```

Or double-click `run_frontend.bat` after installing the dependencies.

## 10. Ollama Setup

1. Install Ollama for Windows from [https://ollama.com](https://ollama.com).
2. Open a terminal and download the model:

```bat
ollama pull qwen2.5:0.5b
```

3. Ensure Ollama is running, then test it:

```bat
ollama run qwen2.5:0.5b
```

4. In another terminal, start RepoLens AI. It tries `http://localhost:11434` first.

Optional environment variables:

```bat
set OLLAMA_URL=http://localhost:11434
set OLLAMA_MODEL=qwen2.5:0.5b
```

If Ollama is not available, the app attempts to load the Hugging Face model locally. That fallback may use significant RAM and require a first-time model download.

## 11. Running the FastAPI Backend

In an activated virtual environment:

```bat
uvicorn backend.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` for the interactive API page.

- `GET /health` returns `{"status": "ok"}`.
- `POST /explain` accepts JSON such as:

```json
{
  "repo_url": "https://github.com/psf/requests"
}
```

The Streamlit app intentionally calls the Python modules directly and does not require this API to be running.

## 12. Streamlit Cloud Deployment

1. Create a GitHub repository and push the complete project.
2. Open [https://share.streamlit.io](https://share.streamlit.io).
3. Create an app and select your repository, branch `main`, and main file path `frontend/app.py`.
4. Deploy.

The frontend adds the project root to `sys.path` before importing `backend`, and `backend/__init__.py` is included. Cloud deployment does not require Ollama or a separately running FastAPI service.

**Resource note:** Streamlit Cloud has memory and execution limits. Loading PyTorch and a Transformers model can exceed available resources or take several minutes. If that happens, the app will show a friendly error; use a supported deployment with more memory or run the app locally with Ollama. A 0.5B model is small compared with larger LLMs, but it is not guaranteed to fit every free cloud environment.

## 13. Example Usage

Try a small public repository, for example `https://github.com/psf/requests`. Paste the repository homepage URL and click **Analyze Repository**. Do not paste a URL ending in `/blob/...` or `/tree/...`.

## 14. Limitations

- Public GitHub repositories only; private repositories need authentication and are not supported.
- The processor analyzes a limited number of files and truncates large files.
- The model can misunderstand code; verify important claims against the source.
- First-time Hugging Face model loading needs internet access and can be slow.
- Cloud inference depends on the hosting provider's memory and execution limits.
- This is a demonstration project, not a full static-analysis or security-audit tool.

## 15. Future Enhancements

- Support private repositories with secure token handling.
- Add language-aware call graphs and dependency visualization.
- Let users select files for analysis.
- Add tests and repository comparison.
- Use retrieval-augmented generation for very large projects.
- Add an optional hosted inference API for cloud deployments with limited memory.

## Viva Quick Notes

- **Why GitPython?** It lets Python clone and inspect Git repositories.
- **Why Streamlit?** It creates a web UI directly from Python with little frontend code.
- **Why FastAPI?** It exposes the same workflow through HTTP endpoints for API demonstrations.
- **What does Ollama do?** It runs an LLM on the local machine and exposes an HTTP API.
- **What is Qwen 2.5 0.5B?** A compact instruction-tuned language model family with roughly 0.5 billion parameters.
- **Why a small model?** It is more practical for a student demo and uses fewer resources than larger models, though output quality and cloud compatibility are limited.
- **What does Transformers do?** It downloads model/tokenizer files and runs inference in Python.
- **Why `sys.path`?** When the app entry point is inside `frontend/`, explicitly adding the project root helps Python locate the sibling `backend` package on Streamlit Cloud.
- **Why temporary clones?** They avoid keeping downloaded repository content after an analysis and help control disk use.
- **Why limit context?** Small models have limited context windows and long prompts use more memory/time.
