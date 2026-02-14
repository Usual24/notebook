# Local NotebookLM-style Discord Bot (LM Studio + 100% Local Inference)

Discord 안에서 파일 업로드/웹페이지 추가/유튜브 스크립트 추가/대화형 질의응답(RAG)을 수행하는, **NotebookLM 유사 로컬 시스템**입니다.

- **LLM 추론은 LM Studio 로컬 서버**를 사용합니다.
- **유료 외부 API는 사용하지 않습니다.**
- Discord가 UI 역할을 하며, 업로드/소스추가/질문을 모두 Discord에서 수행합니다.

## 핵심 기능

- 파일 업로드 인덱싱 (`/addfile`)
  - txt, md, pdf 등 텍스트 추출 가능한 파일
- 웹페이지(HTML) 분석 (`/addurl`)
  - 기사/블로그/문서 등 HTML 컨텐츠 본문 추출
- 유튜브 스크립트 + 제목 처리 (`/addyoutube`)
  - 자막 transcript 수집 후 인덱싱
  - 제목은 YouTube 페이지에서 가능한 경우 자동 추출
- RAG 질의응답 (`/ask`)
  - 로컬 임베딩 + 로컬 벡터DB 검색
  - 검색 문맥 기반으로 LM Studio 모델 답변
- 소스 목록 확인 (`/sources`)

## 구조

- `src/local_notebooklm/config.py`: 환경변수 설정
- `src/local_notebooklm/ingest.py`: 파일/웹/유튜브 파서
- `src/local_notebooklm/retrieval.py`: 임베딩 + ChromaDB 인덱싱/검색
- `src/local_notebooklm/llm.py`: LM Studio(OpenAI 호환) 호출
- `src/local_notebooklm/bot.py`: Discord slash command 구현
- `src/local_notebooklm/storage.py`: SQLite 메타데이터 저장

## 사전 준비

1. Python 3.10+
2. LM Studio 설치 후 로컬 서버 실행
   - OpenAI 호환 endpoint 예: `http://127.0.0.1:1234/v1`
3. Discord Bot 생성 및 토큰 발급
   - Server에 bot 추가 + application commands 권한 부여

## 설치

```bash
pip install -r requirements.txt
```

또는

```bash
pip install -e .
```

## 환경 변수

```bash
cp .env.example .env
```

`.env` 예시:

```env
DISCORD_TOKEN=your_discord_bot_token
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
LMSTUDIO_MODEL=local-model-name
DATA_DIR=./data
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
TOP_K=6
MAX_CONTEXT_CHUNKS=8
```

## 실행

```bash
python -m local_notebooklm.app
```

또는

```bash
local-notebooklm
```

## Discord 명령어

- `/addfile file:<attachment>`
- `/addurl url:<https://...>`
- `/addyoutube url_or_id:<youtube url or id>`
- `/sources`
- `/ask question:<질문>`

## 동작 방식 요약

1. 소스 추가 시 텍스트를 추출/정규화
2. 청크 분할
3. 로컬 임베딩 모델로 벡터화
4. ChromaDB + SQLite에 저장
5. 질문 시 top-k 검색 후 문맥을 LM Studio 모델에 전달

## 주의사항

- 완전 로컬 추론(LLM/임베딩/벡터DB)은 가능하지만,
  - 웹페이지 수집(`/addurl`),
  - 유튜브 스크립트/제목 수집(`/addyoutube`)
  는 원문 접근을 위해 네트워크가 필요합니다.
- 유튜브 자막이 없는 영상은 transcript 수집이 실패할 수 있습니다.
- 대용량 문서에서는 임베딩 초기 로딩 시간이 걸릴 수 있습니다.
