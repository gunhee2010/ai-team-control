    # =====================================================================
# ⚓ AI 팀 관제실 — 프로덕션급 통합 마스터 v3.0 (DeepSeek V3 엔진 적용)
# 주요 추가: ①모바일 반응형 CSS ②DeepSeek 429 백오프 재시도
#            ③SQLite timeout 동시성 락 방지 ④컨텍스트 정제
#            ⑤실시간 활동 bar_chart ⑥메모 핀(고정) 기능
#            ⑦Gemini -> DeepSeek V3 공식 API 완전 교체 (openai 패키지)
# =====================================================================

import streamlit as st
import sqlite3
from openai import OpenAI  # 구글 genai 대신 openai 패키지 사용
import os
import time
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
    "🗣️ 자유 대화":       "너는 친근하고 똑똑한 AI 어시스턴트야. 어떤 질문이든 친절하고 명확하게 답변해줘. 한국어로 답변해.",
    "💻 코딩 도우미":      "너는 파이썬 전문 시니어 개발자야. 실용적이고 최적화된 코드를 작성해줘. 코드에는 항상 주석을 달고, 사용 예시도 포함해줘. 한국어로 설명해.",
    "🔧 에러 수정 전문가": "너는 디버깅 전문가야. 에러 원인을 명확히 분석하고, 수정된 코드와 재발방지 방법을 순서대로 알려줘. 한국어로 답변해.",
    "📄 문서 작성 도우미": "너는 기술 문서 전문가야. AI 경진대회 보고서에 바로 사용할 수 있게 전문적이고 구조적으로 작성해. 한국어로 작성해.",
    "💡 아이디어 브레인스토밍": "너는 창의적인 아이디어 전문가야. AI 경진대회에서 차별화될 수 있는 혁신적이고 실현 가능한 아이디어를 제안해. 각 아이디어의 장점과 구현 방법도 포함해. 한국어로 답변해."
}

MEMBER_COLORS = {
    "최건희": "#ff7b72",
    "이서우": "#79c0ff",
    "현수민": "#a5d6ff"
}

# DeepSeek 백오프 설정
DEEPSEEK_MAX_RETRIES = 3   # 최대 재시도 횟수
DEEPSEEK_BASE_DELAY  = 5   # 첫 대기(초) — 이후 2배씩 증가


