import os
import uuid
from typing import Any

import requests
import streamlit as st


DEFAULT_BASE_URL = os.getenv("PAPERPILOT_BASE_URL", "http://localhost:8000")
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"
REQUEST_TIMEOUT = 600


st.set_page_config(page_title="PaperPilot Console", page_icon="📄", layout="wide")


def api_url(path: str) -> str:
    return f"{BASE_URL.rstrip('/')}{path}"


def request_json(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    response = requests.request(method, api_url(path), timeout=REQUEST_TIMEOUT, **kwargs)
    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def show_api_error(error: Exception) -> None:
    if isinstance(error, requests.ConnectionError):
        st.error("无法连接后端服务。请确认 FastAPI 已在 BASE_URL 对应地址启动，例如 http://localhost:8000。")
        st.code(
            "cd F:\\PaperPilot\n"
            "pip install -r requirements.txt\n"
            "docker compose up -d\n"
            "alembic upgrade head\n"
            "uvicorn app.main:app --reload",
            language="powershell",
        )
        return
    if isinstance(error, requests.HTTPError) and error.response is not None:
        try:
            detail = error.response.json()
        except ValueError:
            detail = error.response.text
        st.error(f"API 请求失败：HTTP {error.response.status_code}")
        st.code(str(detail), language="json")
        return
    st.error(f"请求失败：{error}")


def dataframe_or_info(items: list[dict[str, Any]], empty_message: str) -> None:
    if items:
        st.dataframe(items, use_container_width=True)
    else:
        st.info(empty_message)


def is_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False


st.title("PaperPilot 控制台")
st.caption("FastAPI + LangGraph + RAG 学术论文写作辅助系统 Demo")

with st.sidebar:
    st.header("项目设置")
    BASE_URL = st.text_input("Backend BASE_URL", value=DEFAULT_BASE_URL)
    if st.button("检查后端连接", use_container_width=True):
        try:
            health = request_json("GET", "/health")
            st.success(f"后端在线：{health.get('app', 'PaperPilot')} / {health.get('env', '-')}")
        except Exception as exc:
            show_api_error(exc)

    user_id = st.text_input("user_id", value=st.session_state.get("user_id", DEFAULT_USER_ID))
    if not is_uuid(user_id):
        st.warning("user_id 必须是 UUID。点击下面按钮可恢复默认 demo user。")
        if st.button("使用默认 user_id", use_container_width=True):
            st.session_state["user_id"] = DEFAULT_USER_ID
            st.rerun()

    project_id = st.text_input("project_id", value=st.session_state.get("project_id", ""))
    if project_id and not is_uuid(project_id):
        st.warning("project_id 必须是后端返回的 UUID，不能填 1 这样的数字。请先创建或选择项目。")

    st.session_state["project_id"] = project_id
    st.session_state["user_id"] = user_id

    with st.expander("创建 / 选择项目", expanded=not is_uuid(project_id)):
        project_title = st.text_input("新项目标题", value="PaperPilot Demo Project")
        project_direction = st.text_input("研究方向", value="RAG, LangGraph, 学术论文助手")
        project_keywords = st.text_input("关键词（逗号分隔）", value="RAG,Agent,论文写作")

        if st.button("创建项目", type="primary", use_container_width=True):
            if not is_uuid(user_id):
                st.warning("请先填写合法 user_id UUID。")
            elif not project_title.strip():
                st.warning("项目标题不能为空。")
            else:
                with st.spinner("正在创建项目..."):
                    try:
                        payload = {
                            "user_id": user_id,
                            "title": project_title.strip(),
                            "research_direction": project_direction.strip() or None,
                            "keywords": [item.strip() for item in project_keywords.split(",") if item.strip()],
                            "description": "Created from Streamlit demo console",
                        }
                        created = request_json("POST", "/api/projects", json=payload)
                        st.session_state["project_id"] = created["id"]
                        st.success(f"项目创建成功：{created['id']}")
                        st.rerun()
                    except Exception as exc:
                        show_api_error(exc)

        if st.button("刷新项目列表", use_container_width=True):
            with st.spinner("正在查询项目列表..."):
                try:
                    st.session_state["projects"] = request_json("GET", "/api/projects")
                except Exception as exc:
                    show_api_error(exc)

        projects = st.session_state.get("projects", [])
        if projects:
            labels = [f"{item.get('title')} | {item.get('id')}" for item in projects]
            selected_label = st.selectbox("选择已有项目", labels)
            selected_index = labels.index(selected_label)
            if st.button("使用选中项目", use_container_width=True):
                st.session_state["project_id"] = projects[selected_index]["id"]
                st.rerun()

    st.divider()
    st.subheader("上传论文")
    uploaded_file = st.file_uploader("选择 PDF / DOCX", type=["pdf", "docx"])
    upload_clicked = st.button("上传文档", type="primary", use_container_width=True)

    if upload_clicked:
        if not project_id.strip():
            st.warning("请先输入 project_id。")
        elif uploaded_file is None:
            st.warning("请选择要上传的 PDF 或 DOCX 文件。")
        else:
            with st.spinner("正在上传文档..."):
                try:
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type or "application/octet-stream",
                        )
                    }
                    data = request_json(
                        "POST",
                        f"/api/projects/{project_id}/documents/upload",
                        files=files,
                    )
                    st.success("上传成功")
                    st.json(data)
                    if data.get("document_id"):
                        st.session_state["last_document_id"] = data["document_id"]
                except Exception as exc:
                    show_api_error(exc)

    if st.session_state.get("last_document_id"):
        st.caption(f"最近 document_id：`{st.session_state['last_document_id']}`")

    with st.expander("选择已上传文档", expanded=False):
        if st.button("刷新文档列表", use_container_width=True):
            if not is_uuid(project_id):
                st.warning("请先选择合法 project_id。")
            else:
                with st.spinner("正在查询文档列表..."):
                    try:
                        st.session_state["documents"] = request_json("GET", f"/api/projects/{project_id}/documents")
                    except Exception as exc:
                        show_api_error(exc)

        documents = st.session_state.get("documents", [])
        if documents:
            doc_labels = [
                (
                    f"{item.get('original_filename')} | "
                    f"parsed={item.get('parse_status')} | indexed={item.get('index_status')} | {item.get('id')}"
                )
                for item in documents
            ]
            selected_doc_label = st.selectbox("选择文档", doc_labels)
            selected_doc_index = doc_labels.index(selected_doc_label)
            if st.button("使用选中文档", use_container_width=True):
                st.session_state["last_document_id"] = documents[selected_doc_index]["id"]
                st.rerun()


