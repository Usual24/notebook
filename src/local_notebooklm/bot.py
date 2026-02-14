from __future__ import annotations

import asyncio
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from .config import Settings
from .ingest import parse_uploaded_file, parse_url, parse_youtube
from .llm import LocalLLM
from .retrieval import LocalRetriever


class NotebookBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        self.settings = settings
        self.retriever = LocalRetriever(settings)
        self.llm = LocalLLM(settings)

    async def setup_hook(self) -> None:
        self.tree.add_command(add_file)
        self.tree.add_command(add_url)
        self.tree.add_command(add_youtube)
        self.tree.add_command(list_sources)
        self.tree.add_command(ask)
        await self.tree.sync()


bot_ref: NotebookBot | None = None


@app_commands.command(name="addfile", description="파일을 업로드해서 지식베이스에 추가")
@app_commands.describe(file="txt/md/pdf 등 텍스트 추출 가능한 파일")
async def add_file(interaction: discord.Interaction, file: discord.Attachment):
    await interaction.response.defer(thinking=True)
    assert bot_ref is not None

    upload_dir = bot_ref.settings.data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / file.filename
    await file.save(save_path)

    def work() -> tuple[str, int]:
        doc = parse_uploaded_file(save_path)
        count = bot_ref.retriever.index_document(doc)
        return doc.title, count

    title, count = await asyncio.to_thread(work)
    await interaction.followup.send(f"✅ 파일 추가 완료: **{title}** (청크 {count}개)")


@app_commands.command(name="addurl", description="웹페이지(HTML) 내용을 추출해 지식베이스에 추가")
@app_commands.describe(url="분석할 URL")
async def add_url(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    assert bot_ref is not None

    def work() -> tuple[str, int]:
        doc = parse_url(url)
        count = bot_ref.retriever.index_document(doc)
        return doc.title, count

    title, count = await asyncio.to_thread(work)
    await interaction.followup.send(f"✅ URL 추가 완료: **{title}** (청크 {count}개)")


@app_commands.command(name="addyoutube", description="유튜브 자막/스크립트를 수집해 지식베이스에 추가")
@app_commands.describe(url_or_id="유튜브 URL 또는 video id")
async def add_youtube(interaction: discord.Interaction, url_or_id: str):
    await interaction.response.defer(thinking=True)
    assert bot_ref is not None

    def work() -> tuple[str, int, str]:
        doc = parse_youtube(url_or_id)
        count = bot_ref.retriever.index_document(doc)
        return doc.title, count, doc.source_ref

    title, count, source_ref = await asyncio.to_thread(work)
    await interaction.followup.send(
        f"✅ YouTube 추가 완료: **{title}** (청크 {count}개)\n원본: {source_ref}"
    )


@app_commands.command(name="sources", description="현재 인덱싱된 소스 목록")
async def list_sources(interaction: discord.Interaction):
    assert bot_ref is not None
    docs = await asyncio.to_thread(bot_ref.retriever.list_documents)
    if not docs:
        await interaction.response.send_message("아직 추가된 소스가 없습니다.")
        return

    lines = [f"- `{d['source_type']}` | **{d['title'] or 'untitled'}** | {d['source_ref']}" for d in docs[:30]]
    await interaction.response.send_message("\n".join(lines))


@app_commands.command(name="ask", description="RAG 기반으로 질문")
@app_commands.describe(question="질문 내용")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    assert bot_ref is not None

    contexts = await asyncio.to_thread(bot_ref.retriever.query, question)
    answer = await asyncio.to_thread(bot_ref.llm.generate_answer, question, contexts)

    refs = []
    for item in contexts[: bot_ref.settings.max_context_chunks]:
        meta = item.get("meta", {})
        refs.append(f"- {meta.get('title', 'untitled')} | {meta.get('source_ref', 'unknown')}")

    ref_text = "\n".join(refs) if refs else "- (참조 없음)"
    msg = f"**답변**\n{answer}\n\n**참고 소스**\n{ref_text}"

    if len(msg) > 1900:
        msg = msg[:1850] + "\n...(생략)"
    await interaction.followup.send(msg)


def run_bot(settings: Settings) -> None:
    global bot_ref
    bot_ref = NotebookBot(settings)
    bot_ref.run(settings.discord_token)