# ====================== CSS (모바일 반응형 + 편의성 개선) ======================
def inject_css():
    st.markdown("""
<style>
/* ── Base & Scrollbar ── */
.stApp {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
.main .block-container { padding: 2rem 2.5rem 4rem; max-width: 1250px; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #8b949e; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #121620 0%, #0d1117 100%);
    border-right: 1px solid #21262d;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    background: transparent;
    color: #8b949e;
    border: 1px solid transparent;
    border-radius: 8px;
    text-align: left;
    padding: 0.6rem 1.2rem;
    margin: 2px 0;
    font-size: 0.92rem;
    transition: all 0.2s ease;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #1f2430;
    color: #00ffcc;
    border-color: rgba(0, 255, 204, 0.15);
    transform: translateX(4px);
}

/* ── Cards ── */
.card {
    background: #161b27;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin: 0.5rem 0;
    transition: all 0.2s ease;
}
.card:hover { border-color: rgba(0, 255, 204, 0.25); box-shadow: 0 4px 25px rgba(0,255,204,0.05); }
.card-accent  { border-left: 4px solid #00ffcc; }
.card-blue    { border-left: 4px solid #58a6ff; }
.card-purple  { border-left: 4px solid #bc8cff; }
.card-pinned  { border-left: 4px solid #f0d000; box-shadow: 0 0 10px rgba(240,208,0,0.08); }

/* ── Metric Cards ── */
.metric-card {
    background: linear-gradient(135deg, #161b27 0%, #192233 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.4rem 1rem;
    text-align: center;
    transition: all 0.25s ease;
    box-shadow: 0 4px 10px rgba(0,0,0,0.2);
}
.metric-card:hover { border-color: rgba(0, 255, 204, 0.3); transform: translateY(-3px); }
.metric-icon  { font-size: 1.5rem; margin-bottom: 0.2rem; }
.metric-value { font-size: 2.1rem; font-weight: 700; color: #00ffcc; line-height: 1.1; margin: 0.3rem 0; text-shadow: 0 0 10px rgba(0,255,204,0.1); }
.metric-label { font-size: 0.8rem; color: #8b949e; letter-spacing: 0.04em; }

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00ffcc 0%, #00c9a7 100%);
    color: #0d1117;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    transition: all 0.25s ease;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #00e6b8 0%, #00b594 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(0,255,204,0.3);
}
.stButton > button {
    border-radius: 8px !important;
    border: 1px solid #30363d !important;
    background-color: #161b27 !important;
    color: #cdd9e5 !important;
    transition: all 0.2s;
    /* 모바일 터치 최소 크기 보장 */
    min-height: 40px;
}
.stButton > button:hover { border-color: #8b949e !important; color: #ffffff !important; }

/* ── Typography ── */
h1 { color: #00ffcc !important; font-size: 1.8rem !important; font-weight: 700 !important; margin-bottom: 0.5rem !important; }
h2 { color: #e6edf3 !important; font-weight: 600 !important; }
h3 { color: #cdd9e5 !important; font-weight: 600 !important; }
p  { color: #cdd9e5; line-height: 1.6; }

/* ── Tags ── */
.tag {
    display: inline-block;
    background: #21262d;
    color: #58a6ff;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    margin: 2px;
    font-weight: 500;
}
.tag-green  { color: #3fb950; background: rgba(63,185,80,0.1); border-color: rgba(63,185,80,0.2); }
.tag-orange { color: #e3b341; background: rgba(227,179,65,0.1); border-color: rgba(227,179,65,0.2); }
.tag-red    { color: #f85149; background: rgba(248,81,73,0.1); border-color: rgba(248,81,73,0.2); }
.tag-gold   { color: #f0d000; background: rgba(240,208,0,0.1); border-color: rgba(240,208,0,0.25); }

/* ── Activity Feed ── */
.activity-item {
    display: flex;
    align-items: flex-start;
    gap: 0.8rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid #21262d;
}
.activity-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #00ffcc;
    margin-top: 6px;
    flex-shrink: 0;
    box-shadow: 0 0 8px rgba(0,255,204,0.5);
}

/* ── Kanban ── */
.kanban-header {
    font-weight: 700;
    margin-bottom: 1rem;
    padding: 0.6rem 0.8rem;
    border-radius: 8px;
    text-align: center;
    font-size: 0.92rem;
    letter-spacing: 0.05em;
    box-shadow: 0 2px 5px rgba(0,0,0,0.15);
}
.kh-todo  { background: #21262d; color: #9ca3af; border: 1px solid #30363d; }
.kh-doing { background: rgba(30,58,95,0.6); color: #93c5fd; border: 1px solid #1e3a5f; }
.kh-done  { background: rgba(6,78,59,0.6); color: #6ee7b7; border: 1px solid #064e3b; }
.task-card {
    background: #161b27;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin: 0.5rem 0;
    transition: all 0.2s;
}
.task-card:hover { border-color: #58a6ff66; transform: scale(1.01); }

/* ── Inputs & Selectbox ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background-color: #161b27 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 8px !important;
    /* 모바일: 최소 16px → 자동 줌 방지 */
    font-size: 16px !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #00ffccaa !important;
    box-shadow: 0 0 0 2px rgba(0,255,204,0.15) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 1px solid #21262d; gap: 0.5rem; }
.stTabs [data-baseweb="tab"] { background: transparent; color: #8b949e; border-radius: 8px 8px 0 0; padding: 0.6rem 1.4rem; font-size: 0.9rem; transition: all 0.2s; }
.stTabs [data-baseweb="tab"]:hover { color: #ffffff; background: #161b27; }
.stTabs [aria-selected="true"] { background: #161b27 !important; color: #00ffcc !important; border-bottom: 2px solid #00ffcc !important; font-weight: 600; }

/* ── Expander ── */
[data-testid="stExpander"] { background: #161b27; border: 1px solid #30363d; border-radius: 10px; margin: 0.5rem 0; }

/* ── Chat Messages ── */
[data-testid="stChatMessage"] {
    background-color: #161b27 !important;
    border: 1px solid #21262d !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    margin: 0.6rem 0 !important;
}
[data-testid="stChatMessageUser"] { background-color: #1c2333 !important; border-color: #30363d !important; }
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] ol,
[data-testid="stChatMessage"] ul,
.stMarkdown p, .stMarkdown li, .stMarkdown strong {
    color: #e6edf3 !important;
    font-size: 0.95rem;
    line-height: 1.6;
}

/* ── Code Blocks ── */
code { background: #21262d !important; color: #ff7b72 !important; padding: 2px 6px !important; border-radius: 4px !important; font-size: 0.88rem !important; }
pre code { color: #e6edf3 !important; background: transparent !important; padding: 0 !important; font-size: 0.9rem !important; }
pre { background: #0d1117 !important; border: 1px solid #30363d !important; border-radius: 8px !important; padding: 1rem !important; }

/* ── Misc ── */
hr { border-color: #21262d !important; margin: 1.2rem 0 !important; }
[data-testid="stAlert"] { border-radius: 8px !important; background-color: #1c1a22 !important; border-color: #443e50 !important; }
.stSpinner > div { border-color: #00ffcc !important; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }

/* ============================================================
   📱 모바일 반응형 미디어 쿼리 (≤ 768px)
   ============================================================ */
@media (max-width: 768px) {
    /* 블록 여백 축소 */
    .main .block-container { padding: 1rem 0.75rem 3rem !important; }

    /* 사이드바: 좁은 화면에서 아이콘 크기 조정 */
    [data-testid="stSidebar"] .stButton > button {
        font-size: 0.85rem;
        padding: 0.55rem 0.8rem;
    }

    /* h1 폰트 크기 축소 */
    h1 { font-size: 1.35rem !important; }

    /* 메트릭 카드: 1열 스택 레이아웃으로 전환 */
    .metric-card { padding: 1rem 0.6rem; }
    .metric-value { font-size: 1.7rem; }

    /* 버튼 최소 높이 & 터치 영역 확보 */
    .stButton > button { min-height: 48px !important; font-size: 0.88rem !important; }
    .stButton > button[kind="primary"] { padding: 0.65rem 1.2rem; }

    /* 칸반: 열 간격 축소 */
    .task-card { padding: 0.7rem 0.8rem; margin: 0.35rem 0; }
    .kanban-header { font-size: 0.82rem; padding: 0.5rem 0.6rem; }

    /* 카드 패딩 축소 */
    .card { padding: 0.9rem 1rem; }

    /* 탭 텍스트 크기 */
    .stTabs [data-baseweb="tab"] { padding: 0.5rem 0.8rem; font-size: 0.82rem; }

    /* 채팅 입력창 */
    [data-testid="stChatMessage"] { padding: 0.7rem !important; }

    /* 활동 피드 간격 */
    .activity-item { gap: 0.5rem; padding: 0.55rem 0; }
    .activity-dot  { width: 7px; height: 7px; margin-top: 5px; }

    /* 태그 */
    .tag { padding: 2px 8px; font-size: 0.7rem; }
}

/* 초소형 화면 (≤ 380px) */
@media (max-width: 380px) {
    .main .block-container { padding: 0.7rem 0.5rem 2.5rem !important; }
    h1 { font-size: 1.15rem !important; }
    .metric-value { font-size: 1.45rem; }
    .stButton > button { min-height: 44px !important; }
}
</style>
""", unsafe_allow_html=True)