if not project_id.strip():
    st.warning("请先在左侧输入 project_id。")


tab_chat, tab_summary, tab_translation, tab_planning, tab_trace = st.tabs(
    ["1️⃣ RAG 问答", "2️⃣ 论文总结", "3️⃣ 论文翻译", "4️⃣ 论文规划", "5️⃣ Run Trace 查看"]
)


with tab_chat:
    st.subheader("RAG 知识库问答")
    question = st.text_area("输入问题", placeholder="例如：这篇论文提出的方法是什么？", height=120)
    chat_document_id = st.text_input(
        "可选 document_id（建议选择 parsed/indexed 的文档）",
        value=st.session_state.get("last_document_id", ""),
        key="chat_document_id",
    )
    col_top_k, col_threshold = st.columns(2)
    with col_top_k:
        chat_top_k = st.slider("top_k", min_value=1, max_value=20, value=6)
    with col_threshold:
        chat_threshold = st.slider(
            "similarity_threshold（调试时可设为 0.00）",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.01,
        )
    ask_clicked = st.button("提问", type="primary")

    if ask_clicked:
        if not project_id.strip() or not question.strip():
            st.warning("project_id 和问题不能为空。")
        else:
            payload = {
                "project_id": project_id,
                "user_id": user_id,
                "query": question.strip(),
                "top_k": chat_top_k,
                "similarity_threshold": chat_threshold,
            }
            if chat_document_id.strip():
                if is_uuid(chat_document_id.strip()):
                    payload["document_ids"] = [chat_document_id.strip()]
                else:
                    st.warning("document_id 不是合法 UUID，将按整个项目知识库检索。")
            with st.spinner("正在检索项目知识库并生成回答..."):
                try:
                    data = request_json("POST", "/api/chat", json=payload)
                    st.markdown("### 回答")
                    st.markdown(data.get("answer", ""))

                    st.markdown("### 引用来源")
                    dataframe_or_info(data.get("citations", []), "没有返回引用。")

                    if data.get("agent_run_id"):
                        st.info(f"agent_run_id: `{data['agent_run_id']}`")
                except Exception as exc:
                    show_api_error(exc)


