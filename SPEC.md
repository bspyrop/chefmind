# ChefMind Spec v1
AI Recipe & Meal Planning Assistant (RAG + MCP Tool Calling + Streamlit + LangChain + OpenAI)

## 1. Project Summary

**Title:** ChefMind — AI Recipe & Meal Planning Assistant

ChefMind is a Streamlit web app where users chat with an AI agent that can:
- Recommend **X recipes** based on ingredients/diet constraints by searching **YouTube transcript RAG**.
- Generate a **user-friendly written recipe** from a given **YouTube video ID**.
- Estimate **nutrition** for a recipe (calories/macros and optionally micros).
- Provide **exact timestamps** for specific steps in the cooking process.
- Maintain **conversation memory** across turns.

The app also supports adding new YouTube videos, which are ingested into the RAG index under the hood.

---

## 2. Tech Stack & Architecture

### 2.1 Core Technologies
- **OpenAI (LLM + Embeddings)**
  - Chat model via LangChain `ChatOpenAI`
  - Embeddings via LangChain `OpenAIEmbeddings`
- **LangChain**
  - Agent + memory
  - Tool calling integration (via MCP server tools and/or LangChain tools)
- **Streamlit**
  - Minimal, clean UI: chat + panels for RAG evidence and tool logs
- **Vector Database**
  - Any supported store (e.g., Chroma/FAISS/Pinecone/Weaviate). Choose one and keep it consistent.

### 2.2 High-Level Flow
1. User chats in Streamlit.
2. Agent decides whether to:
   - retrieve transcript chunks via `rag_search`, or
   - add a new video via `rag_add_youtube_video`, or
   - estimate nutrition via `nutrition_estimate`, etc.
3. Agent answers with:
   - a clean user-facing response
   - a small `UI_JSON` block for the app to route updates (YouTube preview, citations, etc.)
4. Streamlit renders:
   - Chat
   - RAG evidence panel (retrieved chunks with timestamps)
   - Tool log panel (tool calls + results)
   - YouTube player preview
   - Indexed video catalog list

---

## 3. Streamlit UI Requirements (Minimal & Clean)

The page must contain five areas:

1. **Chat area**
   - User + assistant messages
   - Streaming responses optional

2. **RAG Evidence panel**
   - Show the retrieval query
   - Show top retrieved chunks (text + `start/end` timestamp + video title/url)

3. **Tool Calls panel**
   - Show tool invocation input + tool output
   - Display in chronological order

4. **YouTube video preview**
   - Embedded player for currently selected `video_id`
   - If no video selected, show placeholder text

5. **Video catalog**
   - List titles already indexed in RAG
   - Clicking a title sets it as the selected video (and updates the player)

### 3.1 Naming Convention for Panels (recommended keys)
- `chefmind.chat`
- `chefmind.rag`
- `chefmind.tools`
- `chefmind.video`
- `chefmind.catalog`

---

## 4. RAG Data Model

### 4.1 Stored Document (per transcript chunk)
Each embedded chunk must store at least:

- `video_id` (string)
- `title` (string)
- `channel` (string)
- `url` (string)
- `published_at` (string/date)
- `chunk_text` (string)
- `start_time_sec` (int)
- `end_time_sec` (int)

Optional helpful metadata:
- `ingredients_detected` (list[str])
- `recipe_name_guess` (string)
- `language` (string)

### 4.2 Chunking Requirements
- Chunk by **30–90 seconds** of transcript or **~300–800 tokens**
- Preserve time alignment:
  - Every chunk must have accurate `start_time_sec` and `end_time_sec`
- Keep transcript text mostly “as spoken”:
  - Light cleaning is okay (remove repeated intro/outro), but do not rewrite steps in a way that breaks timestamp mapping.

### 4.3 Retrieval Requirements
When the user asks about:
- recipes
- ingredients
- steps
- timestamps
- “what did they say about X”
…the agent must call `rag_search` and ground answers in retrieved chunks.

