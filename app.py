import streamlit as st
import sqlite3
import google.generativeai as genai
import os
from datetime import datetime
import pandas as pd
import shutil

st.set_page_config(page_title="AI 경진대회 팀 관제실", page_icon="⚓", layout="wide")

# ====================== 팀 설정 ======================
TEAM_USERS = {
    "팀원A(하드웨어)": "1234",
    "팀원B(시각AI)": "5678",
    "팀원C(시스템총괄)": "0000"
}

ROLE_PROMPTS = {
    "코딩 도우미": "너는 파이썬 전문 시니어 개발자야. 요청한 기능을 바로 동작하는 코드로 짜줘. 코드는 ```python 블록으로 감싸고 사용법도 알려줘.",
    "에러 수정 전문가": "너는 디버깅 전문가야. 에러를 분석할 때 ## 원인, ## 수정 코드, ## 재발 방지 형식으로 답변해.",
    "문서 작성 도우미": "너는 기술 문서 전문 작가야. 경진대회 보고서에 바로 쓸 수 있게 깔끔한 마크다운으로 작성해."
}

DB_PATH = "team_data.db"
BACKUP_DIR = "backups"

# ====================== 자동 백업 ======================
def create_backup():
    if not os.path.exists(DB_PATH): return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    backup_path = os.path.join(BACKUP_DIR, f"team_data_{timestamp}.db")
    try:
        shutil.copy2(DB_PATH, backup_path)
        # 최근 10개만 유지
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith(".db")], reverse=True)
        for old in backups[10:]:
            os.remove(os.path.join(BACKUP_DIR, old))
    except:
        pass

# ====================== DB ======================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            ai_role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS shared_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            ai_role TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS starred_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tag TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            comment TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by TEXT NOT NULL,
            assigned_to TEXT NOT NULL,
            task TEXT NOT NULL,
            status TEXT DEFAULT 'todo',
            due_date TEXT,
            timestamp TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()

# ====================== Gemini ======================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ GEMINI_API_KEY가 설정되지 않았습니다.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

def call_gemini(history, ai_role):
    system = ROLE_PROMPTS.get(ai_role)
    msgs = [{"role": "user" if m["role"]=="user" else "model", "parts": [m["content"]]} for m in history]
    if msgs and msgs[-1]["role"] == "user":
        msgs[-1]["parts"][0] = system + "\n\n" + msgs[-1]["parts"][0]
    try:
        res = model.generate_content(msgs)
        return res.text
    except Exception as e:
        return f"API 오류: {e}"

# ====================== 기타 DB 함수 (간단 버전) ======================
def save_message(username, role, ai_role, content):
    conn = get_db()
    ts = datetime.now().isoformat()
    conn.execute("INSERT INTO chat_history (username,role,ai_role,content,timestamp) VALUES (?,?,?,?,?)",
                 (username, role, ai_role, content, ts))
    conn.commit()
    conn.close()

def get_chat_history(username):
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM chat_history WHERE username=? ORDER BY timestamp", conn, params=(username,))
    conn.close()
    return df.to_dict('records')

# ====================== 메인 앱 ======================
init_db()
create_backup()

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
    st.session_state.current_view = "main"

if st.session_state.logged_in_user is None:
    st.title("⚓ AI 경진대회 팀 관제실")
    username = st.selectbox("팀원 선택", TEAM_USERS.keys())
    pw = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if TEAM_USERS.get(username) == pw:
            st.session_state.logged_in_user = username
            st.rerun()
        else:
            st.error("비밀번호 틀림")
else:
    user = st.session_state.logged_in_user
    st.sidebar.markdown(f"**👤 {user}**")
    
    role = st.sidebar.radio("AI 역할 선택", ROLE_PROMPTS.keys())
    st.session_state.ai_role = role

    if st.sidebar.button("🚪 로그아웃"):
        st.session_state.logged_in_user = None
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["💬 AI 대화", "🔴 에러 분석", "📋 공유 현황"])

    with tab1:
        history = get_chat_history(user)
        for msg in history[-15:]:
            st.chat_message(msg["role"]).write(msg["content"])

        if prompt := st.chat_input("질문을 입력하세요..."):
            st.chat_message("user").write(prompt)
            save_message(user, "user", role, prompt)
            
            with st.spinner("AI 생각 중..."):
                response = call_gemini(history + [{"role":"user", "content":prompt}], role)
            
            st.chat_message("assistant").write(response)
            save_message(user, "assistant", role, response)

st.caption("자동 백업 포함 버전")