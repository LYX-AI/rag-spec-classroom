# 规格问答 · 库存查询（课堂 Demo）

**Classroom demo: spec-sheet RAG + fake-inventory MCP**

> 这是一门 **Agent 入门课** 的辅助材料：用一个能跑的最小闭环，讲清 **RAG** 和 **MCP / Tool**。  
> This repo is companion material for an **introductory Agent course**. It is a runnable **minimum closed loop** for learning **RAG** and **MCP / Tool**.

它不是 Agent：问答顺序写死为「安检 → 检索 → 生成」，库存要人点按钮才查。  
It is **not** an Agent. Q&A follows a fixed workflow (`guardrail → retrieve → generate`). Inventory is queried only when a human clicks the button.

---

## 中文

### 这是什么

企业内部「设备规格助手」的课堂精简版：

| 能力 | 做什么 |
|---|---|
| **RAG** | 先从说明书里找出相关段落，再按资料生成答案；没有就承认没有 |
| **护栏** | 与工程机械无关的问题（例如写诗）在检索前拦截 |
| **MCP / Tool** | 左侧「查询库存」走假库存服务（`list_tools` → `call_tool`） |

适合：听完概念后，对着真实页面和源码看「层」落在哪。不包含完整课件讲义。

### 你需要准备

- Python 3.10+
- 两把免费 API Key（写在 `.env`，**不要提交**）：
  - [智谱](https://open.bigmodel.cn/usercenter/apikeys) `ZHIPUAI_API_KEY` → 对话 `glm-4-flash`
  - [硅基流动](https://cloud.siliconflow.cn) `SILICONFLOW_API_KEY` → 向量 `BAAI/bge-m3`（不要写成 `Pro/BAAI/bge-m3`）

### 启动

在项目根目录：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

用编辑器打开 `.env`，填入两把 Key。然后建库并启动页面：

```powershell
python ingest.py
python -m streamlit run app.py
```

macOS / Linux 把激活和复制换成：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 Key
python ingest.py
python -m streamlit run app.py
```

浏览器打开终端给出的地址，一般是 `http://localhost:8501`。侧栏勾上 **Show retrieved context**。

改过 `scripts/spec-sheets/` 里的说明书后，必须再跑一次 `python ingest.py`。

### 建议怎么玩（对应课堂三问）

一次只问一句，看完再问下一句。

1. **资料里有的**  
   `BD850 额定功率是多少？`  
   应出现约 `634 kW` / `850 hp`，以及推土机 PDF 出处。

2. **资料里没有的字段（先用英文）**  
   `What is the lifting capacity of the BD850 bulldozer?`  
   应类似 `I don't have that information.` 检索仍会跑，但段落里没有起重吨位。

3. **不该进业务的问题**  
   `Write a poem about cooking pasta`  
   应 `I'm unable to answer this, please try again`，**没有** Retrieved references。

**库存：** 左侧型号填 `BD850` 点查询。填 `FAIL` 可看失败提示（课上用来说明「失败要看得见」）。

**已知课堂漏洞（不是操作错误）：** 用中文问「BD850 推土机的起重能力是多少」时，检索前 3 段可能混进吊车说明书，模型会把吊车吨位抄到推土机上。英文问同一句通常能停住。用来讲「抽错书仍会抄错」，本仓库不修。

### 文件说明

```text
app.py                 页面：安检 → 检索 → 生成；左侧库存按钮
bedrock_utils.py       valid_prompt / query_knowledge_base / generate_response
ingest.py              切片、向量化、本地余弦检索
inventory_server.py    假库存 MCP Server（check_inventory）
mcp_client.py          MCP Client（list / call）
data/inventory.json    假库存表
scripts/spec-sheets/   说明书 PDF（优先入库）与 Markdown 备用
.env.example           Key 模板
```

对话模型和向量模型不是同一路，不要讲成一个模型。

---

## English

### What this is

A small in-class **spec-sheet assistant** for heavy machinery:

| Piece | Role |
|---|---|
| **RAG** | Retrieve passages from company spec sheets, then generate **only** from that context |
| **Guardrail** | Off-topic prompts (e.g. a pasta poem) are blocked **before** retrieval |
| **MCP / Tool** | The left-hand inventory lookup is a fake stock tool (`list_tools` → `call_tool`) |

Use it after the concepts talk: point at the running UI and the source. Full lecture notes are **not** in this repo.

This is a **Workflow + Tool** demo, not an Agent: the model does not choose the next step.

### Prerequisites

- Python 3.10+
- Two free API keys in `.env` (never commit `.env`):
  - [Zhipu](https://open.bigmodel.cn/usercenter/apikeys) `ZHIPUAI_API_KEY` for chat (`glm-4-flash`)
  - [SiliconFlow](https://cloud.siliconflow.cn) `SILICONFLOW_API_KEY` for embeddings (`BAAI/bge-m3` — do **not** use the `Pro/` prefix)

### Run

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

Fill both keys in `.env`, then:

```bash
python ingest.py
python -m streamlit run app.py
```

Open the URL from the terminal (usually `http://localhost:8501`). Enable **Show retrieved context** in the sidebar.

Re-run `python ingest.py` after you change files under `scripts/spec-sheets/`.

### Suggested demo prompts

Ask one question at a time.

1. **In the sheets:** `What is the rated power of the BD850 bulldozer?`  
   Expect about `634 kW` / `850 hp` and a bulldozer PDF citation.

2. **Field not in the sheets:** `What is the lifting capacity of the BD850 bulldozer?`  
   Expect `I don't have that information.` Retrieval still runs; the passages have no lifting capacity.

3. **Out of domain:** `Write a poem about cooking pasta`  
   Expect `I'm unable to answer this, please try again` and **no** retrieved references.

**Inventory:** query `BD850` on the left. Use `FAIL` to see a visible tool error.

**Known teaching bug:** the Chinese question *「BD850 推土机的起重能力是多少」* may retrieve a mobile-crane sheet and copy crane tonnage onto the bulldozer. The English phrasing above usually stays on bulldozer pages. Left unfixed on purpose.

### Layout

Same file list as in the Chinese section. Chat and embedding are **two** model stacks, not one.

---

## License

Course companion code. Use and copy for teaching; do not commit API keys.