If retrieval is weak/empty:
- Say so
- Suggest: add more videos or refine the query

---

## 5. MCP Tools (Tool Calling Contract)

ChefMind uses tool calling through an MCP server (or equivalent LangChain tool layer). Tool names must remain stable.

### Tool A — `rag_search`
**Purpose:** Retrieve transcript chunks from vector DB  
**Inputs:**
```json
{ "query": "string", "k": 6, "filters": { "video_id": "optional-string" } }
```
**Returns:** list of chunks with metadata:
```json
[
  {
    "video_id": "...",
    "title": "...",
    "url": "...",
    "chunk_text": "...",
    "start_time_sec": 123,
    "end_time_sec": 175
  }
]
```

### Tool B — `rag_add_youtube_video`
**Purpose:** Ingest a YouTube URL into RAG (transcript + metadata + chunking + embedding + upsert)  
**Inputs:**
```json
{ "url": "https://www.youtube.com/watch?v=..." }
```
**Returns:**
```json
{ "video_id": "...", "title": "...", "url": "...", "chunks_added": 42, "status": "ok" }
```

### Tool C — `get_video_catalog`
**Purpose:** List indexed videos  
**Inputs:** `{}`  
**Returns:**
```json
[
  { "video_id": "...", "title": "...", "url": "..." }
]
```

### Tool D — `nutrition_estimate`
**Purpose:** Estimate nutrition from ingredient list  
**Inputs:**
```json
{ "ingredients": ["..."], "servings": 2 }
```
**Returns:** (example)
```json
{ "per_serving": { "calories": 550, "protein_g": 35, "carbs_g": 50, "fat_g": 22 } }
```

### Tool E — `parse_recipe_from_transcript` (optional)
**Purpose:** Convert transcript text into structured recipe JSON  
**Inputs:**
```json
{ "transcript_text": "..." }
```
**Returns:**
```json
{ "title": "...", "servings": null, "ingredients": ["..."], "steps": ["..."] }
```

> Note: In most LangChain implementations, OpenAI is configured as `ChatOpenAI` rather than exposed as a tool. Tools above are for domain actions and retrieval.

---

## 6. OpenAI Configuration

### 6.1 LLM (Agent)
- Use LangChain `ChatOpenAI`
- Suggested educational settings:
  - `temperature = 0.2` (or `0` for maximum determinism)
- Ensure secrets are loaded from environment:
  - `OPENAI_API_KEY` via Streamlit secrets or `.env`
- Never hardcode API keys.

### 6.2 Embeddings (RAG)
- Use LangChain `OpenAIEmbeddings` for:
  - Indexing transcript chunks
  - Query embeddings during retrieval
- Use the **same embedding model** consistently for both indexing and querying.

---

## 7. Agent Prompting Specification

This project includes a clear prompting blueprint:
- **System prompt**: defines role, rules, tool usage, RAG discipline, output contract
- **Router prompt**: classifies intent and selects tools
- **RAG query builder**: constructs strong retrieval query
- **Answer-from-context**: produces grounded response with citations/timestamps

### 7.1 System Prompt (ChefMind Agent)
The agent must:
- Use `rag_search` for knowledge grounded in videos.
- Provide URLs/titles when referencing videos.
- Never guess timestamps; use chunk metadata only.
- Keep responses short, list-based, clean.

### 7.2 Router Intent Classes
- `ADD_VIDEO`
- `LIST_VIDEOS`
- `FIND_RECIPES`
- `REWRITE_RECIPE`
- `NUTRITION`
- `TIMESTAMPS`
- `GENERAL_CHAT`

Tool selection rules:
- ADD_VIDEO → `rag_add_youtube_video`
- LIST_VIDEOS → `get_video_catalog`
- FIND_RECIPES → `rag_search` (broad)
- REWRITE_RECIPE → `rag_search` with `filters.video_id`
- NUTRITION → `rag_search` (if needed) → `nutrition_estimate`
- TIMESTAMPS → `rag_search` with optional `filters.video_id`

