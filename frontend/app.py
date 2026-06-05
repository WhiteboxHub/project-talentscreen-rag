# frontend/app.py
"""Talent Screen UI – Streamlit front‑end.
Enterprise Recruitment Assistant with Search, Chat, Analytics, and Document Management.
"""

import os
import streamlit as st
import requests
import pandas as pd
import json

# ---------------------------------------------------------------------
# Configuration & helpers
# ---------------------------------------------------------------------
# Backend API URL – inside Docker the service name is `backend`
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

# ---------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Talent Screen | Enterprise AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------
# Custom CSS for a premium look
# ---------------------------------------------------------------------
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
        .stApp {background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);color:#f8fafc;}
        .candidate-card {background: rgba(255,255,255,0.05);backdrop-filter: blur(10px);border:1px solid rgba(255,255,255,0.1);padding:24px;border-radius:16px;margin-bottom:20px;transition:transform 0.2s, border 0.2s;}
        .candidate-card:hover {transform:translateY(-4px);border:1px solid #3b82f6;}
        .main-title {background: linear-gradient(90deg, #3b82f6, #2dd4bf);-webkit-background-clip: text;-webkit-text-fill-color: transparent;font-weight:800;font-size:3rem;margin-bottom:0.5rem;}
        .skill-tag {background: rgba(59,130,246,0.2);color:#60a5fa;padding:4px 12px;border-radius:9999px;font-size:0.75rem;font-weight:600;border:1px solid rgba(59,130,246,0.3);margin-right:6px;margin-bottom:6px;display:inline-block;}
        [data-testid="stMetricValue"] {color:#3b82f6 !important;font-weight:700;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------
# Sidebar – ingestion controls
# ---------------------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3850/3850285.png", width=80)
    st.markdown("## **Talent Screen**")
    st.caption("v2.0.0-Production Ready")
    st.divider()
    st.subheader("📥 Data Ingestion")

    # Form for file upload
    with st.form(key="upload_form"):
        uploaded_files = st.file_uploader(
            "Upload Documents (PDF/DOCX/TXT/MD)",
            accept_multiple_files=True,
        )
        doc_type = st.selectbox("Document Type", ["Auto-detect", "Resume", "Job Description", "Interview Guide", "Hiring Policy", "SOP"])
        
        submit = st.form_submit_button("🚀 Process documents")
        if submit:
            if uploaded_files:
                prog = st.progress(0)
                for i, f in enumerate(uploaded_files):
                    params = {}
                    if doc_type != "Auto-detect":
                        params["document_type"] = doc_type.lower().replace(" ", "_")
                        
                    res = requests.post(
                        f"{BACKEND_URL}/upload",
                        params=params,
                        files={"file": (f.name, f.getvalue())},
                    )
                    if res.status_code == 200:
                        st.toast(f"Processing: {f.name}")
                    else:
                        st.error(f"Failed to queue {f.name}")
                    prog.progress((i + 1) / len(uploaded_files))
                st.success("All documents queued for indexing.")
            else:
                st.error("No files selected!")
    st.divider()
    
    # System Status
    try:
        health = requests.get(f"{BACKEND_URL}/health").json()
        status_text = "✅" if health.get("status") == "healthy" else "⚠️"
        st.info(f"System fully operational: {status_text}")
    except:
        st.error("Cannot connect to backend")

# ---------------------------------------------------------------------
# Main dashboard UI
# ---------------------------------------------------------------------
st.markdown('<h1 class="main-title">AI Recruitment Hub</h1>', unsafe_allow_html=True)
st.markdown("#### *Enterprise‑grade candidate retrieval & analysis*")

# Tabs for Search, Chat, Documents, Analytics
tab_search, tab_chat, tab_docs, tab_analytics = st.tabs(["🔍 Smart Retrieval", "💬 Talent Intelligence", "📂 Documents", "📊 Talent Pool Stats"])

# ---------------------------------------------------------------------
# Search tab
# ---------------------------------------------------------------------
with tab_search:
    st.markdown("### Search Talent Pool")
    col_query, col_k = st.columns([4, 1])
    with col_query:
        query = st.text_input("Describe the ideal candidate...", placeholder="e.g., Senior Full‑Stack Engineer with React & AWS experience")
    with col_k:
        top_k = st.select_slider("Results count", options=[3, 5, 10, 20], value=5)
    
    if query:
        with st.spinner("Analyzing intent and searching pool…"):
            try:
                resp = requests.get(f"{BACKEND_URL}/search", params={"query": query, "top_k": top_k})
                if resp.status_code == 200:
                    data = resp.json()
                    # Show AI expansion insight
                    with st.expander("✨ AI Search Insights (Query Analysis)"):
                        st.write(f"**Optimized Query:** {data.get('optimized_query', data['query'])}")
                        st.write(f"**Expanded Query:** {data.get('expanded_query', '')}")
                        st.json(data.get('intent', {}))
                    
                    # Show results
                    results = data.get("results", [])
                    if not results:
                        st.warning("No matches found for this criteria.")
                    else:
                        for r in results:
                            meta = r.get("metadata", {})
                            st.markdown(
                                f"""
                                <div class="candidate-card">
                                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                                        <h3 style="margin:0;color:#eff6ff;">📄 {meta.get('filename','Unknown')} ({meta.get('document_type', 'doc').upper()})</h3>
                                        <span style="background:#059669;color:white;padding:2px 10px;border-radius:4px;font-size:0.8rem;">Score: {r.get('rrank_score', r.get('rrf_score', 0))*1000:.1f}</span>
                                    </div>
                                    <div style="margin-top:10px;color:#94a3b8;">
                                        <b>Role:</b> {meta.get('job_role', 'N/A')} | <b>Experience:</b> {meta.get('years_of_experience', meta.get('experience', 'N/A'))} Years | <b>Edu:</b> {meta.get('education','N/A')}
                                    </div>
                                    <div style="margin-top:12px;">
                                        {" ".join([f'<span class="skill-tag">{s}</span>' for s in str(meta.get('skills', '')).split(',')][:10]) if meta.get('skills') else ""}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            with st.expander("View Document Chunk Content"):
                                st.write(r.get("text", "No text available"))
                else:
                    st.error("Search failed – check backend logs.")
            except Exception as e:
                st.error(f"Could not connect to search API: {e}")

# ---------------------------------------------------------------------
# Chat tab – streaming LLM assistant
# ---------------------------------------------------------------------
with tab_chat:
    st.markdown("### AI Recruitment Assistant")
    st.caption("Ask questions about candidates, hiring policies, or job requirements.")
    
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
        
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            
    if chat_input := st.chat_input("How can I help you with your hiring today?"):
        st.session_state.messages.append({"role": "user", "content": chat_input})
        with st.chat_message("user"):
            st.markdown(chat_input)
            
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_resp = ""
            try:
                # Stream response from backend chat endpoint
                with requests.post(
                    f"{BACKEND_URL}/chat", 
                    json={"query": chat_input, "session_id": st.session_state.session_id}, 
                    stream=True
                ) as r:
                    if r.status_code == 200:
                        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                            if chunk:
                                full_resp += chunk
                                placeholder.markdown(full_resp + "▌")
                        placeholder.markdown(full_resp)
                        st.session_state.messages.append({"role": "assistant", "content": full_resp})
                    else:
                        st.error(f"Chat failed: {r.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")

# ---------------------------------------------------------------------
# Documents tab
# ---------------------------------------------------------------------
with tab_docs:
    st.markdown("### Document Management")
    if st.button("Refresh Documents"):
        try:
            resp = requests.get(f"{BACKEND_URL}/documents")
            if resp.status_code == 200:
                docs = resp.json()
                if docs:
                    df = pd.DataFrame(docs)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No documents found in the database.")
            else:
                st.error("Failed to load documents.")
        except Exception as e:
            st.error(f"Could not connect to API: {e}")
    else:
        st.info("Click 'Refresh Documents' to view the current database state.")

# ---------------------------------------------------------------------
# Analytics tab – Real metrics from DB
# ---------------------------------------------------------------------
with tab_analytics:
    st.markdown("### Talent Pool Analytics")
    if st.button("Refresh Analytics", type="primary"):
        try:
            resp = requests.get(f"{BACKEND_URL}/analytics")
            if resp.status_code == 200:
                data = resp.json()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Documents", data["documents"]["total"])
                with col2:
                    st.metric("Avg. Exp Level", f"{data['insights']['avg_experience_years']} Years")
                with col3:
                    st.metric("Total Searches", data["activity"]["total_searches"])
                
                st.divider()
                
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.markdown("#### Document Types")
                    doc_types = data["documents"].get("by_type", {})
                    if doc_types:
                        df_types = pd.DataFrame(list(doc_types.items()), columns=["Type", "Count"])
                        st.bar_chart(df_types, x="Type", y="Count")
                    else:
                        st.info("No document type data available")
                        
                with col_chart2:
                    st.markdown("#### Top Skills")
                    skills = data["insights"].get("top_skills", {})
                    if skills:
                        df_skills = pd.DataFrame(list(skills.items()), columns=["Skill", "Count"])
                        st.bar_chart(df_skills, x="Skill", y="Count")
                    else:
                        st.info("No skill data available")
            else:
                st.error("Failed to load analytics")
        except Exception as e:
            st.error(f"Could not connect to API: {e}")
    else:
        st.info("Click 'Refresh Analytics' to fetch latest data.")

st.divider()
st.caption("© Talent Screen Enterprise - RAG Reference Architecture")