# ====================== DB — timeout으로 동시성 락 방지 ======================
def get_db():
    """
    timeout=30.0 : 동시 다중 접속 시 최대 30초 대기 후 OperationalError
    check_same_thread=False : Streamlit 멀티스레드 환경 대응
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # WAL 모드: 읽기/쓰기 동시 접근 허용 → 락 충돌 대폭 감소
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, ai_role TEXT, role TEXT,
            content TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS shared_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, title TEXT, content TEXT,
            ai_role TEXT, tags TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS shared_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER, username TEXT,
            content TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_by TEXT, assigned_to TEXT,
            task TEXT, status TEXT DEFAULT "todo",
            priority TEXT DEFAULT "medium",
            due_date TEXT, timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS memos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT, title TEXT, content TEXT,
            is_shared INTEGER DEFAULT 0,
            is_pinned INTEGER DEFAULT 0,
            timestamp TEXT
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
    ''')
    # memos 테이블에 is_pinned 컬럼이 없으면 마이그레이션
    try:
        conn.execute("ALTER TABLE memos ADD COLUMN is_pinned INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass  # 이미 있으면 무시
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
        # DB 락 발생 시 로그만 기록하고 앱은 계속 구동
        st.toast(f"⚠️ 활동 기록 실패 (DB 혼잡): {e}", icon="⚠️")


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ====================== DeepSeek V3 통신 (OpenAI 패키지 활용) ======================
def init_deepseek():
    if "deepseek_ready" not in st.session_state:
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if api_key:
            # DeepSeek API는 OpenAI 클라이언트와 완벽 호환됩니다.
            st.session_state.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            st.session_state.deepseek_ready = True
        else:
            st.session_state.deepseek_ready = False


def call_deepseek(prompt: str, role: str) -> str:
    """
    DeepSeek V3 공식 API 호출 with 지수 백오프 재시도.
    429(할당량 초과) 감지 시 최대 DEEPSEEK_MAX_RETRIES 회 자동 재시도.
    에러 응답은 '❌' 접두어로 시작 → 컨텍스트 정제 함수로 필터링됨.
    """
    if not st.session_state.get("deepseek_ready"):
        return "⚠️ DEEPSEEK_API_KEY 환경변수가 설정되지 않았습니다. Render.com 환경변수를 확인해주세요."

    system = ROLE_PROMPTS.get(role, ROLE_PROMPTS["🗣️ 자유 대화"])

    delay = DEEPSEEK_BASE_DELAY
    for attempt in range(1, DEEPSEEK_MAX_RETRIES + 1):
        try:
            response = st.session_state.client.chat.completions.create(
                model="deepseek-chat",  # DeepSeek V3 공식 모델명
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "quota" in err_str.lower() or "resource exhausted" in err_str.lower()

            if is_rate_limit and attempt < DEEPSEEK_MAX_RETRIES:
                # 429 감지: 재시도 대기 안내 + 대기
                st.toast(
                    f"⏳ API 한도 초과 — {delay}초 후 재시도 중... ({attempt}/{DEEPSEEK_MAX_RETRIES})",
                    icon="⏳"
                )
                time.sleep(delay)
                delay *= 2  # 지수 백오프: 5s → 10s → 20s
            else:
                # 재시도 불가 오류 또는 최대 횟수 초과
                return f"❌ AI 응답 오류 ({attempt}회 시도): {err_str}"

    return "❌ AI 응답 실패: 최대 재시도 횟수를 초과했습니다. 잠시 후 다시 시도해주세요."


def purge_error_messages(messages: list) -> list:
    """
    대화 맥락 정제: '❌' 또는 '⚠️'로 시작하는 AI 오류 응답과
    해당 오류에 이어진 사용자 메시지 쌍을 컨텍스트에서 제거.
    """
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
            skip_next_user = False  # 오류 응답 자체는 제거
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


# ====================== 페이지: 홈 ======================
def page_home(user, is_admin):
    hour = datetime.now().hour
    if   hour < 6 or hour >= 22: greet = "🌙 좋은 밤이에요"
    elif hour < 12:               greet = "🌅 좋은 아침이에요"
    else:                         greet = "☀️ 좋은 오후예요"

    color = MEMBER_COLORS.get(user, "#00ffcc")
    st.markdown("<h1>🏠 팀 대시보드</h1>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='color:#8b949e; font-size:1rem; margin-bottom:1.5rem;'>"
        f"{greet}, <b style='color:{color};'>{user}</b>님! "
        f"POSCO DX 7회 AI 청소년 챌린지 화이팅! 🚀</p>",
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
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-icon'>{icon}</div>
                <div class='metric-value'>{val}</div>
                <div class='metric-label'>{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 실시간 팀 활동 차트 (⑤ 신규) ──
    conn = get_db()
    act_rows = conn.execute(
        "SELECT username, COUNT(*) as cnt FROM activity_log GROUP BY username"
    ).fetchall()
    conn.close()
    if act_rows:
        act_df = pd.DataFrame([{"팀원": r["username"], "활동 수": r["cnt"]} for r in act_rows])
        act_df = act_df.set_index("팀원")
        st.markdown("### 📊 팀원별 누적 활동")
        st.bar_chart(act_df, color="#00ffcc", height=180)

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([2, 1])

    # ── 최근 활동 ──
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
                detail_html = (f"<br><span style='color:#6e7681;font-size:0.8rem;'>{a['detail']}</span>"
                               if a["detail"] else "")
                html += f"""
                <div class='activity-item'>
                    <div class='activity-dot'></div>
                    <div>
                        <span style='color:{c};font-weight:600;'>{a["username"]}</span>
                        <span style='color:#8b949e;'> · {a["action"]}</span>
                        {detail_html}
                        <br><span style='color:#484f58;font-size:0.72rem;'>{a["timestamp"]}</span>
                    </div>
                </div>"""
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown(
                "<p style='color:#484f58;text-align:center;margin-top:2rem;'>"
                "아직 활동이 없습니다. 팀을 시작해보세요! 🚀</p>",
                unsafe_allow_html=True
            )

        # ── 진행 중 할 일 미리보기 ──
        st.markdown("<br>### 📋 현재 진행 중인 할 일", unsafe_allow_html=True)
        conn = get_db()
        doing = conn.execute(
            "SELECT * FROM todos WHERE status='doing' ORDER BY timestamp DESC LIMIT 5"
        ).fetchall()
        conn.close()
        if doing:
            for t in doing:
                mc = MEMBER_COLORS.get(t["assigned_to"], "#8b949e")
                st.markdown(f"""
                <div class='card' style='padding:0.7rem 1rem; margin:0.3rem 0;'>
                    <span style='color:#e3b341;font-size:0.75rem;'>⚡ 진행 중</span>
                    <span style='float:right;color:{mc};font-size:0.8rem;font-weight:600;'>{t["assigned_to"]}</span><br>
                    <span style='color:#e6edf3;font-size:0.9rem;'>{t["task"]}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:#484f58;font-size:0.85rem;'>진행 중인 할 일이 없습니다.</p>",
                        unsafe_allow_html=True)

    # ── 우측 패널 ──
    with right:
        st.markdown("### 💡 AI 아이디어 추천")
        st.markdown(
            "<p style='color:#8b949e;font-size:0.85rem;margin-bottom:0.8rem;'>"
            "경진대회에 도움이 될 창의적인 아이디어를 AI가 추천해드려요</p>",
            unsafe_allow_html=True
        )
        if st.button("✨ 새 아이디어 받기", type="primary", use_container_width=True, key="home_idea_btn"):
            with st.spinner("🤖 AI가 아이디어를 생각하고 있어요..."):
                result = call_deepseek(
                    "POSCO DX AI 청소년 챌린지 경진대회 프로젝트에 도움이 될 창의적이고 혁신적인 아이디어 3가지를 추천해줘. "
                    "각 아이디어마다 ①핵심 개요 ②주요 기능 ③차별점 순서로 간결하게 설명해줘.",
                    "💡 아이디어 브레인스토밍"
                )
                st.session_state.home_idea = result
                log_activity(user, "AI 아이디어 추천", "홈 대시보드")

        if "home_idea" in st.session_state:
            st.markdown(
                f"<div class='card card-accent' style='margin-top:0.8rem;'>"
                f"<p style='font-size:0.83rem;color:#cdd9e5;white-space:pre-wrap;'>"
                f"{st.session_state.home_idea}</p></div>",
                unsafe_allow_html=True
            )

        st.markdown("<br>### 👥 팀원 현황", unsafe_allow_html=True)
        members = [("최건희", "👑"), ("이서우", "🧑‍💻"), ("현수민", "🧑‍🎨")]
        for name, icon in members:
            c    = MEMBER_COLORS.get(name, "#8b949e")
            conn = get_db()
            last = conn.execute(
                "SELECT timestamp FROM activity_log WHERE username=? ORDER BY id DESC LIMIT 1", (name,)
            ).fetchone()
            conn.close()
            last_t = last["timestamp"][11:16] if last else "—"
            st.markdown(f"""
            <div class='card' style='padding:0.65rem 1rem;margin:0.25rem 0;'>
                <span style='color:{c};font-weight:600;'>{icon} {name}</span>
                {"<span style='background:#1c3a2a;color:#3fb950;font-size:0.7rem;border-radius:4px;padding:1px 6px;float:right;'>관리자</span>" if name == ADMIN_USER else ""}
                <br><span style='color:#484f58;font-size:0.75rem;'>마지막 활동 {last_t}</span>
            </div>""", unsafe_allow_html=True)


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

    # 상단 버튼
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

    # 대화 기록 보기 패널
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

    # 대화 출력
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

    # 입력
    if prompt := st.chat_input(f"{role}에게 메시지를 보내세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        # ④ 컨텍스트 정제: 에러 메시지 제거 후 전달할 프롬프트 구성
        clean_ctx = purge_error_messages(st.session_state.messages)
        ctx_text  = "\n".join(
            [f"[{'사용자' if m['role']=='user' else 'AI'}] {m['content']}"
             for m in clean_ctx[-10:]]  # 최근 10턴만 포함
        )
        full_prompt = f"이전 대화:\n{ctx_text}\n\n현재 질문:\n{prompt}" if len(clean_ctx) > 1 else prompt

        with st.spinner("🤖 AI가 생각하고 있어요..."):
            response = call_deepseek(full_prompt, role)

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
            new_task = st.text_input("할 일 내용", placeholder="예: DeepSeek API 연동 테스트하기")
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

    st.markdown("<br>", unsafe_allow_html=True)

    conn     = get_db()
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
                st.markdown(f"""
                <div class='task-card'>
                    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>
                        {priority_badge(task["priority"])}
                        <span style='color:{mc};font-size:0.75rem;font-weight:600;'>{task["assigned_to"]}</span>
                    </div>
                    <p style='margin:0.25rem 0 0.4rem;font-size:0.88rem;color:#e6edf3;'>{task["task"]}</p>
                    {due_html}
                </div>""", unsafe_allow_html=True)

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


# ====================== 페이지: 메모 (핀 고정 기능 추가) ======================
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
                     1 if is_pinned_new else 0,
                     ts())
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
        # 고정(is_pinned DESC) → 최신(id DESC) 정렬
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
                "<p style='color:#484f58;text-align:center;margin-top:4rem;font-size:1rem;'>"
                "📭 아직 메모가 없습니다</p>",
                unsafe_allow_html=True
            )
            return

        # 검색
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

                # 핀 토글 (본인 또는 관리자)
                if is_admin or memo["username"] == user:
                    with act1:
                        pin_label = "📌 고정 해제" if pinned else "📌 고정하기"
                        if st.button(pin_label, key=f"pin_memo_{memo['id']}", use_container_width=True):
                            conn = get_db()
                            conn.execute(
                                "UPDATE memos SET is_pinned=? WHERE id=?",
                                (0 if pinned else 1, memo["id"])
                            )
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
            st.markdown(f"""
            <div class='card card-accent'>
                <div style='display:flex;gap:0.8rem;align-items:center;margin-bottom:0.8rem;flex-wrap:wrap;'>
                    {member_badge(log["username"])}
                    <span class='tag'>{log["ai_role"]}</span>
                    <span style='color:#484f58;font-size:0.78rem;'>{log["timestamp"]}</span>
                </div>
                <div style='color:#cdd9e5;white-space:pre-wrap;line-height:1.6;font-size:0.88rem;'>
                    {log["content"]}
                </div>
            </div>""", unsafe_allow_html=True)

            # 댓글
            conn     = get_db()
            comments = conn.execute(
                "SELECT * FROM shared_comments WHERE log_id=? ORDER BY id", (log["id"],)
            ).fetchall()
            conn.close()

            if comments:
                st.markdown("**💬 댓글**")
                for cm in comments:
                    cc = MEMBER_COLORS.get(cm["username"], "#8b949e")
                    st.markdown(f"""
                    <div style='background:#21262d;border-radius:8px;padding:0.6rem 1rem;margin:0.25rem 0;'>
                        <span style='color:{cc};font-weight:600;font-size:0.85rem;'>{cm["username"]}</span>
                        <span style='color:#484f58;font-size:0.72rem;margin-left:0.5rem;'>{cm["timestamp"][:16]}</span>
                        <p style='margin:0.25rem 0 0;color:#cdd9e5;font-size:0.88rem;'>{cm["content"]}</p>
                    </div>""", unsafe_allow_html=True)

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
        title        = st.text_input("코드 제목", placeholder="예: DeepSeek API 스트리밍 호출")
        desc         = st.text_area("설명 (선택)", placeholder="이 코드가 무엇을 하는지 간단히 설명해주세요", height=70)
        default_code = st.session_state.pop("pending_code", "")
        code         = st.text_area("코드", value=default_code, placeholder="코드를 여기에 붙여넣으세요...", height=320)
        c1, c2 = st.columns(2)
        with c1:
            lang = st.selectbox("언어", ["Python", "JavaScript", "SQL", "Bash", "기타"])
        with c2:
            tags = st.text_input("태그 (쉼표 구분)", placeholder="예: API, DeepSeek, 유틸")
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
                "<p style='color:#484f58;text-align:center;margin-top:3rem;'>"
                "💾 저장된 코드가 없습니다</p>",
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


