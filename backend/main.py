from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend.repository import clone_repository, cleanup_repository, RepositoryError
from backend.code_processor import build_repository_context
from backend.llm import explain_repository

app = FastAPI(title="RepoLens AI API", version="1.0.0")


class ExplainRequest(BaseModel):
    repo_url: str = Field(..., min_length=1, description="Public GitHub repository URL")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/explain")
def explain(request: ExplainRequest):
    repo_path = None
    try:
        repo_path = clone_repository(request.repo_url)
        context = build_repository_context(repo_path)
        result = explain_repository(context)
        return {
            "repository": context["repository_name"],
            "files_discovered": context["file_count"],
            "files_analyzed": context["analyzed_file_count"],
            "important_files": context["important_files"],
            "provider": result["provider"],
            "model": result["model"],
            "explanation": result["explanation"],
        }
    except (RepositoryError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Analysis failed. Please try another public repository.") from exc
    finally:
        if repo_path:
            cleanup_repository(repo_path)
