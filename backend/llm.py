import os
from functools import lru_cache

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
HF_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"

SYSTEM_PROMPT = """You are a software project explainer. Analyze the provided GitHub repository context
and explain the project in simple language suitable for a college student.
Only describe functionality supported by the provided repository context. Do not invent features.
Do not reproduce large sections of source code. Explain the actual project.
Return concise Markdown with these headings:
1. Project Overview
2. Main Features
3. Project Structure
4. How the Application Works
5. Technologies Used
6. Important Code Components
7. Simple Summary
Mention uncertainty when the supplied files do not establish something."""


def _make_prompt(repository_context: dict) -> str:
    structure = "\n".join(repository_context.get("structure", []))
    files = "\n".join(repository_context.get("important_files", []))
    return f"""{SYSTEM_PROMPT}

Repository name: {repository_context.get('repository_name', 'Unknown')}
Files discovered: {repository_context.get('file_count', 0)}
Files included in analysis:
{files}

Repository structure (first files):
{structure}

Repository file contents:
{repository_context.get('context_text', '')}
"""


def _ollama_generate(prompt: str) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096, "num_predict": 900},
        },
        timeout=(5, 180),
    )
    response.raise_for_status()
    text = response.json().get("response", "").strip()
    if not text:
        raise RuntimeError("Ollama returned an empty explanation.")
    return text


def _load_hf_model():
    # Import Streamlit only when the cloud/local Transformers path is needed.
    import streamlit as st
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    @st.cache_resource(show_spinner="Loading Qwen model (first run can take a few minutes)...")
    def load_model(model_name: str):
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True,
        )
        model.eval()
        return tokenizer, model

    return load_model(HF_MODEL)


def _hf_generate(prompt: str) -> str:
    import torch

    tokenizer, model = _load_hf_model()
    messages = [
        {"role": "system", "content": "You explain software repositories accurately and simply."},
        {"role": "user", "content": prompt},
    ]
    if getattr(tokenizer, "chat_template", None):
        input_text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    else:
        input_text = prompt
    inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=6000)
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=900,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    generated = output[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(generated, skip_special_tokens=True).strip()
    if not text:
        raise RuntimeError("The Hugging Face model returned an empty explanation.")
    return text


def explain_repository(repository_context: dict) -> dict:
    """Try local Ollama first, then use the Hugging Face Transformers model."""
    prompt = _make_prompt(repository_context)
    try:
        explanation = _ollama_generate(prompt)
        return {"explanation": explanation, "model": OLLAMA_MODEL, "provider": "Ollama"}
    except (requests.RequestException, ValueError, RuntimeError):
        pass

    try:
        explanation = _hf_generate(prompt)
        return {"explanation": explanation, "model": HF_MODEL, "provider": "Hugging Face Transformers"}
    except Exception as exc:
        # Avoid returning internal stack traces or sensitive runtime details to the UI.
        raise RuntimeError(
            "The AI model could not generate an explanation. Start Ollama with the required model, "
            "or check the internet connection and available memory for the Hugging Face model."
        ) from exc