# ====================== 페이지: 관리자 ======================
def page_admin(user):
    st.markdown("<h1>👑 관리자 패널</h1>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📊 팀 통계", "💾 데이터 백업", "⚠️ 데이터 관리"])

    with tab1:
        st.markdown("### 팀원별 활동 현황")
        conn = get_db()

        # ⑤ 관리자: 팀원별 활동 bar_chart
        act_rows = conn.execute(
            "SELECT username, COUNT(*) as cnt FROM activity_log GROUP BY username"
        ).fetchall()
        if act_rows:
            chart_df = pd.DataFrame([{"팀원": r["username"], "활동 수": r["cnt"]} for r in act_rows])
            chart_df = chart_df.set_index("팀원")
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
            st.markdown(f"""
            <div class='card card-accent' style='margin:0.5rem 0;'>
                <div style='display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;'>
                    <span style='font-size:1.3rem;'>{icon}</span>
                    <span style='color:{mc};font-weight:700;font-size:1rem;'>{name}</span>
                </div>
                <div style='display:flex;gap:1.5rem;flex-wrap:wrap;'>
                    <span>💬 대화 <b style='color:#00ffcc;'>{chats}</b></span>
                    <span>📤 공유 <b style='color:#00ffcc;'>{shared}</b></span>
                    <span>✅ 할 일 <b style='color:#00ffcc;'>{todos_c}</b></span>
                    <span>💾 코드 <b style='color:#00ffcc;'>{codes}</b></span>
                    <span>⚡ 전체 활동 <b style='color:#00ffcc;'>{acts}</b></span>
                </div>
            </div>""", unsafe_allow_html=True)
        conn.close()

        st.markdown("### 최근 활동 로그 (50개)")
        conn = get_db()
        logs = conn.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT 50").fetchall()
        conn.close()
        if logs:
            df = pd.DataFrame([dict(r) for r in logs])
            st.dataframe(
                df[["username", "action", "detail", "timestamp"]],
                use_container_width=True,
                hide_index=True
            )

    with tab2:
        st.markdown("### 💾 데이터 백업 (CSV 다운로드)")
        st.markdown(
            "<p style='color:#8b949e;font-size:0.88rem;margin-bottom:1rem;'>"
            "모든 데이터를 CSV 파일로 내보낼 수 있습니다.</p>",
            unsafe_allow_html=True
        )
        tables = {
            "chat_history": "💬 대화 기록",
            "shared_logs":  "📤 공유 로그",
            "todos":        "✅ 할 일 목록",
            "memos":        "📝 메모",
            "code_library": "💾 코드 라이브러리",
            "activity_log": "⚡ 활동 로그",
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

    with tab3:
        st.warning("⚠️ 이 작업은 되돌릴 수 없습니다. 신중히 사용해주세요.")
        target = st.selectbox("초기화 대상 선택", ["대화 기록", "활동 로그", "공유 로그", "댓글"])
        table_map = {
            "대화 기록": "chat_history",
            "활동 로그": "activity_log",
            "공유 로그": "shared_logs",
            "댓글":      "shared_comments",
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
init_deepseek()  # Gemini 통신부 삭제, DeepSeek로 교체됨

# 세션 초기화
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
    <div style='display:flex;flex-direction:column;align-items:center;justify-content:center;
                min-height:75vh;'>
        <div style='text-align:center;margin-bottom:2rem;'>
            <div style='font-size:3.5rem;'>⚓</div>
            <h1 style='color:#00ffcc;font-size:2rem;margin:0.3rem 0;'>AI 팀 관제실</h1>
            <p style='color:#8b949e;margin:0;'>POSCO DX 7회 AI 청소년 챌린지</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.1, 1])
    with col2:
        st.markdown("""
        <div style='background:linear-gradient(135deg,#161b27,#1c2333);
                    border:1px solid #30363d;border-radius:16px;padding:2rem;
                    box-shadow:0 20px 60px rgba(0,255,204,0.06);'>
        """, unsafe_allow_html=True)
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
        # 프로필
        mc = MEMBER_COLORS.get(user, "#8b949e")
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#21262d,#1c2333);
                    border-radius:12px;padding:1.1rem;margin-bottom:1rem;text-align:center;
                    border:1px solid #30363d;'>
            <div style='font-size:2rem;'>{"👑" if is_admin else "🧑‍💻"}</div>
            <div style='color:{mc};font-weight:700;font-size:1rem;margin-top:0.3rem;'>{user}</div>
            <div style='color:#484f58;font-size:0.72rem;'>{"관리자" if is_admin else "팀원"}</div>
        </div>""", unsafe_allow_html=True)

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
        if st.button("🚪  로그아웃", use_container_width=True):
            log_activity(user, "로그아웃")
            for k in ["logged_in_user", "messages", "home_idea", "show_history", "pending_code"]:
                st.session_state.pop(k, None)
            st.session_state.current_view = "home"
            st.rerun()

        st.markdown(
            "<p style='color:#21262d;font-size:0.65rem;text-align:center;margin-top:1rem;'>"
            "⚓ AI 팀 관제실 v3.0</p>",
            unsafe_allow_html=True
        )

    # ── 페이지 라우팅 ──
    v = st.session_state.current_view
    if   v == "home":              page_home(user, is_admin)
    elif v == "chat":              page_chat(user)
    elif v == "todo":              page_todo(user, is_admin)
    elif v == "memo":              page_memo(user, is_admin)
    elif v == "shared":            page_shared(user, is_admin)
    elif v == "code_library":      page_code_library(user, is_admin)
    elif v == "admin" and is_admin: page_admin(user)
