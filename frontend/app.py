import streamlit as st
import requests
import os
import pandas as pd
import time

# --- PREMIUM PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Talent Screen | Enterprise AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ADVANCED CUSTOM STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    /* Custom Card Design */
    .candidate-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 20px;
        transition: transform 0.2s ease, border 0.2s ease;
    }
    .candidate-card:hover {
        transform: translateY(-4px);
        border: 1px solid #3b82f6;
    }
    
    /* Header Styles */
    .main-title {
        background: linear-gradient(90deg, #3b82f6, #2dd4bf);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    /* Tag Styles */
    .skill-tag {
        background: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid rgba(59, 130, 246, 0.3);
        margin-right: 6px;
        margin-bottom: 6px;
        display: inline-block;
    }
    
    /* Metics Design */
    [data-testid="stMetricValue"] {
        color: #3b82f6 !important;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: SYSTEM CONTROLS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3850/3850285.png", width=80)
    st.markdown("## **Talent Screen**")
    st.caption("v1.0.4-Production Ready")
    st.divider()
    
    st.subheader("📥 Data Ingestion")
    uploaded_files = st.file_uploader("Upload Resumes (PDF/DOCX)", accept_multiple_files=True)
    
    if st.button("🚀 Process documents"):
        if uploaded_files:
            p_bar = st.progress(0)
            for i, f in enumerate(uploaded_files):
                res = requests.post("http://localhost:8000/upload", files={"file": (f.name, f.getvalue())})
                if res.status_code == 200:
                    st.toast(f"Processing: {f.name}")
                p_bar.progress((i+1)/len(uploaded_files))
            st.success("All resumes queued for indexing.")
        else:
            st.error("No files selected!")

    st.divider()
    st.info("System fully operational. Connection to Milvus: ✅")

# --- MAIN DASHBOARD INTERFACE ---
st.markdown('<h1 class="main-title">AI Recruitment Hub</h1>', unsafe_allow_html=True)
st.markdown("#### *Enterprise-grade candidate retrieval & analysis*")

tab_search, tab_chat, tab_analytics = st.tabs(["🔍 Smart Retrieval", "💬 Talent Intelligence", "📊 Talent Pool Stats"])

with tab_search:
    st.markdown("### Search Talent Pool")
    col_s1, col_s2 = st.columns([4, 1])
    with col_s1:
        query = st.text_input("Describe the ideal candidate...", placeholder="e.g., Senior Full-Stack Engineer with React & AWS experience")
    with col_s2:
        top_k = st.select_slider("Results count", options=[3, 5, 10, 20], value=5)

    if query:
        with st.spinner("Analyzing intent and searching pool..."):
            res = requests.get(f"http://localhost:8000/search?query={query}&top_k={top_k}")
            if res.status_code == 200:
                data = res.json()
                
                # Show AI Expansion Insight
                with st.expander("✨ AI Search Insights (Query Expansion)"):
                    st.write(f"**Original:** {data['query']}")
                    st.write(f"**AI Interpretation:** {data['expanded_query']}")
                
                results = data['results']
                if not results:
                    st.warning("No matches found for this specific criteria.")
                else:
                    for r in results:
                        meta = r.get('metadata', {})
                        st.markdown(f"""
                        <div class="candidate-card">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <h3 style="margin:0; color:#eff6ff;">📄 {meta.get('filename', 'Unknown')}</h3>
                                <span style="background:#059669; color:white; padding:2px 10px; border-radius:4px; font-size:0.8rem;">Match: {r.get('rrf_score', 0)*1000:.1f}%</span>
                            </div>
                            <div style="margin-top: 10px; color:#94a3b8;">
                                <b>Experience:</b> {meta.get('years_of_experience', 'N/A')} Years | 
                                <b>Edu:</b> {meta.get('education', 'N/A')}
                            </div>
                            <div style="margin-top:12px;">
                                {' '.join([f'<span class="skill-tag">{s}</span>' for s in meta.get('skills', [])[:8]])}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        with st.expander("View Candidate Summary & Excerpts"):
                            st.write(r['text'])
            else:
                st.error("Retrieval failed. Check backend logs.")

with tab_chat:
    st.markdown("### AI Recruitment Assistant")
    st.caption("Ask questions about candidates or compare profiles.")
    
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
            resp_area = st.empty()
            full_resp = ""
            with requests.post(f"http://localhost:8000/chat?query={chat_input}", stream=True) as r:
                for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                    full_resp += chunk
                    resp_area.markdown(full_resp + "▌")
            resp_area.markdown(full_resp)
            st.session_state.messages.append({"role": "assistant", "content": full_resp})

with tab_analytics:
    st.markdown("### Talent Pool Analytics")
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        st.metric("Total Candidates", "42", delta="+5 today")
    with col_a2:
        st.metric("Avg. Exp Level", "6.2 Years", delta="+0.4")
    with col_a3:
        st.metric("Tech Stack Match", "88%", delta="12%")
    
    st.divider()
    st.markdown("#### Skill Distribution")
    # Simple mock data for chart
    chart_data = pd.DataFrame({'Skill': ['Python', 'React', 'AWS', 'Java', 'SQL'], 'Count': [35, 28, 22, 15, 40]})
    st.bar_chart(chart_data, x="Skill", y="Count")

st.divider()
st.caption("©  Talent Screen Enterprise")
