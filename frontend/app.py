import sys
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from backend.repository import clone_repository, cleanup_repository, RepositoryError
from backend.code_processor import build_repository_context
from backend.llm import explain_repository

st.set_page_config(page_title="RepoLens AI", page_icon="🔎", layout="wide")

st.markdown("""
<style>
    .block-container {max-width: 1100px; padding-top: 2rem; padding-bottom: 3rem;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 16px; background: linear-gradient(120deg, #14213d, #253b63); color: white; margin-bottom: 1.2rem;}
    .hero h1 {color: white; margin: 0;}
    .hero p {color: #dbeafe; margin-bottom: 0;}
    div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.25); padding: 12px; border-radius: 12px;}
</style>
<div class="hero">
<h1>🔎 RepoLens AI</h1>
<p>Local GitHub Repository Code Explainer · Understand a codebase in simple language</p>
</div>
""", unsafe_allow_html=True)

st.write("Paste a **public GitHub repository URL**. RepoLens AI scans selected files and asks a Qwen language model to explain the project.")
repo_url = st.text_input(
    "GitHub repository URL",
    placeholder="https://github.com/psf/requests",
    help="Use the repository homepage URL, not a link to a specific file or branch.",
)
analyze = st.button("Analyze Repository", type="primary", use_container_width=False)

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if analyze:
    st.session_state.analysis_result = None
    repo_path = None
    try:
        parsed = urlparse(repo_url.strip())
        if parsed.scheme != "https" or parsed.netloc.lower() not in {"github.com", "www.github.com"}:
            raise RepositoryError("Enter a valid public GitHub repository URL.")
        with st.spinner("Cloning repository and selecting useful files..."):
            repo_path = clone_repository(repo_url)
            context = build_repository_context(repo_path)
        with st.spinner("Asking the AI model to explain the code... This may take a few minutes on first run."):
            result = explain_repository(context)
        st.session_state.analysis_result = {
            "repo_url": repo_url.strip(),
            "context": context,
            "result": result,
        }
        st.success("Repository analysis completed.")
    except (RepositoryError, ValueError) as exc:
        st.error(str(exc))
    except RuntimeError as exc:
        st.error(str(exc))
    except Exception:
        st.error("Something went wrong while analyzing this repository. Check the URL, internet connection, and model setup.")
    finally:
        if repo_path:
            cleanup_repository(repo_path)

data = st.session_state.analysis_result
if data:
    context = data["context"]
    result = data["result"]
    st.markdown(f"## 📦 {context['repository_name']}")
    st.caption(data["repo_url"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Files discovered", context["file_count"])
    c2.metric("Files analyzed", context["analyzed_file_count"])
    c3.metric("AI provider", result["provider"])
    st.caption(f"Model: `{result['model']}`")

    left, right = st.columns([1, 2])
    with left:
        st.markdown("### Important files")
        for filename in context["important_files"]:
            st.markdown(f"- `{filename}`")
        with st.expander("Repository structure"):
            st.code("\n".join(context["structure"]) or "No structure available.", language="text")
    with right:
        st.markdown("### 🧠 AI-generated explanation")
        st.markdown(result["explanation"])
        st.download_button(
            "Download explanation (.md)",
            data=result["explanation"],
            file_name=f"{context['repository_name']}_explanation.md",
            mime="text/markdown",
        )
else:
    st.info("Ready when you are. Try a small public repository first for the fastest demo.")
    with st.expander("What happens when I click Analyze?"):
        st.markdown("""
1. Validate the GitHub repository URL.
2. Clone the repository into a temporary folder.
3. Ignore generated folders and select useful source/documentation files.
4. Build a size-limited repository context.
5. Try local Ollama first; if unavailable, use Qwen through Hugging Face Transformers.
6. Show the generated explanation and remove the temporary clone.
""")

st.divider()
st.caption("College mini-project demo · Only public repositories are supported. Large repositories may be truncated to fit the model context.")