---

## 8. Output Contract: UI_JSON

Every assistant response must end with a `UI_JSON` block, used by Streamlit to update panels.

### 8.1 UI_JSON Shape (required)
```json
UI_JSON: {
  "selected_video_id": null,
  "video_recommendations": [
    { "video_id": "...", "title": "...", "url": "..." }
  ],
  "timestamps": [
    { "label": "Sear chicken", "time": "05:42", "video_id": "..." }
  ],
  "rag_queries": ["..."],
  "used_tools": ["rag_search"],
  "notes_for_ui": "Show first recommended video in player"
}
```

Rules:
- Keep it small.
- If nothing applies, leave arrays empty and values null.
- `selected_video_id` should be set when there is a clear best video.
- `timestamps` should be included when asked for timestamps or when explicitly provided.
- `used_tools` must reflect tools actually used.

---

## 9. End-to-End Behaviors (User Stories)

### 9.1 Add video to RAG
User: “Add this video: <YouTube URL>”
- Call `rag_add_youtube_video(url)`
- Confirm status and show title/video_id
- Update catalog and optionally select this video in UI_JSON

### 9.2 List available videos
User: “What videos are available?”
- Call `get_video_catalog()`
- Display titles (clean list)
- Include list in UI_JSON notes if needed

### 9.3 Find X recipes for ingredients
User: “Give me 5 recipes using chickpeas and spinach.”
- Call `rag_search(query, k=10)`
- Group by `video_id`
- Return exactly X (or fewer if not enough)
- Each item includes title + URL + one-line reason

### 9.4 Write a user-friendly recipe from YouTube ID
User: “Write a user-friendly recipe for YouTube ID abc123.”
- Call `rag_search(..., filters={video_id:"abc123"})`
- Produce:
  - Title
  - Ingredients (bullets)
  - Steps (numbered)
  - Optional tips (max 3)

If transcript lacks quantities:
- Mark quantities as “not specified in transcript”

### 9.5 Nutrition estimates
User: “Give me the nutritions for that recipe for 2 servings.”
- Ensure ingredient list exists:
  - retrieve via `rag_search` if needed
- Call `nutrition_estimate(ingredients, servings=2)`
- Return a short nutrition summary
- Label as an estimate

### 9.6 Exact timestamps for a step
User: “What’s the timestamp for when they add garlic?”
- Call `rag_search(query="add garlic", filters={video_id if known})`
- Return 1–3 candidate timestamps from retrieved chunks
- Never guess; use metadata only

---

## 10. Data Preparation Tool (Python Ingestion)

ChefMind must include a Python ingestion pipeline used by:
- CLI script OR callable function
- MCP tool `rag_add_youtube_video` uses this internally

### 10.1 Ingestion Pipeline Contract
Input: YouTube URL  
Steps:
1. Extract `video_id`
2. Fetch metadata (title, channel, publish date, duration)
3. Fetch transcript with timecodes
4. Normalize lightly (optional)
5. Chunk while preserving timestamps
6. Embed with OpenAI embeddings
7. Upsert chunks to vector DB with metadata
8. Return ingestion summary

Output:
- video_id, title, url, chunks_added, status

---

## 11. Quality Rules (Educational & Minimal)

- Keep UI clean, not “busy”.
- Keep code commented, educational, and minimal.
- Keep answers short and structured:
  - Lists, steps, recipe cards
- Do not hallucinate:
  - If transcript evidence is missing, say so.
- Timestamps must be grounded in chunk metadata, not guessed.

---

## 12. Demo/Test Prompts

- “Add this video to ChefMind: https://www.youtube.com/watch?v=XXXXX”
- “What videos are available?”
- “Give me 3 recipes with chicken and rice.”
- “Write a user-friendly recipe for YouTube ID XXXXX.”
- “What are the nutritions for that recipe for 2 servings?”
- “What’s the timestamp for when they add garlic?”
- “Give me a weekly meal plan using high-protein dinners from the indexed videos.”

---
