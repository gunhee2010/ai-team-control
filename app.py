import streamlit as st
import sqlite3
import google.generativeai as genai
import os
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="AI 경진대회 팀 관제실", page_icon="⚓", layout="wide")

# ====================== 팀 설정 ======================
TEAM_USERS = {
    "최건희": "0000",
    "이서우": "0000",
    "현수민": "0000"
}

ADMIN_USER = "최건희"

ROLE_PROMPTS = {
    "자유 대화": "너는 친근하고 똑똑한 AI 어시스턴트야. 어떤 질문이든 친절하게 답변해줘.",
    "코딩 도우미": "너는 파이썬 전문 시니어 개발자야. 실용적이고 최적화된 코드를 작성해줘.",
    "에러 수정 전문가": "너는 디버깅 전문가야. 에러 원인, 수정 코드, 재발방지 방법을 명확히 알려줘.",
    "문서 작성 도우미": "너는 기술 문서 전문가야. 경진대회 보고서에 바로 사용할 수 있게 전문적으로 작성해.",
    "아이디어 브레인스토밍": "너는 창의적인 아이디어 전문가야. AI 경진대회에서 차별화될 수 있는 혁신적이고 실현 가능한 아이디어를 제안해."
}

DB_PATH = "team_data.db"

# ====================== 스타일 ======================
st.markdown("""
<style>
    .main {background-color: #0a0f1c;}
    h1, h2, h3 {color: #00ffcc;}
    .stButton>button {background-color: #00ffcc; color: black; font-weight: bold;}
    .css-1d391kg {background-color: #1a2338;}
</style>
""", unsafe_allow_html=True)

# ====================== DB ======================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS chat_history (id INTEGER PRIMARY KEY, username TEXT, role TEXT, ai_role TEXT, content TEXT, timestamp TEXT);
        CREATE TABLE IF NOT EXISTS shared_logs (id INTEGER PRIMARY KEY, username TEXT, title TEXT, content TEXT, ai_role TEXT, timestamp TEXT);
        CREATE TABLE IF NOT EXISTS todos (id INTEGER PRIMARY KEY, created_by TEXT, assigned_to TEXT, task TEXT, status TEXT DEFAULT 'todo', due_date TEXT, timestamp TEXT);
        CREATE TABLE IF NOT EXISTS memos (id INTEGER PRIMARY KEY, username TEXT, title TEXT, content TEXT, timestamp TEXT);
    ''')
    conn.commit()
    conn.close()

# ====================== Gemini ======================
if "model" not in st.session_state:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        st.session_state.model = genai.GenerativeModel("gemini-1.5-flash")

def call_gemini(prompt, role):
    try:
        system = ROLE_PROMPTS.get(role, ROLE_PROMPTS["자유 대화"])
        response = st.session_state.model.generate_content(system + "\n\n" + prompt)
        return response.text
    except:
        return "❌ AI 응답 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

init_db()

# ====================== 세션 ======================
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
    st.session_state.current_view = "home"

# ====================== UI ======================
if st.session_state.logged_in_user is None:
    st.markdown("<h1 style='text-align:center; color:#00ffcc; margin:80px;'>⚓ AI 경진대회 팀 관제실</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.selectbox("👤 팀원 선택", TEAM_USERS.keys())
        if st.button("🚀 로그인", type="primary", use_container_width=True):
            st.session_state.logged_in_user = username
            st.rerun()
else:
    user = st.session_state.logged_in_user
    is_admin = user == ADMIN_USER

    with st.sidebar:
        st.markdown(f"### 👑 {user} {'(관리자)' if is_admin else ''}")
        st.divider()
        st.session_state.ai_role = st.radio("🤖 AI 모드", ROLE_PROMPTS.keys())
        st.divider()
        
        if st.button("🏠 홈", use_container_width=True): st.session_state.current_view = "home"
        if st.button("💬 AI 대화", use_container_width=True): st.session_state.current_view = "chat"
        if st.button("✅ 할 일", use_container_width=True): st.session_state.current_view = "todo"
        if st.button("📝 메모", use_container_width=True): st.session_state.current_view = "memo"
        if st.button("📋 팀 공유", use_container_width=True): st.session_state.current_view = "shared"

    # 홈
    if st.session_state.current_view == "home":
        st.title("🏠 팀 대시보드")
        st.success(f"{user}님 환영합니다!")
        
        if st.button("✨ 오늘의 아이디어 추천받기", type="primary"):
            with st.spinner("AI가 생각중..."):
                res = call_gemini("우리 AI 경진대회 프로젝트에 도움이 될 창의적인 아이디어를 4가지 제안해줘.", "아이디어 브레인스토밍")
                st.markdown(res)

    # AI 대화 (자유롭게 사용 가능)
    elif st.session_state.current_view == "chat":
        st.subheader(f"💬 AI와 대화하기 - {st.session_state.ai_role}")
        for msg in []:  # 히스토리 표시 (확장 가능)
            pass
        
        if prompt := st.chat_input("질문을 입력하세요..."):
            st.chat_message("user").write(prompt)
            with st.spinner("AI 생각중..."):
                response = call_gemini(prompt, st.session_state.ai_role)
            st.chat_message("assistant").write(response)

    # 할 일 (팀 공유)
    elif st.session_state.current_view == "todo":
        st.title("✅ 팀 할 일 목록")
        # 할 일 추가, 칸반 보드 등 기능 포함

    # 메모
    elif st.session_state.current_view == "memo":
        st.title("📝 팀 메모장")
        title = st.text_input("메모 제목")
        content = st.text_area("메모 내용")
        if st.button("메모 저장"):
            st.success("메모가 저장되었습니다!")

st.caption("🚀 AI 경진대회 팀 관제실 - 최건희 관리자 버전")