with tab_summary:
    st.subheader("论文总结")
    summary_document_id = st.text_input(
        "document_id",
        value=st.session_state.get("last_document_id", ""),
        key="summary_document_id",
    )
    summary_type = st.selectbox("summary_type", ["quick", "standard", "detailed"], index=1)
    summary_clicked = st.button("生成总结", type="primary")

    if summary_clicked:
        if not project_id.strip() or not summary_document_id.strip():
            st.warning("project_id 和 document_id 不能为空。")
        else:
            payload = {
                "project_id": project_id,
                "document_id": summary_document_id.strip(),
                "user_id": user_id,
                "summary_type": summary_type,
            }
            with st.spinner("正在生成论文总结..."):
                try:
                    data = request_json("POST", "/api/paper/summary", json=payload)
                    if data.get("output_id"):
                        st.success(f"生成成功，output_id: {data['output_id']}")
                    st.markdown(data.get("summary_markdown", ""))
                except Exception as exc:
                    show_api_error(exc)


with tab_translation:
    st.subheader("英文论文翻译")
    translation_document_id = st.text_input(
        "document_id",
        value=st.session_state.get("last_document_id", ""),
        key="translation_document_id",
    )
    col_mode, col_style = st.columns(2)
    with col_mode:
        translation_mode = st.selectbox("translation_mode", ["faithful", "polished"])
    with col_style:
        output_style = st.selectbox("output_style", ["bilingual", "chinese_only"])
    st.caption("Demo 建议先翻译少量 chunk 或页码范围；整篇 PDF 会连续调用多次 LLM，耗时较长。")
    range_type = st.selectbox("range_type", ["chunks", "pages", "full"], index=0)
    page_from = page_to = chunk_from = chunk_to = None
    if range_type == "pages":
        col_page_from, col_page_to = st.columns(2)
        with col_page_from:
            page_from = st.number_input("page_from", min_value=1, value=1, step=1)
        with col_page_to:
            page_to = st.number_input("page_to", min_value=1, value=3, step=1)
    elif range_type == "chunks":
        col_chunk_from, col_chunk_to = st.columns(2)
        with col_chunk_from:
            chunk_from = st.number_input("chunk_from", min_value=0, value=0, step=1)
        with col_chunk_to:
            chunk_to = st.number_input("chunk_to", min_value=0, value=10, step=1)

    translation_clicked = st.button("开始翻译", type="primary")

    if translation_clicked:
        if not project_id.strip() or not translation_document_id.strip():
            st.warning("project_id 和 document_id 不能为空。")
        else:
            payload = {
                "project_id": project_id,
                "document_id": translation_document_id.strip(),
                "user_id": user_id,
                "translation_mode": translation_mode,
                "output_style": output_style,
                "range_type": range_type,
                "requirements": "保持学术表达，保留公式、图表编号和引用编号",
            }
            if range_type == "pages":
                payload.update({"page_from": int(page_from), "page_to": int(page_to)})
            elif range_type == "chunks":
                payload.update({"chunk_from": int(chunk_from), "chunk_to": int(chunk_to)})
            with st.spinner("正在分段翻译论文，耗时取决于文档长度..."):
                try:
                    data = request_json("POST", "/api/translation/document", json=payload)
                    if data.get("output_id"):
                        st.success(f"翻译完成，output_id: {data['output_id']}")

                    warnings = data.get("warnings", [])
                    if warnings:
                        st.warning("存在术语或分段翻译提醒：")
                        for warning in warnings:
                            st.write(f"- {warning}")

                    st.markdown("### 翻译结果")
                    st.markdown(data.get("translated_markdown", ""))

                    st.markdown("### 术语表")
                    dataframe_or_info(data.get("terminologies", []), "没有返回术语表。")
                except Exception as exc:
                    show_api_error(exc)


