# =====================================================================
# ⚓ AI 팀 관제실 — 프로덕션급 통합 마스터 v5.0
# 원본 v4.0 전체 기능 유지 + 신규 기능 추가:
#   ① 실시간 디지털 시계 (st.fragment, 1초 갱신)
#   ② 사이드바 Up-Down 해킹 미니게임 위젯
#   ③ 실시간 팀 채팅 (st.fragment, 3초 자동 갱신)
#   ④ 아이디어 투표 게시판 (1인 1표 제한)
#   ⑤ DuckDuckGo 직접 연동 웹검색 (groq/compound-mini 제거)
#   ⑥ CSS 고대비 시인성 개선
#   ⑦ 프로젝트 진행률 게이지 바
#   ⑧ AI 할 일 자동 분할기
#   ⑨ 대회 제출용 마크다운 Export Hub
# =====================================================================

import streamlit as st
import sqlite3
from openai import OpenAI
from duckduckgo_search import DDGS
import os
import time
import random
from datetime import datetime
import pandas as pd

st.set_page_config(
    page_title="⚓ AI 팀 관제실",
    page_icon="⚓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== 설정 ======================
TEAM_USERS = {
    "최건희": "0909",
    "이서우": "0000",
    "현수민": "0000"
}
ADMIN_USER = "최건희"
DB_PATH    = "team_data.db"

ROLE_PROMPTS = {
    "🗣️ 자유 대화":            "너는 친근하고 똑똑한 AI 어시스턴트야. 어떤 질문이든 친절하고 명확하게 답변해줘. 한국어로 답변해.",
    "💻 코딩 도우미":           "너는 파이썬 전문 시니어 개발자야. 실용적이고 최적화된 코드를 작성해줘. 코드에는 항상 주석을 달고, 사용 예시도 포함해줘. 한국어로 설명해.",
    "🔧 에러 수정 전문가":      "너는 디버깅 전문가야. 에러 원인을 명확히 분석하고, 수정된 코드와 재발방지 방법을 순서대로 알려줘. 한국어로 답변해.",
    "📄 문서 작성 도우미":      "너는 기술 문서 전문가야. AI 경진대회 보고서에 바로 사용할 수 있게 전문적이고 구조적으로 작성해. 한국어로 작성해.",
    "💡 아이디어 브레인스토밍": "너는 창의적인 아이디어 전문가야. AI 경진대회에서 차별화될 수 있는 혁신적이고 실현 가능한 아이디어를 제안해. 각 아이디어의 장점과 구현 방법도 포함해. 한국어로 답변해.",
    "🔍 웹 검색 도우미":        "너는 최신 정보 검색 전문가야. 제공된 웹 검색 결과를 바탕으로 정확하고 유용한 정보를 정리해서 알려줘. 출처 URL도 함께 언급해줘. 한국어로 답변해."
}

MEMBER_COLORS = {
    "최건희": "#ff7b72",
    "이서우": "#79c0ff",
    "현수민": "#a5d6ff"
}

GROQ_MAX_RETRIES = 3
GROQ_BASE_DELAY  = 5


# ====================== CSS ======================
def inject_css():
    st.markdown("""
<style>
/* ════════════════════════════════════════════
   🎨 디자인 토큰
   ════════════════════════════════════════════ */
:root {
    --bg-base:      #0d1117;
    --bg-surface:   #161b27;
    --bg-elevated:  #1c2333;
    --bg-overlay:   #21262d;
    --border:       #21262d;
    --border-mid:   #30363d;
    --border-muted: #3a4149;
    --text-primary:  #f0f6fc;
    --text-secondary:#cdd9e5;
    --text-muted:    #8b949e;
    --text-faint:    #484f58;
    --accent:        #00ffcc;
    --accent-dim:    rgba(0, 255, 204, 0.18);
    --accent-glow:   rgba(0, 255, 204, 0.08);
    --blue:   #58a6ff;
    --purple: #bc8cff;
    --green:  #3fb950;
    --yellow: #e3b341;
    --red:    #f85149;
    --gold:   #f0d000;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --transition: 0.18s ease;
}

/* ════════════════════════════════════════════
   🏗️ 기본 레이아웃
   ════════════════════════════════════════════ */
.stApp {
    background-color: var(--bg-base);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
.main .block-container { padding: 2rem 2.5rem 5rem; max-width: 1280px; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ════════════════════════════════════════════
   🗂️ 사이드바
   ════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111826 0%, var(--bg-base) 100%);
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: transparent;
    color: var(--text-muted);
    border: 1px solid transparent;
    border-radius: var(--radius-md);
    text-align: left;
    padding: 0.55rem 1rem;
    margin: 1px 0;
    font-size: 0.9rem;
    transition: all var(--transition);
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--bg-elevated);
    color: var(--accent);
    border-color: var(--accent-dim);
    transform: translateX(3px);
}

/* ════════════════════════════════════════════
   🃏 카드
   ════════════════════════════════════════════ */
.card {
    background: var(--bg-surface);
    border: 1px solid var(--border-mid);
    border-radius: var(--radius-lg);
    padding: 1.1rem 1.4rem;
    margin: 0.45rem 0;
    transition: border-color var(--transition), box-shadow var(--transition);
}
.card:hover {
    border-color: rgba(0, 255, 204, 0.22);
    box-shadow: 0 6px 28px var(--accent-glow);
}
.card-accent  { border-left: 3px solid var(--accent); }
.card-blue    { border-left: 3px solid var(--blue); }
.card-purple  { border-left: 3px solid var(--purple); }
.card-pinned  {
    border-left: 3px solid var(--gold);
    background: linear-gradient(135deg, var(--bg-surface) 0%, #1c1e10 100%);
    box-shadow: 0 0 16px rgba(240, 208, 0, 0.06);
}

/* ── 메트릭 카드 ── */
.metric-card {
    background: linear-gradient(145deg, var(--bg-surface) 0%, #192133 100%);
    border: 1px solid var(--border-mid);
    border-radius: var(--radius-lg);
    padding: 1.3rem 0.8rem;
    text-align: center;
    transition: transform var(--transition), border-color var(--transition);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
}
.metric-card:hover { transform: translateY(-2px); border-color: rgba(0, 255, 204, 0.28); }
.metric-icon  { font-size: 1.4rem; margin-bottom: 0.15rem; }
.metric-value {
    font-size: 2rem; font-weight: 700; color: var(--accent);
    line-height: 1.15; margin: 0.2rem 0; letter-spacing: -0.02em;
}
.metric-label { font-size: 0.76rem; color: var(--text-muted); letter-spacing: 0.05em; text-transform: uppercase; }

/* ════════════════════════════════════════════
   🔘 버튼
   ════════════════════════════════════════════ */
.stButton > button {
    border-radius: var(--radius-md) !important;
    border: 1px solid var(--border-mid) !important;
    background: var(--bg-surface) !important;
    color: var(--text-secondary) !important;
    font-size: 0.875rem !important;
    min-height: 38px;
    transition: all var(--transition) !important;
}
.stButton > button:hover {
    border-color: var(--border-muted) !important;
    color: var(--text-primary) !important;
    background: var(--bg-elevated) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent) 0%, #00c4a0 100%) !important;
    color: var(--bg-base) !important;
    font-weight: 700 !important;
    border: none !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #00e6b8 0%, #00b090 100%) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 5px 18px rgba(0, 255, 204, 0.28) !important;
}

/* ════════════════════════════════════════════
   ✍️ 입력 필드 — 글자색 강제 강화
   ════════════════════════════════════════════ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-mid) !important;
    color: #ffffff !important;
    border-radius: var(--radius-md) !important;
    font-size: 0.9rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-dim) !important;
}
.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder { color: var(--text-faint) !important; }

/* ════════════════════════════════════════════
   🔤 타이포그래피 — 고대비 시인성
   ════════════════════════════════════════════ */
h1 {
    color: var(--accent) !important;
    font-size: 1.75rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 0.4rem !important;
    text-shadow: 0 0 12px rgba(0, 255, 204, 0.2) !important;
}
h2 { color: var(--text-primary) !important; font-weight: 600 !important; }
h3 { color: var(--text-secondary) !important; font-weight: 600 !important; }
p  { color: var(--text-secondary); line-height: 1.65; }

b, strong { color: var(--accent) !important; }

/* ════════════════════════════════════════════
   🏷️ 태그
   ════════════════════════════════════════════ */
.tag {
    display: inline-block;
    background: var(--bg-overlay);
    color: var(--blue);
    border: 1px solid var(--border-mid);
    border-radius: 99px;
    padding: 2px 10px;
    font-size: 0.72rem;
    font-weight: 500;
    margin: 2px;
}
.tag-green  { color: var(--green);  background: rgba(63,185,80,0.1);  border-color: rgba(63,185,80,0.25); }
.tag-orange { color: var(--yellow); background: rgba(227,179,65,0.1); border-color: rgba(227,179,65,0.25); }
.tag-red    { color: var(--red);    background: rgba(248,81,73,0.1);  border-color: rgba(248,81,73,0.25); }
.tag-gold   { color: var(--gold);   background: rgba(240,208,0,0.1);  border-color: rgba(240,208,0,0.28); }

/* ════════════════════════════════════════════
   ⚡ 활동 피드
   ════════════════════════════════════════════ */
.activity-item {
    display: flex; align-items: flex-start; gap: 0.75rem;
    padding: 0.7rem 0; border-bottom: 1px solid var(--border);
}
.activity-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--accent); margin-top: 7px; flex-shrink: 0;
    box-shadow: 0 0 7px rgba(0, 255, 204, 0.55);
}

/* ════════════════════════════════════════════
   📋 칸반
   ════════════════════════════════════════════ */
.kanban-header {
    font-weight: 700; margin-bottom: 0.9rem;
    padding: 0.55rem 0.9rem; border-radius: var(--radius-md);
    text-align: center; font-size: 0.88rem;
    letter-spacing: 0.06em; text-transform: uppercase;
}
.kh-todo  { background: var(--bg-overlay); color: var(--text-muted); border: 1px solid var(--border-mid); }
.kh-doing { background: rgba(30,58,95,0.5); color: #93c5fd; border: 1px solid rgba(30,90,160,0.4); }
.kh-done  { background: rgba(6,78,59,0.5);  color: #6ee7b7; border: 1px solid rgba(6,120,80,0.4); }
.task-card {
    background: var(--bg-surface); border: 1px solid var(--border-mid);
    border-radius: var(--radius-md); padding: 0.85rem 1rem; margin: 0.4rem 0;
    transition: border-color var(--transition), transform var(--transition);
}
.task-card:hover { border-color: rgba(88, 166, 255, 0.4); transform: translateY(-1px); }

/* ════════════════════════════════════════════
   🗂️ 탭
   ════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: transparent; border-bottom: 1px solid var(--border); gap: 0.3rem;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: var(--text-muted);
    border-radius: var(--radius-md) var(--radius-md) 0 0;
    padding: 0.55rem 1.2rem; font-size: 0.875rem;
    transition: color var(--transition), background var(--transition);
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text-primary); background: var(--bg-surface); }
.stTabs [aria-selected="true"] {
    background: var(--bg-surface) !important;
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    font-weight: 600;
}

/* ════════════════════════════════════════════
   💬 채팅 메시지 — 글자색 강제 보장
   ════════════════════════════════════════════ */
[data-testid="stChatMessage"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 1rem 1.2rem !important;
    margin: 0.5rem 0 !important;
}
[data-testid="stChatMessageUser"] {
    background: var(--bg-elevated) !important;
    border-color: var(--border-mid) !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] ol,
[data-testid="stChatMessage"] ul,
.stMarkdown p, .stMarkdown li, .stMarkdown strong {
    color: var(--text-primary) !important;
    font-size: 0.93rem;
    line-height: 1.65;
}

/* ════════════════════════════════════════════
   💻 코드 블록
   ════════════════════════════════════════════ */
code {
    background: var(--bg-overlay) !important;
    color: #ff7b72 !important;
    padding: 2px 6px !important;
    border-radius: var(--radius-sm) !important;
    font-size: 0.85rem !important;
}
pre code { color: var(--text-primary) !important; background: transparent !important; padding: 0 !important; }
pre {
    background: var(--bg-base) !important;
    border: 1px solid var(--border-mid) !important;
    border-radius: var(--radius-md) !important;
    padding: 1.1rem !important;
}

/* ════════════════════════════════════════════
   🔧 기타 컴포넌트
   ════════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: var(--bg-surface);
    border: 1px solid var(--border-mid);
    border-radius: var(--radius-md);
    margin: 0.4rem 0;
}
[data-testid="stDataFrame"] { border: 1px solid var(--border-mid); border-radius: var(--radius-md); overflow: hidden; }
[data-testid="stAlert"]     { border-radius: var(--radius-md) !important; background: #1c1820 !important; border-color: #443850 !important; }
hr { border-color: var(--border) !important; margin: 1.2rem 0 !important; }
.stSpinner > div { border-color: var(--accent) !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToggle"] label { color: var(--text-muted) !important; font-size: 0.875rem !important; }

/* ── 실시간 시계 박스 ── */
.clock-box {
    background: rgba(0, 255, 204, 0.04);
    border: 1px solid var(--accent-dim);
    border-radius: var(--radius-md);
    padding: 0.6rem 0.9rem;
    text-align: center;
    margin-bottom: 1rem;
}

/* ── 미니게임 박스 ── */
.game-box {
    background: var(--bg-surface);
    border: 1px solid var(--border-mid);
    border-radius: var(--radius-md);
    padding: 0.8rem;
    margin: 0.5rem 0;
}

/* ════════════════════════════════════════════
   📱 모바일 반응형 (≤ 768px)
   ════════════════════════════════════════════ */
@media (max-width: 768px) {
    .main .block-container { padding: 0.9rem 0.75rem 3.5rem !important; }
    h1 { font-size: 1.3rem !important; }
    .metric-card { padding: 1rem 0.5rem; }
    .metric-value { font-size: 1.65rem; }
    .card { padding: 0.85rem 0.9rem; }
    .task-card { padding: 0.65rem 0.8rem; margin: 0.3rem 0; }
    .stButton > button { min-height: 44px !important; font-size: 0.84rem !important; }
}
@media (max-width: 390px) {
    .main .block-container { padding: 0.6rem 0.4rem 2.5rem !important; }
    h1 { font-size: 1.1rem !important; }
    .metric-value { font-size: 1.4rem; }
}
</style>
""", unsafe_allow_html=True)


# ====================== DB ======================
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, ai_role TEXT, role TEXT, content TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS shared_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, title TEXT, content TEXT, ai_role TEXT, tags TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS shared_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER, username TEXT, content TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by TEXT, assigned_to TEXT, task TEXT,
            status TEXT DEFAULT "todo", priority TEXT DEFAULT "medium",
            due_date TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, title TEXT, content TEXT,
            is_shared INTEGER DEFAULT 0, is_pinned INTEGER DEFAULT 0, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS code_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, title TEXT, description TEXT,
            code TEXT, language TEXT, tags TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, action TEXT, detail TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS team_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, message TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS idea_board (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, title TEXT, description TEXT,
            votes INTEGER DEFAULT 0, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS idea_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER, username TEXT, vote_type TEXT,
            UNIQUE(idea_id, username)
        );
    ''')
    # memos 마이그레이션
    try:
        conn.execute("ALTER TABLE memos ADD COLUMN is_pinned INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    conn.commit()
    conn.close()


def log_activity(username, action, detail=""):
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO activity_log (username, action, detail, timestamp) VALUES (?,?,?,?)",
            (username, action, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        st.toast(f"⚠️ 활동 기록 실패 (DB 혼잡): {e}", icon="⚠️")


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ====================== AI (Groq + DuckDuckGo 직접 연동) ======================
def init_deepseek():
    if "deepseek_ready" not in st.session_state:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if api_key:
            st.session_state.deepseek_client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            st.session_state.deepseek_ready = True
        else:
            st.session_state.deepseek_ready = False


def call_deepseek(prompt: str, role: str, use_search: bool = False) -> str:
    """
    ⑤ 웹검색: groq/compound-mini 대신 DuckDuckGo 직접 크롤링 후 컨텍스트 주입
    모델은 llama-3.3-70b-versatile 단일 고정 (안정성 보장)
    """
    if not st.session_state.get("deepseek_ready"):
        return "⚠️ GROQ_API_KEY 환경변수가 설정되지 않았습니다. Render.com 환경변수를 확인해주세요."

    system = ROLE_PROMPTS.get(role, ROLE_PROMPTS["🗣️ 자유 대화"])
    model = "llama-3.3-70b-versatile"
    max_tokens = 4096

    # DuckDuckGo 직접 검색 — groq/compound-mini 의존성 완전 제거
    search_context = ""
    if use_search or role == "🔍 웹 검색 도우미":
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(prompt, max_results=3))
                if results:
                    search_context = "\n\n[실시간 웹 검색 결과]\n"
                    for idx, r in enumerate(results, 1):
                        search_context += (
                            f"{idx}. 제목: {r.get('title', '')}\n"
                            f"   내용: {r.get('body', '')}\n"
                            f"   출처: {r.get('href', '')}\n\n"
                        )
                else:
                    search_context = "\n\n[웹 검색 결과 없음 — 기존 지식으로 답변]\n"
        except Exception as e:
            search_context = f"\n\n[웹 검색 오류: {str(e)}]\n"

        prompt = f"{search_context}\n사용자 질문: {prompt}\n\n위 웹 검색 결과를 최우선으로 참조하여 출처 URL과 함께 한국어로 답변하세요."

    delay = GROQ_BASE_DELAY
    for attempt in range(1, GROQ_MAX_RETRIES + 1):
        try:
            response = st.session_state.deepseek_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": prompt}
                ],
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "rate limit" in err_str.lower()
            if is_rate_limit and attempt < GROQ_MAX_RETRIES:
                st.toast(f"⏳ API 한도 초과 — {delay}초 후 재시도... ({attempt}/{GROQ_MAX_RETRIES})", icon="⏳")
                time.sleep(delay)
                delay *= 2
            else:
                return f"❌ AI 응답 오류 ({attempt}회 시도): {err_str}"
    return "❌ AI 응답 실패: 최대 재시도 횟수를 초과했습니다."


def call_gemini(prompt: str, role: str, use_search: bool = False) -> str:
    return call_deepseek(prompt, role, use_search)


def purge_error_messages(messages: list) -> list:
    cleaned = []
    skip_next_user = False
    for msg in messages:
        if skip_next_user and msg["role"] == "user":
            skip_next_user = False
            continue
        is_error = msg["role"] == "assistant" and (
            msg["content"].startswith("❌") or msg["content"].startswith("⚠️")
        )
        if is_error:
            skip_next_user = False
            continue
        cleaned.append(msg)
    return cleaned


# ====================== 헬퍼 ======================
def member_badge(name):
    color = MEMBER_COLORS.get(name, "#8b949e")
    icon  = "👑" if name == ADMIN_USER else "🧑‍💻"
    return f"<span style='color:{color}; font-weight:600;'>{icon} {name}</span>"


def priority_badge(p):
    mapping = {
        "🔴 높음": ("#f85149", "높음"),
        "🟡 중간": ("#e3b341", "중간"),
        "🟢 낮음": ("#3fb950", "낮음"),
    }
    color, label = mapping.get(p, ("#8b949e", p))
    return f"<span style='color:{color}; font-size:0.75rem; font-weight:600;'>● {label}</span>"


# ====================== ① 실시간 디지털 시계 ======================
@st.fragment(run_every=1.0)
def render_realtime_clock():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(
        f"""<div class='clock-box'>
            <span style='color:#8b949e;font-size:0.68rem;letter-spacing:0.1em;display:block;font-weight:600;'>
                ⚓ MISSION CONTROL</span>
            <span style='color:var(--accent);font-size:1.15rem;font-family:"Courier New",monospace;
                         font-weight:700;text-shadow:0 0 8px rgba(0,255,204,0.4);'>
                {now_str}</span>
        </div>""",
        unsafe_allow_html=True
    )


# ====================== ② 사이드바 Up-Down 해킹 미니게임 ======================
def render_mini_game():
    st.markdown(
        "<p style='color:#8b949e;font-size:0.72rem;letter-spacing:0.08em;margin:0.3rem 0;'>🎮 HACK MINI-GAME</p>",
        unsafe_allow_html=True
    )

    if "g_target" not in st.session_state:
        st.session_state.g_target   = random.randint(1, 100)
        st.session_state.g_tries    = 0
        st.session_state.g_max      = 7
        st.session_state.g_log      = []
        st.session_state.g_status   = "playing"

    remaining = st.session_state.g_max - st.session_state.g_tries

    if st.session_state.g_status == "playing":
        st.markdown(
            f"<p style='font-size:0.78rem;color:#8b949e;margin:2px 0;'>"
            f"1~100 암호 해독 | 남은 기회: <b style='color:var(--accent);'>{remaining}</b>회</p>",
            unsafe_allow_html=True
        )
        with st.form("mini_game_form", clear_on_submit=True):
            guess = st.number_input("", min_value=1, max_value=100, step=1,
                                    value=50, label_visibility="collapsed")
            if st.form_submit_button("⚡ 인젝트", use_container_width=True):
                st.session_state.g_tries += 1
                if guess == st.session_state.g_target:
                    st.session_state.g_status = "won"
                    st.session_state.g_log.append(f"🎯 [{guess}] ACCESS GRANTED!")
                elif st.session_state.g_tries >= st.session_state.g_max:
                    st.session_state.g_status = "lost"
                    st.session_state.g_log.append(f"💥 [{guess}] LOCKOUT (정답:{st.session_state.g_target})")
                elif guess < st.session_state.g_target:
                    st.session_state.g_log.append(f"🔼 [{guess}] UP")
                else:
                    st.session_state.g_log.append(f"🔽 [{guess}] DOWN")
                st.rerun()
    elif st.session_state.g_status == "won":
        st.success(f"🔓 클리어! {st.session_state.g_tries}회 만에 성공")
        if st.button("🔄 재시작", key="game_reset_won", use_container_width=True):
            for k in ["g_target", "g_tries", "g_max", "g_log", "g_status"]:
                st.session_state.pop(k, None)
            st.rerun()
    else:
        st.error(f"💀 실패! 정답: {st.session_state.g_target}")
        if st.button("🔄 재시작", key="game_reset_lost", use_container_width=True):
            for k in ["g_target", "g_tries", "g_max", "g_log", "g_status"]:
                st.session_state.pop(k, None)
            st.rerun()

    # 로그 출력
    if st.session_state.get("g_log"):
        log_html = "<div style='font-family:monospace;font-size:0.73rem;margin-top:4px;'>"
        for line in reversed(st.session_state.g_log[-4:]):
            if "GRANTED" in line:
                color = "#3fb950"
            elif "UP" in line:
                color = "#e3b341"
            elif "LOCKOUT" in line:
                color = "#f85149"
            else:
                color = "#8b949e"
            log_html += f"<div style='color:{color};'>{line}</div>"
        log_html += "</div>"
        st.markdown(log_html, unsafe_allow_html=True)


# ====================== 페이지: 홈 ======================
def page_home(user, is_admin):
    hour = datetime.now().hour
    if   hour < 6 or hour >= 22: greet = "🌙 좋은 밤이에요"
    elif hour < 12:               greet = "🌅 좋은 아침이에요"
    else:                         greet = "☀️ 좋은 오후예요"

    color = MEMBER_COLORS.get(user, "#00ffcc")
    st.markdown("<h1>🏠 팀 대시보드</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:#8b949e;font-size:1rem;margin-bottom:1.5rem;'>"
        f"{greet}, <b style='color:{color};'>{user}</b>님! POSCO DX 7회 AI 청소년 챌린지 화이팅! 🚀</p>",
        unsafe_allow_html=True
    )

    # ── 메트릭 ──
    conn    = get_db()
    todo_n  = conn.execute("SELECT COUNT(*) FROM todos WHERE status='todo'").fetchone()[0]
    doing_n = conn.execute("SELECT COUNT(*) FROM todos WHERE status='doing'").fetchone()[0]
    done_n  = conn.execute("SELECT COUNT(*) FROM todos WHERE status='done'").fetchone()[0]
    shared_n= conn.execute("SELECT COUNT(*) FROM shared_logs").fetchone()[0]
    code_n  = conn.execute("SELECT COUNT(*) FROM code_library").fetchone()[0]
    conn.close()

    m1, m2, m3, m4, m5 = st.columns(5)
    for col, icon, val, label in [
        (m1, "📋", todo_n,   "대기 중"),
        (m2, "⚡", doing_n,  "진행 중"),
        (m3, "✅", done_n,   "완료"),
        (m4, "📤", shared_n, "공유 로그"),
        (m5, "💾", code_n,   "코드 저장"),
    ]:
        with col:
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='metric-icon'>{icon}</div>"
                f"<div class='metric-value'>{val}</div>"
                f"<div class='metric-label'>{label}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    # ⑦ 프로젝트 진행률 게이지
    total_tasks = todo_n + doing_n + done_n
    progress_pct = int(done_n / total_tasks * 100) if total_tasks > 0 else 0
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"""<div class='card card-accent' style='padding:1rem 1.4rem;'>
            <div style='display:flex;justify-content:space-between;margin-bottom:0.5rem;'>
                <span style='color:var(--text-secondary);font-weight:600;font-size:0.9rem;'>📊 프로젝트 전체 진행률</span>
                <span style='color:var(--accent);font-weight:700;'>{progress_pct}% ({done_n}/{total_tasks} 완료)</span>
            </div>
            <div style='background:var(--bg-overlay);border-radius:99px;height:10px;overflow:hidden;border:1px solid var(--border-mid);'>
                <div style='background:linear-gradient(90deg,var(--accent) 0%,#00c4a0 100%);
                            width:{progress_pct}%;height:100%;transition:width 0.5s ease;'></div>
            </div>
        </div>""",
        unsafe_allow_html=True
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # 팀 활동 차트
    conn = get_db()
    act_rows = conn.execute(
        "SELECT username, COUNT(*) as cnt FROM activity_log GROUP BY username"
    ).fetchall()
    conn.close()
    if act_rows:
        act_df = pd.DataFrame([{"팀원": r["username"], "활동 수": r["cnt"]} for r in act_rows]).set_index("팀원")
        st.markdown("### 📊 팀원별 누적 활동")
        st.bar_chart(act_df, color="#00ffcc", height=180)

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([2, 1])

    with left:
        st.markdown("### ⚡ 최근 팀 활동")
        conn = get_db()
        acts = conn.execute(
            "SELECT username, action, detail, timestamp FROM activity_log ORDER BY id DESC LIMIT 10"
        ).fetchall()
        conn.close()
        if acts:
            html = ""
            for a in acts:
                c = MEMBER_COLORS.get(a["username"], "#8b949e")
                detail_part = (f"<span style='color:#6e7681;font-size:0.8rem;display:block;'>{a['detail']}</span>"
                               if a["detail"] else "")
                ts_part = f"<span style='color:#484f58;font-size:0.72rem;'>{a['timestamp']}</span>"
                html += (
                    f"<div class='activity-item'>"
                    f"<div class='activity-dot'></div>"
                    f"<div style='min-width:0;'>"
                    f"<span style='color:{c};font-weight:600;'>{a['username']}</span>"
                    f"<span style='color:#8b949e;'> · {a['action']}</span>"
                    f"{detail_part}<div>{ts_part}</div>"
                    f"</div></div>"
                )
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown(
                "<p style='color:#484f58;text-align:center;margin-top:2rem;'>아직 활동이 없습니다. 팀을 시작해보세요! 🚀</p>",
                unsafe_allow_html=True
            )

        st.markdown("### 📋 현재 진행 중인 할 일")
        conn = get_db()
        doing = conn.execute(
            "SELECT * FROM todos WHERE status='doing' ORDER BY timestamp DESC LIMIT 5"
        ).fetchall()
        conn.close()
        if doing:
            for t in doing:
                mc = MEMBER_COLORS.get(t["assigned_to"], "#8b949e")
                st.markdown(
                    f"<div class='card' style='padding:0.7rem 1rem;margin:0.3rem 0;'>"
                    f"<span style='color:#e3b341;font-size:0.75rem;'>⚡ 진행 중</span>"
                    f"<span style='float:right;color:{mc};font-size:0.8rem;font-weight:600;'>{t['assigned_to']}</span>"
                    f"<div style='margin-top:0.3rem;color:#e6edf3;font-size:0.9rem;'>{t['task']}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown("<p style='color:#484f58;font-size:0.85rem;'>진행 중인 할 일이 없습니다.</p>",
                        unsafe_allow_html=True)

    with right:
        st.markdown("### 💡 AI 아이디어 추천")
        st.markdown(
            "<p style='color:#8b949e;font-size:0.85rem;margin-bottom:0.8rem;'>"
            "경진대회에 도움이 될 창의적인 아이디어를 AI가 추천해드려요</p>",
            unsafe_allow_html=True
        )
        if st.button("✨ 새 아이디어 받기", type="primary", use_container_width=True, key="home_idea_btn"):
            with st.spinner("🤖 AI가 아이디어를 생각하고 있어요..."):
                result = call_gemini(
                    "POSCO DX AI 청소년 챌린지 경진대회 프로젝트에 도움이 될 창의적이고 혁신적인 아이디어 3가지를 추천해줘. "
                    "각 아이디어마다 ①핵심 개요 ②주요 기능 ③차별점 순서로 간결하게 설명해줘.",
                    "💡 아이디어 브레인스토밍"
                )
                st.session_state.home_idea = result
                log_activity(user, "AI 아이디어 추천", "홈 대시보드")

        if "home_idea" in st.session_state:
            st.markdown(
                f"<div class='card card-accent' style='margin-top:0.8rem;'>"
                f"<p style='font-size:0.83rem;color:#cdd9e5;white-space:pre-wrap;margin:0;'>"
                f"{st.session_state.home_idea}</p></div>",
                unsafe_allow_html=True
            )

        st.markdown("### 👥 팀원 현황")
        members = [("최건희", "👑"), ("이서우", "🧑‍💻"), ("현수민", "🧑‍🎨")]
        for name, icon in members:
            c    = MEMBER_COLORS.get(name, "#8b949e")
            conn = get_db()
            last = conn.execute(
                "SELECT timestamp FROM activity_log WHERE username=? ORDER BY id DESC LIMIT 1", (name,)
            ).fetchone()
            conn.close()
            last_t = last["timestamp"][11:16] if last else "—"
            admin_badge = ("<span style='background:#1c3a2a;color:#3fb950;font-size:0.7rem;"
                          "border-radius:4px;padding:1px 6px;float:right;'>관리자</span>"
                          if name == ADMIN_USER else "")
            st.markdown(
                f"<div class='card' style='padding:0.65rem 1rem;margin:0.25rem 0;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                f"<span style='color:{c};font-weight:600;'>{icon} {name}</span>{admin_badge}"
                f"</div>"
                f"<div style='color:#484f58;font-size:0.75rem;margin-top:0.2rem;'>마지막 활동 {last_t}</div>"
                f"</div>",
                unsafe_allow_html=True
            )


# ====================== 페이지: AI 대화 ======================
def page_chat(user):
    role = st.session_state.get("ai_role", "🗣️ 자유 대화")

    st.markdown(
        f"<h1>💬 AI 대화 <span style='font-size:0.9rem;color:#8b949e;'>— {role}</span></h1>",
        unsafe_allow_html=True
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_role" not in st.session_state:
        st.session_state.chat_role = role
    if st.session_state.chat_role != role:
        st.session_state.messages = []
        st.session_state.chat_role = role

    c1, c2, c3, c4 = st.columns([1, 1, 1, 3])
    with c1:
        if st.button("🗑️ 초기화", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with c2:
        if st.button("💾 전체 저장", use_container_width=True):
            if st.session_state.messages:
                conn = get_db()
                for m in st.session_state.messages:
                    conn.execute(
                        "INSERT INTO chat_history (username,ai_role,role,content,timestamp) VALUES (?,?,?,?,?)",
                        (user, role, m["role"], m["content"], ts())
                    )
                conn.commit()
                conn.close()
                log_activity(user, "대화 기록 저장", role)
                st.success("저장 완료!")
            else:
                st.info("대화 내용이 없습니다.")
    with c3:
        if st.button("📋 기록 보기", use_container_width=True):
            st.session_state.show_history = not st.session_state.get("show_history", False)

    use_search = st.toggle(
        "🔍 웹 검색 사용 (최신 정보가 필요할 때 켜세요)",
        value=(role == "🔍 웹 검색 도우미"),
        key="web_search_toggle"
    )
    if use_search:
        st.markdown(
            "<div style='background:rgba(0,255,204,0.06);border:1px solid rgba(0,255,204,0.2);"
            "border-radius:8px;padding:0.4rem 0.9rem;margin-bottom:0.5rem;font-size:0.82rem;"
            "color:#00ffcc;'>🌐 DuckDuckGo 웹 검색 활성화 — 최신 정보를 실시간 검색합니다</div>",
            unsafe_allow_html=True
        )

    if st.session_state.get("show_history"):
        with st.expander("📋 저장된 대화 기록", expanded=True):
            conn = get_db()
            hist = conn.execute(
                "SELECT * FROM chat_history WHERE username=? ORDER BY id DESC LIMIT 30", (user,)
            ).fetchall()
            conn.close()
            if hist:
                for h in hist:
                    icon = "🧑" if h["role"] == "user" else "🤖"
                    st.markdown(
                        f"<div style='background:#161b27;border-radius:8px;padding:0.5rem 0.8rem;"
                        f"margin:0.2rem 0;font-size:0.82rem;'>"
                        f"<span style='color:#8b949e;'>{icon} {h['timestamp'][:16]}</span><br>"
                        f"<span style='color:#cdd9e5;'>{h['content'][:200]}{'...' if len(h['content'])>200 else ''}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.info("저장된 대화가 없습니다.")

    st.markdown("<hr>", unsafe_allow_html=True)

    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
                bc1, bc2, bc3 = st.columns([1, 1, 4])
                with bc1:
                    if st.button("📤 팀 공유", key=f"share_{i}", use_container_width=True):
                        conn = get_db()
                        title_str = f"[{role}] {datetime.now().strftime('%m/%d %H:%M')} — {user}"
                        conn.execute(
                            "INSERT INTO shared_logs (username,title,content,ai_role,tags,timestamp) VALUES (?,?,?,?,?,?)",
                            (user, title_str, msg["content"], role, "", ts())
                        )
                        conn.commit()
                        conn.close()
                        log_activity(user, "AI 대화 공유", role)
                        st.success("✅ 팀에 공유됨!")
                with bc2:
                    if st.button("💾 코드 저장", key=f"code_{i}", use_container_width=True):
                        st.session_state.pending_code = msg["content"]
                        st.session_state.current_view = "code_library"
                        st.rerun()

    if prompt := st.chat_input(f"{role}에게 메시지를 보내세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        clean_ctx = purge_error_messages(st.session_state.messages)
        ctx_text  = "\n".join(
            [f"[{'사용자' if m['role']=='user' else 'AI'}] {m['content']}"
             for m in clean_ctx[-10:]]
        )
        full_prompt = f"이전 대화:\n{ctx_text}\n\n현재 질문:\n{prompt}" if len(clean_ctx) > 1 else prompt

        with st.spinner("🤖 AI가 생각하고 있어요..."):
            response = call_gemini(full_prompt, role, use_search=use_search)

        st.session_state.messages.append({"role": "assistant", "content": response})
        conn = get_db()
        conn.execute(
            "INSERT INTO chat_history (username,ai_role,role,content,timestamp) VALUES (?,?,?,?,?)",
            (user, role, "user", prompt, ts())
        )
        conn.execute(
            "INSERT INTO chat_history (username,ai_role,role,content,timestamp) VALUES (?,?,?,?,?)",
            (user, role, "assistant", response, ts())
        )
        conn.commit()
        conn.close()
        log_activity(user, "AI 대화", role)
        st.rerun()


# ====================== 페이지: 할 일 (칸반) ======================
def page_todo(user, is_admin):
    st.markdown("<h1>✅ 팀 할 일 — 칸반 보드</h1>", unsafe_allow_html=True)

    with st.expander("➕ 새 할 일 추가", expanded=False):
        r1c1, r1c2, r1c3 = st.columns([3, 1, 1])
        with r1c1:
            new_task = st.text_input("할 일 내용", placeholder="예: Gemini API 연동 테스트하기")
        with r1c2:
            assigned = st.selectbox("담당자", list(TEAM_USERS.keys()))
        with r1c3:
            priority = st.selectbox("우선순위", ["🔴 높음", "🟡 중간", "🟢 낮음"])
        r2c1, _ = st.columns([1, 3])
        with r2c1:
            due_date = st.date_input("마감일", value=None)
        if st.button("➕ 추가하기", type="primary"):
            if new_task.strip():
                conn = get_db()
                conn.execute(
                    "INSERT INTO todos (created_by,assigned_to,task,status,priority,due_date,timestamp) VALUES (?,?,?,?,?,?,?)",
                    (user, assigned, new_task.strip(), "todo", priority, str(due_date) if due_date else "", ts())
                )
                conn.commit()
                conn.close()
                log_activity(user, "할 일 추가", new_task[:30])
                st.success("✅ 할 일이 추가됐습니다!")
                st.rerun()
            else:
                st.error("할 일 내용을 입력해주세요.")

    # ⑧ AI 할 일 자동 분할기
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("### 🤖 AI 거대 목표 자동 분할기")
    st.markdown(
        "<p style='color:#8b949e;font-size:0.85rem;margin-bottom:0.5rem;'>"
        "큰 목표를 입력하면 AI가 실행 가능한 3개의 세부 할 일로 나눠 칸반에 자동 등록합니다.</p>",
        unsafe_allow_html=True
    )
    ai_col1, ai_col2 = st.columns([3, 1])
    with ai_col1:
        ai_objective = st.text_input("🎯 거대 목표 입력", placeholder="예: 데이터 파이프라인 구축 및 모델 학습 실험", key="ai_todo_obj")
    with ai_col2:
        ai_assignee = st.selectbox("담당자", list(TEAM_USERS.keys()), key="ai_todo_assign")
    if st.button("✨ AI로 세부 할 일 자동 생성", type="primary", use_container_width=True):
        if ai_objective.strip():
            with st.spinner("🤖 AI가 목표를 분석하여 할 일을 생성하고 있어요..."):
                breakdown_prompt = (
                    f"우리는 POSCO DX AI 청소년 챌린지를 준비하는 팀이야. "
                    f"거대 목표 '{ai_objective}'를 오늘 바로 실행 가능한 구체적인 하위 태스크 3개로 쪼개줘. "
                    f"다른 설명은 전혀 하지 말고, 오직 각 줄마다 하나의 태스크명만 정확히 3줄로만 작성해줘."
                )
                ai_res = call_deepseek(breakdown_prompt, "💻 코딩 도우미")
                lines = [l.strip() for l in ai_res.split("\n") if l.strip()]
                conn = get_db()
                count = 0
                for line in lines:
                    if count >= 3:
                        break
                    clean = line
                    if len(clean) > 2 and clean[0].isdigit() and clean[1] in ".):":
                        clean = clean[2:].strip()
                    if clean.startswith(("-", "*", "•")):
                        clean = clean[1:].strip()
                    if clean:
                        conn.execute(
                            "INSERT INTO todos (created_by,assigned_to,task,status,priority,due_date,timestamp) "
                            "VALUES (?,?,?,?,?,?,?)",
                            (user, ai_assignee, f"[AI분할] {clean}", "todo", "🟡 중간",
                             datetime.now().strftime("%Y-%m-%d"), ts())
                        )
                        count += 1
                conn.commit()
                conn.close()
                log_activity(user, "AI 할 일 자동 분할", ai_objective[:30])
                st.success(f"✅ '{ai_objective}'를 {count}개 세부 할 일로 분할하여 칸반에 등록했습니다!")
                st.rerun()
        else:
            st.error("목표 내용을 입력해주세요.")

    st.markdown("<br>", unsafe_allow_html=True)

    conn      = get_db()
    all_todos = conn.execute("SELECT * FROM todos ORDER BY timestamp DESC").fetchall()
    conn.close()

    col_todo, col_doing, col_done = st.columns(3)

    def render_column(col, status, header_class, header_label):
        tasks = [t for t in all_todos if t["status"] == status]
        with col:
            st.markdown(
                f"<div class='kanban-header {header_class}'>"
                f"{header_label} <span style='opacity:0.7;'>({len(tasks)})</span></div>",
                unsafe_allow_html=True
            )
            for task in tasks:
                mc = MEMBER_COLORS.get(task["assigned_to"], "#8b949e")
                due_html = (f"<span style='color:#484f58;font-size:0.72rem;'>📅 {task['due_date']}</span><br>"
                            if task["due_date"] else "")
                st.markdown(
                    f"<div class='task-card'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
                    f"{priority_badge(task['priority'])}"
                    f"<span style='color:{mc};font-size:0.75rem;font-weight:600;'>{task['assigned_to']}</span>"
                    f"</div>"
                    f"<div style='margin:0.25rem 0 0.4rem;font-size:0.88rem;color:#e6edf3;'>{task['task']}</div>"
                    f"{due_html}"
                    f"</div>",
                    unsafe_allow_html=True
                )
                btn_map = {
                    "todo":  [("⚡ 시작", "doing")],
                    "doing": [("↩ 되돌리기", "todo"), ("✅ 완료", "done")],
                    "done":  [("↩ 재개", "doing")],
                }
                btns  = btn_map.get(status, [])
                extra = 1 if (is_admin or task["created_by"] == user) else 0
                bcols = st.columns(len(btns) + extra)
                for i, (lbl, ns) in enumerate(btns):
                    with bcols[i]:
                        if st.button(lbl, key=f"mv_{task['id']}_{ns}", use_container_width=True):
                            conn = get_db()
                            conn.execute("UPDATE todos SET status=? WHERE id=?", (ns, task["id"]))
                            conn.commit()
                            conn.close()
                            log_activity(user, "할 일 상태 변경", f"{task['task'][:20]} → {ns}")
                            st.rerun()
                if is_admin or task["created_by"] == user:
                    with bcols[-1]:
                        if st.button("🗑️", key=f"del_todo_{task['id']}", use_container_width=True):
                            conn = get_db()
                            conn.execute("DELETE FROM todos WHERE id=?", (task["id"],))
                            conn.commit()
                            conn.close()
                            log_activity(user, "할 일 삭제", task["task"][:20])
                            st.rerun()

    render_column(col_todo,  "todo",  "kh-todo",  "📋 할 일")
    render_column(col_doing, "doing", "kh-doing", "⚡ 진행 중")
    render_column(col_done,  "done",  "kh-done",  "✅ 완료")


# ====================== 페이지: 메모 ======================
def page_memo(user, is_admin):
    st.markdown("<h1>📝 팀 메모장</h1>", unsafe_allow_html=True)

    tab_write, tab_list = st.tabs(["✍️ 새 메모 작성", "📋 메모 목록"])

    with tab_write:
        title   = st.text_input("제목", placeholder="메모 제목을 입력하세요")
        content = st.text_area("내용", placeholder="메모 내용을 자유롭게 작성하세요...", height=280)
        mc1, mc2 = st.columns([1, 1])
        with mc1:
            is_shared = st.checkbox("👥 팀 전체 공개")
        with mc2:
            is_pinned_new = st.checkbox("📌 상단 고정")
        if st.button("💾 저장하기", type="primary"):
            if title.strip() and content.strip():
                conn = get_db()
                conn.execute(
                    "INSERT INTO memos (username,title,content,is_shared,is_pinned,timestamp) VALUES (?,?,?,?,?,?)",
                    (user, title.strip(), content.strip(),
                     1 if is_shared else 0,
                     1 if is_pinned_new else 0, ts())
                )
                conn.commit()
                conn.close()
                log_activity(user, "메모 저장", title[:30])
                st.success("✅ 메모가 저장되었습니다!")
                st.rerun()
            else:
                st.error("제목과 내용을 모두 입력해주세요.")

    with tab_list:
        conn = get_db()
        if is_admin:
            memos = conn.execute(
                "SELECT * FROM memos ORDER BY is_pinned DESC, id DESC"
            ).fetchall()
        else:
            memos = conn.execute(
                "SELECT * FROM memos WHERE username=? OR is_shared=1 ORDER BY is_pinned DESC, id DESC",
                (user,)
            ).fetchall()
        conn.close()

        if not memos:
            st.markdown(
                "<p style='color:#484f58;text-align:center;margin-top:4rem;font-size:1rem;'>📭 아직 메모가 없습니다</p>",
                unsafe_allow_html=True
            )
            return

        search = st.text_input("🔍 메모 검색", placeholder="제목이나 내용으로 검색...")
        if search:
            memos = [m for m in memos if search.lower() in (m["title"] + m["content"]).lower()]

        for memo in memos:
            c       = MEMBER_COLORS.get(memo["username"], "#8b949e")
            vis     = "🌐 공개" if memo["is_shared"] else "🔒 나만"
            pinned  = memo["is_pinned"]
            pin_tag = "<span class='tag tag-gold'>📌 고정</span>" if pinned else ""
            card_cls= "card-pinned" if pinned else "card-accent"

            with st.expander(
                f"{'📌 ' if pinned else ''}{vis}  {memo['title']}  ·  {memo['username']}  ·  {memo['timestamp'][:10]}"
            ):
                st.markdown(
                    f"<div class='card {card_cls}' style='padding:0.8rem 1rem;'>"
                    f"{pin_tag}"
                    f"<p style='color:#cdd9e5;white-space:pre-wrap;line-height:1.6;margin-top:0.5rem;'>"
                    f"{memo['content']}</p></div>",
                    unsafe_allow_html=True
                )
                act1, act2, act3 = st.columns([1, 1, 3])
                if is_admin or memo["username"] == user:
                    with act1:
                        pin_label = "📌 고정 해제" if pinned else "📌 고정하기"
                        if st.button(pin_label, key=f"pin_memo_{memo['id']}", use_container_width=True):
                            conn = get_db()
                            conn.execute("UPDATE memos SET is_pinned=? WHERE id=?",
                                         (0 if pinned else 1, memo["id"]))
                            conn.commit()
                            conn.close()
                            log_activity(user, "메모 핀 토글", memo["title"][:20])
                            st.rerun()
                    with act2:
                        if st.button("🗑️ 삭제", key=f"del_memo_{memo['id']}", use_container_width=True):
                            conn = get_db()
                            conn.execute("DELETE FROM memos WHERE id=?", (memo["id"],))
                            conn.commit()
                            conn.close()
                            log_activity(user, "메모 삭제", memo["title"][:20])
                            st.rerun()


# ====================== 페이지: 공유 로그 ======================
def page_shared(user, is_admin):
    st.markdown("<h1>📋 팀 공유 로그</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#8b949e;font-size:0.88rem;margin-bottom:1rem;'>"
        "AI 대화 결과, 코드, 아이디어를 팀과 나눠보세요</p>",
        unsafe_allow_html=True
    )
    conn = get_db()
    logs = conn.execute("SELECT * FROM shared_logs ORDER BY id DESC").fetchall()
    conn.close()

    if not logs:
        st.markdown(
            "<div style='text-align:center;margin-top:5rem;'>"
            "<p style='color:#484f58;font-size:1.1rem;'>📭 공유된 내용이 없습니다</p>"
            "<p style='color:#484f58;font-size:0.85rem;'>AI 대화 화면에서 결과를 팀에 공유해보세요!</p>"
            "</div>",
            unsafe_allow_html=True
        )
        return

    for log in logs:
        c = MEMBER_COLORS.get(log["username"], "#8b949e")
        with st.expander(f"📌 {log['title']}  ·  {log['timestamp'][:16]}"):
            st.markdown(
                f"<div class='card card-accent'>"
                f"<div style='display:flex;gap:0.8rem;align-items:center;margin-bottom:0.8rem;flex-wrap:wrap;'>"
                f"{member_badge(log['username'])}"
                f"<span class='tag'>{log['ai_role']}</span>"
                f"<span style='color:#484f58;font-size:0.78rem;'>{log['timestamp']}</span>"
                f"</div>"
                f"<div style='color:#cdd9e5;white-space:pre-wrap;line-height:1.6;font-size:0.88rem;'>{log['content']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

            conn     = get_db()
            comments = conn.execute(
                "SELECT * FROM shared_comments WHERE log_id=? ORDER BY id", (log["id"],)
            ).fetchall()
            conn.close()

            if comments:
                st.markdown("**💬 댓글**")
                for cm in comments:
                    cc = MEMBER_COLORS.get(cm["username"], "#8b949e")
                    st.markdown(
                        f"<div style='background:#21262d;border-radius:8px;padding:0.6rem 1rem;margin:0.25rem 0;'>"
                        f"<span style='color:{cc};font-weight:600;font-size:0.85rem;'>{cm['username']}</span>"
                        f"<span style='color:#484f58;font-size:0.72rem;margin-left:0.5rem;'>{cm['timestamp'][:16]}</span>"
                        f"<div style='margin:0.25rem 0 0;color:#cdd9e5;font-size:0.88rem;'>{cm['content']}</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

            ctxt = st.text_input("댓글 달기", key=f"ci_{log['id']}", placeholder="의견을 남겨보세요...")
            bc1, bc2 = st.columns([1, 4])
            with bc1:
                if st.button("💬 등록", key=f"cb_{log['id']}", use_container_width=True):
                    if ctxt.strip():
                        conn = get_db()
                        conn.execute(
                            "INSERT INTO shared_comments (log_id,username,content,timestamp) VALUES (?,?,?,?)",
                            (log["id"], user, ctxt.strip(), ts())
                        )
                        conn.commit()
                        conn.close()
                        log_activity(user, "댓글 작성", log["title"][:20])
                        st.rerun()

            if is_admin or log["username"] == user:
                if st.button("🗑️ 삭제", key=f"del_log_{log['id']}"):
                    conn = get_db()
                    conn.execute("DELETE FROM shared_logs WHERE id=?", (log["id"],))
                    conn.execute("DELETE FROM shared_comments WHERE log_id=?", (log["id"],))
                    conn.commit()
                    conn.close()
                    log_activity(user, "공유 로그 삭제", log["title"][:20])
                    st.rerun()


# ====================== 페이지: 코드 라이브러리 ======================
def page_code_library(user, is_admin):
    st.markdown("<h1>💾 코드 라이브러리</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#8b949e;font-size:0.88rem;margin-bottom:1rem;'>"
        "팀의 유용한 코드 스니펫을 저장하고 공유하세요</p>",
        unsafe_allow_html=True
    )

    tab_save, tab_browse = st.tabs(["⭐ 코드 저장", "📚 코드 목록"])

    with tab_save:
        title        = st.text_input("코드 제목", placeholder="예: Gemini API 스트리밍 호출")
        desc         = st.text_area("설명 (선택)", placeholder="이 코드가 무엇을 하는지 간단히 설명해주세요", height=70)
        default_code = st.session_state.pop("pending_code", "")
        code         = st.text_area("코드", value=default_code, placeholder="코드를 여기에 붙여넣으세요...", height=320)
        c1, c2 = st.columns(2)
        with c1:
            lang = st.selectbox("언어", ["Python", "JavaScript", "SQL", "Bash", "기타"])
        with c2:
            tags = st.text_input("태그 (쉼표 구분)", placeholder="예: API, Gemini, 유틸")
        if st.button("⭐ 라이브러리에 저장", type="primary"):
            if title.strip() and code.strip():
                conn = get_db()
                conn.execute(
                    "INSERT INTO code_library (username,title,description,code,language,tags,timestamp) VALUES (?,?,?,?,?,?,?)",
                    (user, title.strip(), desc.strip(), code.strip(), lang, tags.strip(), ts())
                )
                conn.commit()
                conn.close()
                log_activity(user, "코드 저장", title[:30])
                st.success("✅ 코드가 라이브러리에 저장되었습니다!")
                st.rerun()
            else:
                st.error("제목과 코드는 필수입니다.")

    with tab_browse:
        sc1, sc2 = st.columns([3, 1])
        with sc1:
            search = st.text_input("🔍 코드 검색", placeholder="제목·설명·태그 검색...")
        with sc2:
            lf = st.selectbox("언어 필터", ["전체", "Python", "JavaScript", "SQL", "Bash", "기타"])

        conn  = get_db()
        codes = conn.execute("SELECT * FROM code_library ORDER BY id DESC").fetchall()
        conn.close()

        if search:
            codes = [c for c in codes if search.lower() in (c["title"]+c["description"]+c["tags"]).lower()]
        if lf != "전체":
            codes = [c for c in codes if c["language"] == lf]

        if not codes:
            st.markdown(
                "<p style='color:#484f58;text-align:center;margin-top:3rem;'>💾 저장된 코드가 없습니다</p>",
                unsafe_allow_html=True
            )

        for cd in codes:
            mc = MEMBER_COLORS.get(cd["username"], "#8b949e")
            with st.expander(f"⭐ {cd['title']}  [{cd['language']}]  ·  {cd['username']}"):
                if cd["description"]:
                    st.markdown(f"<p style='color:#8b949e;font-size:0.85rem;'>{cd['description']}</p>",
                                unsafe_allow_html=True)
                if cd["tags"]:
                    tags_html = " ".join(
                        [f"<span class='tag'>{t.strip()}</span>" for t in cd["tags"].split(",") if t.strip()]
                    )
                    st.markdown(tags_html + "<br>", unsafe_allow_html=True)
                lang_lower = cd["language"].lower() if cd["language"] != "기타" else "text"
                st.code(cd["code"], language=lang_lower)

                ac1, ac2 = st.columns([1, 1])
                with ac1:
                    if st.button("📤 팀 공유", key=f"sc_{cd['id']}", use_container_width=True):
                        conn = get_db()
                        conn.execute(
                            "INSERT INTO shared_logs (username,title,content,ai_role,tags,timestamp) VALUES (?,?,?,?,?,?)",
                            (user, f"[코드] {cd['title']}",
                             f"```{lang_lower}\n{cd['code']}\n```", "코드 라이브러리",
                             cd["tags"], ts())
                        )
                        conn.commit()
                        conn.close()
                        log_activity(user, "코드 공유", cd["title"][:20])
                        st.success("공유됨!")
                with ac2:
                    if is_admin or cd["username"] == user:
                        if st.button("🗑️ 삭제", key=f"dc_{cd['id']}", use_container_width=True):
                            conn = get_db()
                            conn.execute("DELETE FROM code_library WHERE id=?", (cd["id"],))
                            conn.commit()
                            conn.close()
                            log_activity(user, "코드 삭제", cd["title"][:20])
                            st.rerun()


# ====================== ③ 페이지: 실시간 팀 채팅 ======================
def page_team_chat(user):
    st.markdown("<h1>🗣️ 실시간 팀 채팅</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#8b949e;font-size:0.85rem;'>3초마다 전체 새로고침 없이 메시지만 자동 업데이트됩니다.</p>",
        unsafe_allow_html=True
    )

    @st.fragment(run_every=3.0)
    def stream_chat():
        conn = get_db()
        logs = conn.execute(
            "SELECT username, message, timestamp FROM team_chat ORDER BY id DESC LIMIT 50"
        ).fetchall()
        conn.close()

        box = ("<div style='height:400px;overflow-y:auto;border:1px solid #30363d;"
               "border-radius:10px;background:#161b27;padding:12px;margin-bottom:10px;'>")
        if logs:
            for l in reversed(logs):
                c = MEMBER_COLORS.get(l["username"], "#8b949e")
                box += (
                    f"<div style='margin-bottom:8px;border-bottom:1px solid #21262d;padding-bottom:6px;'>"
                    f"<span style='color:{c};font-weight:700;font-size:0.88rem;'>{l['username']}</span>"
                    f"<span style='color:#484f58;font-size:0.72rem;margin-left:6px;'>"
                    f"[{l['timestamp'][11:16]}]</span>"
                    f"<div style='color:#e6edf3;font-size:0.92rem;margin-top:3px;white-space:pre-wrap;'>"
                    f"{l['message']}</div></div>"
                )
        else:
            box += "<p style='color:#484f58;text-align:center;padding-top:160px;font-size:0.9rem;'>첫 메시지를 보내보세요! 💬</p>"
        box += "</div>"
        st.markdown(box, unsafe_allow_html=True)

    stream_chat()

    with st.form("chat_send_form", clear_on_submit=True):
        raw_msg = st.text_input(
            "메시지", placeholder="팀원에게 보낼 메시지를 입력하세요...",
            label_visibility="collapsed", key="chat_input_field"
        )
        sc1, sc2 = st.columns([5, 1])
        with sc2:
            send_btn = st.form_submit_button("전송 🚀", use_container_width=True)
        if send_btn and raw_msg.strip():
            conn = get_db()
            conn.execute(
                "INSERT INTO team_chat (username, message, timestamp) VALUES (?,?,?)",
                (user, raw_msg.strip(), ts())
            )
            conn.commit()
            conn.close()
            log_activity(user, "팀 채팅 전송", raw_msg.strip()[:20])
            st.rerun()


# ====================== ④ 페이지: 아이디어 투표 게시판 ======================
def page_idea_board(user):
    st.markdown("<h1>💡 아이디어 투표 게시판</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#8b949e;font-size:0.85rem;'>팀 아이디어를 올리고 찬반 투표로 우선순위를 결정하세요. 1인 1표 제한.</p>",
        unsafe_allow_html=True
    )

    with st.expander("✨ 새 아이디어 등록하기", expanded=False):
        with st.form("idea_add_form", clear_on_submit=True):
            i_title = st.text_input("아이디어 제목", placeholder="예: 시계열 이상치 탐지 모델 최적화")
            i_desc  = st.text_area("상세 설명", placeholder="아이디어의 핵심 개요, 구현 방법, 기대 효과를 적어주세요.", height=120)
            if st.form_submit_button("💡 게시판에 등록", type="primary"):
                if i_title.strip():
                    conn = get_db()
                    conn.execute(
                        "INSERT INTO idea_board (username, title, description, votes, timestamp) VALUES (?,?,?,0,?)",
                        (user, i_title.strip(), i_desc.strip(), ts())
                    )
                    conn.commit()
                    conn.close()
                    log_activity(user, "아이디어 등록", i_title.strip()[:30])
                    st.success("✅ 아이디어가 게시판에 등록되었습니다!")
                    st.rerun()
                else:
                    st.error("제목을 입력해주세요.")

    st.markdown("<hr>", unsafe_allow_html=True)

    conn   = get_db()
    ideas  = conn.execute("SELECT * FROM idea_board ORDER BY votes DESC, id DESC").fetchall()
    v_hist = conn.execute(
        "SELECT idea_id, vote_type FROM idea_votes WHERE username=?", (user,)
    ).fetchall()
    conn.close()
    v_map = {v["idea_id"]: v["vote_type"] for v in v_hist}

    if not ideas:
        st.markdown(
            "<p style='color:#484f58;text-align:center;padding:3rem;font-size:0.95rem;'>"
            "📭 등록된 아이디어가 없습니다. 첫 번째 아이디어를 올려보세요!</p>",
            unsafe_allow_html=True
        )
        return

    for item in ideas:
        i_id      = item["id"]
        uc        = MEMBER_COLORS.get(item["username"], "#8b949e")
        my_vote   = v_map.get(i_id, None)
        score_clr = "#3fb950" if item["votes"] > 0 else ("#f85149" if item["votes"] < 0 else "#8b949e")

        st.markdown(
            f"""<div class='card card-purple'>
                <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
                    <h3 style='margin:0;font-size:1.05rem;color:#f0f6fc;'>{item['title']}</h3>
                    <span style='background:var(--bg-base);color:{score_clr};font-weight:700;
                                 font-size:1rem;padding:4px 12px;border-radius:8px;
                                 border:1px solid var(--border-mid);white-space:nowrap;'>
                        🔥 {item['votes']:+d} pts</span>
                </div>
                <p style='color:#8b949e;font-size:0.78rem;margin:0.3rem 0 0.7rem;'>
                    제안자: <span style='color:{uc};font-weight:600;'>{item['username']}</span>
                    | {item['timestamp'][:16]}
                    {'<span class="tag tag-green">내 투표: 찬성</span>' if my_vote=="up" else
                     '<span class="tag tag-red">내 투표: 반대</span>' if my_vote=="down" else ""}
                </p>
                <div style='background:var(--bg-base);padding:0.9rem;border-radius:8px;
                            border:1px solid var(--border);font-size:0.9rem;color:#cdd9e5;
                            white-space:pre-wrap;'>{item['description']}</div>
            </div>""",
            unsafe_allow_html=True
        )

        bc1, bc2, _ = st.columns([1.2, 1.2, 5])
        with bc1:
            up_label = "🔺 찬성 취소" if my_vote == "up" else "🔺 찬성"
            if st.button(up_label, key=f"up_{i_id}", use_container_width=True):
                conn = get_db()
                try:
                    if my_vote == "up":
                        conn.execute("DELETE FROM idea_votes WHERE idea_id=? AND username=?", (i_id, user))
                        conn.execute("UPDATE idea_board SET votes = votes - 1 WHERE id=?", (i_id,))
                    elif my_vote == "down":
                        conn.execute("UPDATE idea_votes SET vote_type='up' WHERE idea_id=? AND username=?", (i_id, user))
                        conn.execute("UPDATE idea_board SET votes = votes + 2 WHERE id=?", (i_id,))
                    else:
                        conn.execute("INSERT INTO idea_votes (idea_id, username, vote_type) VALUES (?,?,'up')", (i_id, user))
                        conn.execute("UPDATE idea_board SET votes = votes + 1 WHERE id=?", (i_id,))
                    conn.commit()
                except Exception as e:
                    st.error(f"투표 오류: {e}")
                conn.close()
                log_activity(user, "아이디어 찬성", item["title"][:20])
                st.rerun()
        with bc2:
            dn_label = "🔻 반대 취소" if my_vote == "down" else "🔻 반대"
            if st.button(dn_label, key=f"dn_{i_id}", use_container_width=True):
                conn = get_db()
                try:
                    if my_vote == "down":
                        conn.execute("DELETE FROM idea_votes WHERE idea_id=? AND username=?", (i_id, user))
                        conn.execute("UPDATE idea_board SET votes = votes + 1 WHERE id=?", (i_id,))
                    elif my_vote == "up":
                        conn.execute("UPDATE idea_votes SET vote_type='down' WHERE idea_id=? AND username=?", (i_id, user))
                        conn.execute("UPDATE idea_board SET votes = votes - 2 WHERE id=?", (i_id,))
                    else:
                        conn.execute("INSERT INTO idea_votes (idea_id, username, vote_type) VALUES (?,?,'down')", (i_id, user))
                        conn.execute("UPDATE idea_board SET votes = votes - 1 WHERE id=?", (i_id,))
                    conn.commit()
                except Exception as e:
                    st.error(f"투표 오류: {e}")
                conn.close()
                log_activity(user, "아이디어 반대", item["title"][:20])
                st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)


# ====================== 페이지: 관리자 ======================
def page_admin(user):
    st.markdown("<h1>👑 관리자 패널</h1>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📊 팀 통계", "💾 데이터 백업 & 내보내기", "⚠️ 데이터 관리"])

    with tab1:
        st.markdown("### 팀원별 활동 현황")
        conn = get_db()
        act_rows = conn.execute(
            "SELECT username, COUNT(*) as cnt FROM activity_log GROUP BY username"
        ).fetchall()
        if act_rows:
            chart_df = pd.DataFrame([{"팀원": r["username"], "활동 수": r["cnt"]} for r in act_rows]).set_index("팀원")
            st.bar_chart(chart_df, color="#00ffcc", height=200)
            st.markdown("<br>", unsafe_allow_html=True)

        for name in TEAM_USERS.keys():
            chats   = conn.execute("SELECT COUNT(*) FROM chat_history WHERE username=?", (name,)).fetchone()[0]
            shared  = conn.execute("SELECT COUNT(*) FROM shared_logs WHERE username=?", (name,)).fetchone()[0]
            todos_c = conn.execute("SELECT COUNT(*) FROM todos WHERE created_by=?", (name,)).fetchone()[0]
            acts    = conn.execute("SELECT COUNT(*) FROM activity_log WHERE username=?", (name,)).fetchone()[0]
            codes   = conn.execute("SELECT COUNT(*) FROM code_library WHERE username=?", (name,)).fetchone()[0]
            mc      = MEMBER_COLORS.get(name, "#8b949e")
            icon    = "👑" if name == ADMIN_USER else "🧑‍💻"
            st.markdown(
                f"<div class='card card-accent' style='margin:0.5rem 0;'>"
                f"<div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;'>"
                f"<span style='font-size:1.3rem;'>{icon}</span>"
                f"<span style='color:{mc};font-weight:700;font-size:1rem;'>{name}</span>"
                f"</div>"
                f"<div style='display:flex;gap:1.5rem;flex-wrap:wrap;'>"
                f"<span>💬 대화 <b style='color:#00ffcc;'>{chats}</b></span>"
                f"<span>📤 공유 <b style='color:#00ffcc;'>{shared}</b></span>"
                f"<span>✅ 할 일 <b style='color:#00ffcc;'>{todos_c}</b></span>"
                f"<span>💾 코드 <b style='color:#00ffcc;'>{codes}</b></span>"
                f"<span>⚡ 활동 <b style='color:#00ffcc;'>{acts}</b></span>"
                f"</div></div>",
                unsafe_allow_html=True
            )
        conn.close()

        st.markdown("### 최근 활동 로그 (50개)")
        conn = get_db()
        logs = conn.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT 50").fetchall()
        conn.close()
        if logs:
            df = pd.DataFrame([dict(r) for r in logs])
            st.dataframe(df[["username", "action", "detail", "timestamp"]], use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### 💾 데이터 백업 (CSV 다운로드)")
        tables = {
            "chat_history": "💬 대화 기록",
            "shared_logs":  "📤 공유 로그",
            "todos":        "✅ 할 일 목록",
            "memos":        "📝 메모",
            "code_library": "💾 코드 라이브러리",
            "activity_log": "⚡ 활동 로그",
            "team_chat":    "🗣️ 팀 채팅",
            "idea_board":   "💡 아이디어 보드",
        }
        for table, label in tables.items():
            conn = get_db()
            try:
                df  = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                csv = df.to_csv(index=False).encode("utf-8-sig")
                fname = f"{table}_{datetime.now().strftime('%Y%m%d')}.csv"
                st.download_button(
                    f"📥 {label} 다운로드 ({len(df)}건)",
                    csv, fname, "text/csv",
                    use_container_width=True,
                    key=f"dl_{table}"
                )
            except Exception as e:
                st.error(f"{label} 오류: {e}")
            finally:
                conn.close()

        # ⑨ 대회 제출용 마크다운 Export Hub
        st.markdown("---")
        st.markdown("### 📝 대회 제출용 Markdown 보고서 Export")
        st.markdown(
            "<p style='color:#8b949e;font-size:0.85rem;'>"
            "공유 로그 + 코드 라이브러리를 통합 마크다운 문서로 내보냅니다.</p>",
            unsafe_allow_html=True
        )
        if st.button("🚀 통합 Markdown 보고서 생성", type="primary", use_container_width=True):
            conn = get_db()
            logs_md  = conn.execute("SELECT * FROM shared_logs ORDER BY id ASC").fetchall()
            codes_md = conn.execute("SELECT * FROM code_library ORDER BY id ASC").fetchall()
            conn.close()

            md = f"# ⚓ AI 팀 관제실 — 경진대회 기술 산출물 보고서\n\n"
            md += f"- **추출 일시:** {ts()}\n"
            md += f"- **대상 프로젝트:** POSCO DX 7회 AI 청소년 챌린지\n\n"
            md += "---\n\n## 1. 팀 연구 공유 로그\n\n"
            if logs_md:
                for l in logs_md:
                    md += f"### 📌 {l['title']}\n"
                    md += f"- 작성자: {l['username']} | 역할: {l['ai_role']} | 일시: {l['timestamp']}\n\n"
                    md += f"{l['content']}\n\n---\n\n"
            else:
                md += "*공유 로그가 없습니다.*\n\n"

            md += "## 2. 코드 라이브러리\n\n"
            if codes_md:
                for c in codes_md:
                    md += f"### 💾 {c['title']} (`{c['language']}`)\n"
                    md += f"- 작성자: {c['username']} | 태그: {c['tags']} | 일시: {c['timestamp']}\n"
                    md += f"- 설명: {c['description']}\n\n"
                    lang_l = c['language'].lower() if c['language'] != '기타' else 'text'
                    md += f"```{lang_l}\n{c['code']}\n```\n\n---\n\n"
            else:
                md += "*저장된 코드가 없습니다.*\n\n"

            fname_md = f"POSCO_DX_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
            st.download_button(
                "📥 통합 Markdown 파일 다운로드",
                md.encode("utf-8"),
                fname_md,
                "text/markdown",
                use_container_width=True,
                key="export_md"
            )
            log_activity(user, "보고서 Export", "Markdown 다운로드")
            st.balloons()

    with tab3:
        st.warning("⚠️ 이 작업은 되돌릴 수 없습니다. 신중히 사용해주세요.")
        target = st.selectbox("초기화 대상 선택", ["대화 기록", "활동 로그", "공유 로그", "댓글", "팀 채팅", "아이디어 보드"])
        table_map = {
            "대화 기록": "chat_history",
            "활동 로그": "activity_log",
            "공유 로그": "shared_logs",
            "댓글":      "shared_comments",
            "팀 채팅":   "team_chat",
            "아이디어 보드": "idea_board",
        }
        confirm = st.text_input("확인 문구 입력 ('삭제확인' 을 입력하세요)")
        if st.button("🗑️ 초기화 실행", type="primary"):
            if confirm == "삭제확인":
                conn = get_db()
                conn.execute(f"DELETE FROM {table_map[target]}")
                conn.commit()
                conn.close()
                log_activity(user, f"{target} 초기화", "관리자 작업")
                st.success(f"✅ {target} 초기화 완료")
                st.rerun()
            else:
                st.error("확인 문구가 올바르지 않습니다.")


# ====================== 앱 진입점 ======================
inject_css()
init_db()
init_deepseek()

for k, v in [
    ("logged_in_user", None),
    ("current_view",   "home"),
    ("ai_role",        "🗣️ 자유 대화"),
    ("messages",       []),
    ("show_history",   False),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── 로그인 화면 ──
if st.session_state.logged_in_user is None:
    st.markdown("""
    <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:75vh;'>
        <div style='text-align:center;margin-bottom:2rem;'>
            <div style='font-size:3.5rem;'>⚓</div>
            <h1 style='color:#00ffcc;font-size:2rem;margin:0.3rem 0;'>AI 팀 관제실</h1>
            <p style='color:#8b949e;margin:0;'>POSCO DX 7회 AI 청소년 챌린지</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.1, 1])
    with col2:
        st.markdown(
            "<div style='background:linear-gradient(135deg,#161b27,#1c2333);"
            "border:1px solid #30363d;border-radius:16px;padding:2rem;"
            "box-shadow:0 20px 60px rgba(0,255,204,0.06);'>",
            unsafe_allow_html=True
        )
        st.markdown("<h2 style='text-align:center;color:#00ffcc;margin:0 0 0.3rem;'>팀원 로그인</h2>",
                    unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#484f58;font-size:0.8rem;margin-bottom:1.5rem;'>"
                    "비밀번호는 관리자만 다릅니다</p>", unsafe_allow_html=True)

        username = st.selectbox("👤 팀원 선택", list(TEAM_USERS.keys()))
        password = st.text_input("🔑 비밀번호", type="password", placeholder="비밀번호 입력")

        if st.button("🚀 로그인하기", type="primary", use_container_width=True):
            if TEAM_USERS.get(username) == password:
                st.session_state.logged_in_user = username
                st.session_state.messages = []
                log_activity(username, "로그인")
                st.rerun()
            else:
                st.error("❌ 비밀번호가 올바르지 않습니다.")

        st.markdown("</div>", unsafe_allow_html=True)

# ── 메인 앱 ──
else:
    user     = st.session_state.logged_in_user
    is_admin = user == ADMIN_USER

    with st.sidebar:
        # ① 실시간 시계
        render_realtime_clock()

        # 프로필
        mc = MEMBER_COLORS.get(user, "#8b949e")
        role_icon  = "👑" if is_admin else "🧑‍💻"
        role_label = "관리자" if is_admin else "팀원"
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#21262d,#1c2333);border-radius:12px;"
            f"padding:1rem;margin-bottom:1rem;text-align:center;border:1px solid #30363d;'>"
            f"<div style='font-size:2rem;'>{role_icon}</div>"
            f"<div style='color:{mc};font-weight:700;font-size:1rem;margin-top:0.3rem;'>{user}</div>"
            f"<div style='color:#484f58;font-size:0.72rem;'>{role_label}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

        # AI 모드
        st.markdown(
            "<p style='color:#8b949e;font-size:0.78rem;margin:0.5rem 0 0.3rem;letter-spacing:0.05em;'>🤖 AI 모드 선택</p>",
            unsafe_allow_html=True
        )
        st.session_state.ai_role = st.radio("", list(ROLE_PROMPTS.keys()), label_visibility="collapsed")

        st.markdown("<hr>", unsafe_allow_html=True)

        # 네비게이션
        nav = [
            ("🏠", "home",         "홈 대시보드"),
            ("💬", "chat",         "AI 대화"),
            ("🗣️", "team_chat",    "실시간 팀 채팅"),
            ("💡", "idea_board",   "아이디어 투표"),
            ("✅", "todo",         "팀 할 일"),
            ("📝", "memo",         "팀 메모장"),
            ("📋", "shared",       "공유 로그"),
            ("💾", "code_library", "코드 라이브러리"),
        ]
        if is_admin:
            nav.append(("👑", "admin", "관리자 패널"))

        for icon, view_key, label in nav:
            if st.button(f"{icon}  {label}", key=f"nav_{view_key}", use_container_width=True):
                st.session_state.current_view = view_key
                st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # ② 미니게임 위젯
        render_mini_game()

        st.markdown("<hr>", unsafe_allow_html=True)
        if st.button("🚪  로그아웃", use_container_width=True):
            log_activity(user, "로그아웃")
            for k in ["logged_in_user", "messages", "home_idea", "show_history",
                      "pending_code", "g_target", "g_tries", "g_max", "g_log", "g_status"]:
                st.session_state.pop(k, None)
            st.session_state.current_view = "home"
            st.rerun()

        st.markdown(
            "<p style='color:#21262d;font-size:0.65rem;text-align:center;margin-top:0.5rem;'>"
            "⚓ AI 팀 관제실 v5.0</p>",
            unsafe_allow_html=True
        )

    # ── 페이지 라우팅 ──
    v = st.session_state.current_view
    if   v == "home":              page_home(user, is_admin)
    elif v == "chat":              page_chat(user)
    elif v == "team_chat":         page_team_chat(user)
    elif v == "idea_board":        page_idea_board(user)
    elif v == "todo":              page_todo(user, is_admin)
    elif v == "memo":              page_memo(user, is_admin)
    elif v == "shared":            page_shared(user, is_admin)
    elif v == "code_library":      page_code_library(user, is_admin)
    elif v == "admin" and is_admin: page_admin(user)
