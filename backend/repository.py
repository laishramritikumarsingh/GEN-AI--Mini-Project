from pathlib import Path
from tempfile import mkdtemp
from urllib.parse import urlparse
import shutil

from git import Repo, GitCommandError


class RepositoryError(ValueError):
    """Expected repository validation or cloning error."""


def validate_github_url(repo_url: str) -> str:
    """Validate a public GitHub repository URL and return its normalized URL."""
    if not isinstance(repo_url, str) or not repo_url.strip():
        raise RepositoryError("Enter a GitHub repository URL.")

    raw = repo_url.strip()
    parsed = urlparse(raw)

    if parsed.scheme != "https" or parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise RepositoryError("Use a public GitHub URL like https://github.com/owner/repository.")

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        raise RepositoryError(
            "Enter a repository homepage URL, not a file, folder, branch, or pull-request URL."
        )

    owner, repo_name = parts
    if not owner or not repo_name or any(ch in owner + repo_name for ch in "?#"):
        raise RepositoryError("That GitHub repository URL is not valid.")

    repo_name = repo_name.removesuffix(".git")
    if not repo_name:
        raise RepositoryError("The repository name is missing.")

    return f"https://github.com/{owner}/{repo_name}.git"


def clone_repository(repo_url: str) -> str:
    """Clone a public GitHub repository into a temporary directory."""
    normalized_url = validate_github_url(repo_url)
    destination = Path(mkdtemp(prefix="repolens_"))
    try:
        Repo.clone_from(
            normalized_url,
            str(destination / "repo"),
            depth=1,
            single_branch=True,
            no_checkout=False,
            multi_options=["--filter=blob:none"],
        )
        return str(destination / "repo")
    except (GitCommandError, OSError) as exc:
        shutil.rmtree(destination, ignore_errors=True)
        message = str(exc).lower()
        if "not found" in message or "repository not found" in message:
            raise RepositoryError("Repository not found or it is private. Use a public repository.") from exc
        if "could not resolve host" in message or "network" in message:
            raise RepositoryError("Could not reach GitHub. Check your internet connection and try again.") from exc
        raise RepositoryError("Git could not clone this repository. Check the URL and try again.") from exc


def cleanup_repository(repo_path: str) -> None:
    """Remove the temporary clone and its parent temporary directory."""
    if not repo_path:
        return
    path = Path(repo_path).resolve()
    # Only delete directories created by this application's temporary clone flow.
    if path.name == "repo" and path.parent.name.startswith("repolens_"):
        shutil.rmtree(path.parent, ignore_errors=True)