with tab_planning:
    st.subheader("论文规划")
    topic = st.text_input(
        "论文题目 / 研究主题",
        placeholder="基于RAG与多Agent编排的论文助手系统设计与实现",
    )
    research_direction = st.text_input(
        "研究方向",
        placeholder="RAG, 多Agent, 学术论文写作辅助",
    )
    planning_clicked = st.button("生成规划", type="primary")

    if planning_clicked:
        if not project_id.strip() or not topic.strip():
            st.warning("project_id 和 topic 不能为空。")
        else:
            payload = {
                "project_id": project_id,
                "user_id": user_id,
                "topic": topic.strip(),
                "research_direction": research_direction.strip() or None,
                "paper_type": "thesis",
            }
            with st.spinner("正在生成论文规划..."):
                try:
                    data = request_json("POST", "/api/planning/topic", json=payload)
                    if data.get("output_id"):
                        st.success(f"规划生成成功，output_id: {data['output_id']}")
                    if data.get("run_id"):
                        st.info(f"异步任务已提交，run_id: `{data['run_id']}`")
                    st.markdown(data.get("final_markdown", ""))
                except Exception as exc:
                    show_api_error(exc)


with tab_trace:
    st.subheader("Run Trace 查看")
    st.caption("用于展示 LangGraph Agent 的节点链路、耗时、输入输出裁剪内容和错误信息。")
    run_id = st.text_input("run_id", placeholder="输入 /api/chat 或异步任务返回的 run_id")
    trace_clicked = st.button("查询 Run Trace", type="primary")

    if trace_clicked:
        if not run_id.strip():
            st.warning("run_id 不能为空。")
        else:
            with st.spinner("正在查询 Agent 执行链路..."):
                try:
                    data = request_json("GET", f"/api/runs/{run_id.strip()}")

                    col_status, col_latency, col_tokens, col_cost = st.columns(4)
                    col_status.metric("status", data.get("status", "-"))
                    col_latency.metric("total_latency_ms", data.get("total_latency_ms", 0))
                    col_tokens.metric("total_tokens", data.get("total_tokens", 0))
                    col_cost.metric("estimated_cost", data.get("estimated_cost", 0.0))

                    st.markdown("### 节点概览")
                    nodes = data.get("nodes", [])
                    overview = [
                        {
                            "node_name": node.get("node_name") or node.get("tool_name"),
                            "status": node.get("status"),
                            "latency_ms": node.get("latency_ms"),
                            "error_message": node.get("error_message"),
                        }
                        for node in nodes
                    ]
                    dataframe_or_info(overview, "当前 run 没有 trace 节点。")

                    st.markdown("### 节点详情")
                    for index, node in enumerate(nodes, start=1):
                        node_name = node.get("node_name") or node.get("tool_name") or f"node-{index}"
                        status = node.get("status", "unknown")
                        latency_ms = node.get("latency_ms", 0)
                        title = f"{index}. {node_name} | {status} | {latency_ms} ms"
                        with st.expander(title, expanded=status == "error"):
                            st.write("**input**")
                            st.json(node.get("input"))
                            st.write("**output**")
                            st.json(node.get("output"))
                            if node.get("error_message"):
                                st.error(node["error_message"])
                except Exception as exc:
                    show_api_error(exc)
