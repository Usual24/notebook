from __future__ import annotations

import httpx

from .config import Settings


class LocalLLM:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_answer(self, question: str, contexts: list[dict]) -> str:
        context_blocks = []
        for i, item in enumerate(contexts[: self.settings.max_context_chunks], start=1):
            meta = item.get("meta", {})
            src = meta.get("source_ref", "unknown")
            title = meta.get("title", "untitled")
            context_blocks.append(f"[Context {i}] title={title} source={src}\n{item['chunk']}")

        context_text = "\n\n".join(context_blocks) if context_blocks else "(no context found)"
        system_prompt = (
            "당신은 로컬 NotebookLM 스타일 어시스턴트입니다. "
            "반드시 제공된 문맥에 근거해 답하고, 근거가 약하면 모른다고 말하세요."
        )
        user_prompt = f"질문:\n{question}\n\n문맥:\n{context_text}"

        payload = {
            "model": self.settings.lmstudio_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        url = f"{self.settings.lmstudio_base_url.rstrip('/')}" + "/chat/completions"
        with httpx.Client(timeout=120) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]
