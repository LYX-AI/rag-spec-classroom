import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from bedrock_utils import generate_response, query_knowledge_base, valid_prompt
from mcp_client import call_check_inventory, list_inventory_tools

load_dotenv(Path(__file__).resolve().parent / ".env")

st.set_page_config(page_title="规格问答 · 库存查询", page_icon="🚜", layout="wide")
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.4rem; }
    .hero-kicker { color: #64748b; font-size: 0.86rem; letter-spacing: 0.04em; text-transform: uppercase; }
    .stock-pill { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 999px; font-weight: 600; font-size: 0.9rem; }
    .stock-yes { background: #dcfce7; color: #166534; }
    .stock-no { background: #fee2e2; color: #991b1b; }
    .tool-chip { display: inline-block; background: #f1f5f9; color: #334155; border-radius: 8px; padding: 0.15rem 0.5rem; margin-right: 0.35rem; font-size: 0.82rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Streamlit UI
st.markdown('<p class="hero-kicker">规格助手</p>', unsafe_allow_html=True)
st.title("设备规格与库存")
st.caption("问规格走说明书检索。查库存走 MCP 接到外部库存服务。")

if "mcp_tools" not in st.session_state:
    st.session_state.mcp_tools = None
    st.session_state.mcp_tools_error = None
    try:
        st.session_state.mcp_tools = list_inventory_tools()
    except Exception as exc:
        st.session_state.mcp_tools_error = str(exc)

tool_col, query_col = st.columns((1.05, 1.35), gap="large")

with tool_col:
    with st.container(border=True):
        st.subheader("可用工具")
        st.caption("库存服务对外提供的能力")
        if st.session_state.get("mcp_tools_error"):
            st.error("库存服务暂时连不上。")
            st.caption(st.session_state.mcp_tools_error)
        elif not st.session_state.get("mcp_tools"):
            st.info("当前没有可用工具。")
        else:
            for tool in st.session_state.mcp_tools:
                st.markdown(f"**{tool.get('title') or tool.get('name')}**")
                st.caption(tool.get("description") or "")
                chips = []
                for param in tool.get("parameters") or []:
                    mark = "必填" if param.get("required") else "可选"
                    chips.append(f"`{param.get('name')}` · {mark}")
                if chips:
                    st.markdown("参数：" + "　".join(chips))
        if st.button("刷新工具列表", use_container_width=True):
            try:
                st.session_state.mcp_tools = list_inventory_tools()
                st.session_state.mcp_tools_error = None
            except Exception as exc:
                st.session_state.mcp_tools_error = str(exc)
                st.session_state.mcp_tools = None
            st.rerun()

with query_col:
    with st.container(border=True):
        st.subheader("查询库存")
        with st.form("inventory_lookup"):
            mcp_model = st.text_input("设备型号", value="BD850", placeholder="例如 BD850")
            submitted = st.form_submit_button("查询", use_container_width=True, type="primary")
        if submitted:
            model_id = (mcp_model or "").strip()
            if not model_id:
                st.session_state.mcp_error = "请先填写型号。"
                st.session_state.mcp_result = None
            else:
                try:
                    st.session_state.mcp_result = call_check_inventory(model_id)
                    st.session_state.mcp_error = None
                except Exception as exc:
                    st.session_state.mcp_error = str(exc)
                    st.session_state.mcp_result = None

        if st.session_state.get("mcp_error"):
            st.error("查询失败，请稍后重试。")
            st.caption(st.session_state.mcp_error)
        result = st.session_state.get("mcp_result")
        if result:
            if not result.get("ok"):
                st.error("库存服务不可用")
                st.caption(result.get("message") or "外部系统没有返回结果。")
            else:
                in_stock = bool(result.get("in_stock"))
                qty = result.get("qty")
                model_name = result.get("model") or "—"
                note = result.get("note") or ""
                pill_class = "stock-yes" if in_stock else "stock-no"
                pill_text = "有货" if in_stock else "无货"
                st.markdown(
                    f'<span class="stock-pill {pill_class}">{pill_text}</span>',
                    unsafe_allow_html=True,
                )
                metric_cols = st.columns(3)
                metric_cols[0].metric("型号", model_name)
                metric_cols[1].metric("库存状态", "在库" if in_stock else "缺货")
                metric_cols[2].metric("数量", 0 if qty is None else qty)
                if note:
                    st.caption(note)

st.divider()
st.subheader("规格问答")
st.caption("根据设备说明书回答。库存数字不在这里查。")

# Sidebar for configurations
st.sidebar.header("Configuration")
model_id = st.sidebar.selectbox("Select LLM Model", ["glm-4-flash"])

default_kb_id = os.getenv("BEDROCK_KB_ID", "local-spec-sheets")
kb_id = st.sidebar.text_input("Knowledge Base ID", default_kb_id)
temperature = st.sidebar.select_slider("Temperature", [i / 10 for i in range(0, 11)], 1)
top_p = st.sidebar.select_slider("Top_P", [i / 1000 for i in range(0, 1001)], 1)
show_context = st.sidebar.checkbox("Show retrieved context", value=False)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to know?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    kb_results = []
    if valid_prompt(prompt, model_id):
        # Query Knowledge Base
        kb_results = query_knowledge_base(prompt, kb_id)

        # Prepare context from Knowledge Base results
        context = "\n\n---\n\n".join([result["text"] for result in kb_results if result.get("text")])
        references = []
        for res in kb_results:
            source = res.get("source")
            if source:
                references.append(
                    f"{source} | score: {round(res['score'], 3) if res.get('score') is not None else 'n/a'}"
                )

        # Generate response using LLM
        instruction = (
            "You are a heavy machinery assistant. Answer the user's question ONLY using the context. "
            "If the context does not contain the answer, reply with \"I don't have that information.\" "
            "Respond in the same language as the question."
        )
        full_prompt = f"{instruction}\n\nContext:\n{context or 'N/A'}\n\nQuestion: {prompt}\nAnswer:"
        response = generate_response(full_prompt, model_id, temperature, top_p)

        # Optionally surface retrieved references under the answer
        if references:
            response = f"{response}\n\n---\nRetrieved references:\n" + "\n".join(references)
        elif not context:
            response = f"I could not find relevant passages in Knowledge Base `{kb_id}`. Please verify the ID or ingest data first."
    else:
        response = "I'm unable to answer this, please try again"

    # Display assistant response
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

    if show_context and kb_results:
        with st.expander("Retrieved context"):
            for idx, res in enumerate(kb_results, start=1):
                st.markdown(f"**Result {idx}** | score: {res.get('score')} | source: {res.get('source')}")
                st.write(res.get("text", ""))
