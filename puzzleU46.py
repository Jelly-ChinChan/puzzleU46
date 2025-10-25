import streamlit as st
import random
import uuid
import pandas as pd

# ====== App 基本設定 ======
st.set_page_config(
    page_title="Puzzle for U4~U6",
    page_icon="📝",
    layout="centered"
)

# ====== CSS：sidebar保留 / 頂貼 / footer隱藏 / 按鈕樣式 ======
st.markdown("""
<style>

/* 隱藏 Streamlit 預設 header / toolbar / footer */
header[data-testid="stHeader"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
footer,
div[role="contentinfo"],
div[data-testid="stStatusWidget"],
div[class*="viewerBadge_container"],
div[class*="stActionButtonIcon"],
div[class*="stDeployButton"],
div[data-testid="stDecoration"],
div[data-testid="stMainMenu"],
div[class*="stFloatingActionButton"],
a[class^="css-"][href*="streamlit.io"],
button[kind="header"] {
    display: none !important;
}

/* 主畫面往上貼 */
div[data-testid="stAppViewContainer"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
div[data-testid="stAppViewBlockContainer"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
main.block-container,
.block-container,
div[data-testid="stVerticalBlock"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
.block-container {
    padding-bottom: 0.9rem !important;
    max-width: 1000px;
}

/* 進度卡片 */
.progress-card {
    margin-top: 0 !important;
    margin-bottom: 0.22rem !important;
}

/* 字體/行高 */
html, body, [class*="css"]  {
    font-size: 22px !important;
}
h1, h2, h3 {
    line-height: 1.35em !important;
}
h2 {
    font-size: 26px !important;
    margin-top: 0.22em !important;
    margin-bottom: 0.22em !important;
}

/* 單選題區塊靠緊標題 */
.stRadio { margin-top: 0 !important; }
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stRadio"]) {
    margin-top: 0 !important;
}

/* 主按鈕 */
.stButton>button{
    height: 44px;
    padding: 0 18px;
    font-size: 20px;
    border-radius: 12px;
    border: 1px solid rgba(0,0,0,0.2);
}

/* 答對 / 答錯 提示 */
.feedback-small {
    font-size: 17px !important;
    line-height: 1.4;
    margin: 6px 0 2px 0;
    display: inline-block;
    padding: 4px 6px;
    border-radius: 6px;
    border: 2px solid transparent;
    font-weight: 700;
}
.feedback-correct {
    color: #1a7f37;
    border-color: #1a7f37;
    background-color: #e8f5e9;
}
.feedback-wrong {
    color: #c62828;
    border-color: #c62828;
    background-color: #ffebee;
}

/* 模式三手寫輸入框放大 */
.text-input-big input {
    font-size: 24px !important;
    height: 3em !important;
    border-radius: 10px !important;
    border: 1px solid rgba(0,0,0,0.3) !important;
}

</style>
""", unsafe_allow_html=True)


# ===================== 題庫讀取：English / Chinese 兩欄 =====================
@st.cache_data
def load_question_bank(xlsx_path="puzzleU46.xlsx"):
    """
    自動對應：
      english_col ← ["english","英文","term","英文名","en","english term"]
      chinese_col ← ["chinese","中文","名稱","name","cn","chinese name","中文名"]

    回傳:
    {
        "ok": bool,
        "error": str,
        "bank": [ { "english":..., "chinese":...}, ... ],
        "debug_cols": [...]
    }
    """
    try:
        df = pd.read_excel(xlsx_path)
    except Exception as e:
        return {
            "ok": False,
            "error": f"無法讀取題庫檔案 {xlsx_path} ：{e}",
            "bank": [],
            "debug_cols": []
        }

    def norm(s):
        return str(s).strip().lower()

    cols_norm = {norm(c): c for c in df.columns}

    eng_candidates = [
        "english","英文","term","英文名","en","english term"
    ]
    chi_candidates = [
        "chinese","中文","名稱","name","cn","chinese name","中文名"
    ]

    def pick_col(cands):
        for cand in cands:
            if cand in cols_norm:
                return cols_norm[cand]
        return None

    eng_col = pick_col(eng_candidates)
    chi_col = pick_col(chi_candidates)

    if eng_col is None or chi_col is None:
        return {
            "ok": False,
            "error": (
                "找不到必要欄位。\n"
                f"檔案欄位：{list(df.columns)}\n"
                f"English 欄候選：{eng_candidates}\n"
                f"Chinese 欄候選：{chi_candidates}\n"
                "請把 Excel 欄位命名成其中一個候選名稱（如 English / Chinese）。"
            ),
            "bank": [],
            "debug_cols": list(df.columns)
        }

    def clean(v):
        if pd.isna(v):
            return ""
        return str(v).strip()

    bank_list = []
    for _, row in df.iterrows():
        en = clean(row.get(eng_col, ""))
        ch = clean(row.get(chi_col, ""))
        if en and ch:
            bank_list.append({"english": en, "chinese": ch})

    return {
        "ok": True,
        "error": "",
        "bank": bank_list,
        "debug_cols": list(df.columns)
    }

loaded = load_question_bank()
QUESTION_BANK = loaded["bank"]

if not loaded["ok"] or not QUESTION_BANK:
    st.error("⚠ 題庫讀取失敗或為空，請檢查 Excel 欄位（需要 English / Chinese）。")
    st.stop()


# ===================== 遊戲常數 =====================
MAX_ROUNDS = 3
QUESTIONS_PER_ROUND = 10

MODE_1 = "模式一：English ➜ 中文"
MODE_2 = "模式二：中文 ➜ English"
MODE_3 = "模式三：中文 ➜ English（手寫，提示首尾）"
MODE_4 = "模式四：混合 (1~3)"

ALL_MODES = [MODE_1, MODE_2, MODE_3, MODE_4]

SUBMODE_NAME_TO_CODE = {
    MODE_1: "eng_to_chi_mc",       # 題幹 English，答案選 Chinese (單選)
    MODE_2: "chi_to_eng_mc",       # 題幹 Chinese，答案選 English (單選)
    MODE_3: "chi_to_eng_input",    # 題幹 Chinese，輸入 English
}

SUBMODE_LIST_FOR_MIX = [
    "eng_to_chi_mc",
    "chi_to_eng_mc",
    "chi_to_eng_input"
]


# ===================== 狀態初始化 =====================
def init_quiz_state():
    """初始化 quiz 運行用 state，不動玩家個資"""
    st.session_state.round = 1                 # 當前回合 (1..MAX_ROUNDS) / None=結束
    st.session_state.cur_round_qidx = []       # 這回合的題目 index 清單
    st.session_state.cur_idx_in_round = 0      # 目前在第幾題 (0-based)
    st.session_state.score_this_round = 0      # 本回合得分
    st.session_state.submitted = False         # 這一題是否已經送出
    st.session_state.last_feedback = ""        # 顯示在題目下方的HTML
    st.session_state.answer_cache = ""         # 模式三的輸入暫存
    st.session_state.options_cache = {}        # (qidx, submode_code)-> {"display":[...]}
    st.session_state.submode_per_question = [] # 與 cur_round_qidx 對齊
    st.session_state.records = []              # 全部作答紀錄(跨回合)
    st.session_state.used_keys = set()         # 用過的英文詞，避免重複
    st.session_state.ask_continue = False      # 回合結束後：要不要繼續？出現詢問畫面
    st.session_state.quiz_done = False         # 全部結束了沒
    st.session_state.show_wrong_review = False # 是否顯示錯題回顧畫面

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())


def ensure_state_ready():
    base_keys = [
        "mode_locked",
        "chosen_mode_label",
        "user_name",
        "user_class",
        "user_seat",
        "round",
        "cur_round_qidx",
        "cur_idx_in_round",
        "score_this_round",
        "submitted",
        "last_feedback",
        "answer_cache",
        "options_cache",
        "session_id",
        "submode_per_question",
        "records",
        "used_keys",
        "ask_continue",
        "quiz_done",
        "show_wrong_review"
    ]
    if any(k not in st.session_state for k in base_keys):
        if "mode_locked" not in st.session_state:
            st.session_state.mode_locked = False
        if "chosen_mode_label" not in st.session_state:
            st.session_state.chosen_mode_label = None
        if "user_name" not in st.session_state:
            st.session_state.user_name = ""
        if "user_class" not in st.session_state:
            st.session_state.user_class = ""
        if "user_seat" not in st.session_state:
            st.session_state.user_seat = ""
        init_quiz_state()


def start_new_round():
    """抽新回合10題 + 安排子模式"""
    # 避免重複：以 english 當 key
    remaining = [
        i for i, it in enumerate(QUESTION_BANK)
        if it["english"] not in st.session_state.used_keys
    ]
    # 如果都用光了，就清空 used_keys
    if not remaining:
        st.session_state.used_keys = set()
        remaining = list(range(len(QUESTION_BANK)))

    # 抽題
    if len(remaining) <= QUESTIONS_PER_ROUND:
        chosen = remaining[:]
        random.shuffle(chosen)
    else:
        chosen = random.sample(remaining, QUESTIONS_PER_ROUND)

    st.session_state.cur_round_qidx = chosen
    st.session_state.cur_idx_in_round = 0
    st.session_state.score_this_round = 0
    st.session_state.submitted = False
    st.session_state.last_feedback = ""
    st.session_state.answer_cache = ""
    st.session_state.options_cache = {}
    st.session_state.ask_continue = False

    # 產生每題子模式
    if st.session_state.chosen_mode_label == MODE_4:
        st.session_state.submode_per_question = [
            random.choice(SUBMODE_LIST_FOR_MIX) for _ in chosen
        ]
    else:
        code = SUBMODE_NAME_TO_CODE[st.session_state.chosen_mode_label]
        st.session_state.submode_per_question = [code for _ in chosen]


ensure_state_ready()
if st.session_state.mode_locked and st.session_state.round and not st.session_state.cur_round_qidx:
    # first entry into quiz page after picking mode
    start_new_round()


# ===================== 工具：產生選項 (for MC modes) =====================
def get_options_for_q(qidx, submode_code):
    """
    submode_code:
      eng_to_chi_mc    題幹 English，選 Chinese
      chi_to_eng_mc    題幹 Chinese，選 English
      chi_to_eng_input 手寫 => 不用選項
    回傳:
      { "display": [...兩個選項字串...] }  (only for MC)
    """
    key = (qidx, submode_code)
    if key in st.session_state.options_cache:
        return st.session_state.options_cache[key]

    item = QUESTION_BANK[qidx]
    correct_en = item["english"].strip()
    correct_ch = item["chinese"].strip()

    pool_en = [it["english"].strip() for it in QUESTION_BANK
               if it["english"].strip().lower() != correct_en.lower()]
    pool_ch = [it["chinese"].strip() for it in QUESTION_BANK
               if it["chinese"].strip() != correct_ch]

    if submode_code == "eng_to_chi_mc":
        # 正解 = 中文
        distractor = random.choice(pool_ch) if pool_ch else "???"
        opts = [correct_ch, distractor]

    elif submode_code == "chi_to_eng_mc":
        # 正解 = English
        distractor = random.choice(pool_en) if pool_en else "???"
        opts = [correct_en, distractor]

    else:
        # 手寫模式不需要選項
        st.session_state.options_cache[key] = {"display": []}
        return {"display": []}

    random.shuffle(opts)
    st.session_state.options_cache[key] = {"display": opts[:]}
    return {"display": opts[:]}


def build_question_prompt(qidx, submode_code):
    """回傳題目文字 + 正解(英/中) + 額外提示(模式三)"""
    item = QUESTION_BANK[qidx]
    en = item["english"].strip()
    ch = item["chinese"].strip()

    if submode_code == "eng_to_chi_mc":
        # 給英文，問中文
        prompt_txt = en
        question_text = f'「{prompt_txt}」對應的正確中文是？'
        correct_answer = ch
        hint = ""
    elif submode_code == "chi_to_eng_mc":
        # 給中文，問英文 (選擇)
        prompt_txt = ch
        question_text = f'「{prompt_txt}」的正確英文是？'
        correct_answer = en
        hint = ""
    else:
        # chi_to_eng_input：給中文，手寫英文
        prompt_txt = ch
        # 提示：英文首尾字母
        if len(en) >= 2:
            hint = f"(提示: {en[0]} ... {en[-1]})"
        else:
            hint = f"(提示: {en})"
        question_text = f'「{prompt_txt}」的正確英文是？ {hint}'
        correct_answer = en

    return question_text, correct_answer, item, hint


def prompt_for_record(qidx, submode_code):
    """存進 records 裡的題幹文字"""
    item = QUESTION_BANK[qidx]
    if submode_code == "eng_to_chi_mc":
        return item["english"].strip()
    else:
        # chi_to_eng_mc or chi_to_eng_input
        return item["chinese"].strip()


# ===================== 回合內 top 卡 =====================
def render_top_card():
    r = st.session_state.round
    i = st.session_state.cur_idx_in_round + 1
    n = len(st.session_state.cur_round_qidx)
    percent = int(i / n * 100) if n else 0
    st.markdown(
        f"""
        <div class="progress-card"
             style='background-color:#f5f5f5;
                    padding:9px 14px;
                    border-radius:12px;'>
            <div style='display:flex;
                        align-items:center;
                        justify-content:space-between;
                        margin-bottom:4px;'>
                <div style='font-size:18px;'>
                    🎯 第 {r} 回合｜進度：{i} / {n}
                </div>
                <div style='font-size:16px; color:#555;'>{percent}%</div>
            </div>
            <progress value='{i}' max='{n if n else 1}'
                      style='width:100%; height:14px;'></progress>
        </div>
        """,
        unsafe_allow_html=True
    )


# ===================== 單題顯示 =====================
def render_question_block():
    cur_pos = st.session_state.cur_idx_in_round
    qidx = st.session_state.cur_round_qidx[cur_pos]
    submode_code = st.session_state.submode_per_question[cur_pos]

    qtext, correct_answer, item, hint = build_question_prompt(qidx, submode_code)

    st.markdown(f"<h2>Q{cur_pos + 1}. {qtext}</h2>", unsafe_allow_html=True)

    user_choice_label = None
    typed_answer = None

    if submode_code in ["eng_to_chi_mc", "chi_to_eng_mc"]:
        payload = get_options_for_q(qidx, submode_code)
        options_disp = payload["display"]
        if options_disp:
            user_choice_label = st.radio(
                "",
                options_disp,
                key=f"mc_{qidx}",
                label_visibility="collapsed"
            )
        return qidx, submode_code, correct_answer, item, ("mc", user_choice_label, payload)

    else:
        # 手寫模式
        default_val = st.session_state.answer_cache if st.session_state.submitted else ""
        typed_answer = st.text_input(
            "請輸入英文答案：",
            value=default_val,
            key=f"inp_{qidx}",
            label_visibility="collapsed",
            placeholder="Type the English term here",
        )
        return qidx, submode_code, correct_answer, item, ("input", typed_answer, None)


# ===================== 處理作答按鈕 =====================
def handle_action(qidx, submode_code, correct_answer, item, user_input):
    """
    user_input:
      ("mc", chosen_label, payload)
      ("input", typed_answer, None)
    """
    ui_type, data, payload = user_input

    # 把正確英文記錄進 used_keys，避免重複抽
    st.session_state.used_keys.add(item["english"].strip())

    # 決定學生答案字串
    if ui_type == "mc":
        if data is None:
            st.warning("請先選擇一個選項。")
            return
        student_answer = data.strip()
    else:
        student_answer = (data or "").strip()
        # 同時緩存到 answer_cache，方便重新rerun時保留
        st.session_state.answer_cache = student_answer

    # 判斷正確與否 (模式三：不理大小寫 / 前後空白)
    is_correct = (student_answer.lower() == correct_answer.lower())

    # 如果還沒 submit -> 這次當成交卷
    if not st.session_state.submitted:
        st.session_state.submitted = True

        # 記錄
        st.session_state.records.append((
            st.session_state.round,           # 回合數
            prompt_for_record(qidx, submode_code),  # 題幹(中文或英文)
            student_answer,                   # 學生答
            correct_answer,                   # 正解
            is_correct,                       # bool
            (payload["display"] if (payload and "display" in payload) else None),
            submode_code                      # 題型
        ))

        # 設定 feedback
        if is_correct:
            st.session_state.score_this_round += 1
            st.session_state.last_feedback = (
                "<div class='feedback-small feedback-correct'>✅ 回答正確</div>"
            )
        else:
            if submode_code == "eng_to_chi_mc":
                # 給英文->中文
                st.session_state.last_feedback = (
                    f"<div class='feedback-small feedback-wrong'>❌ Incorrect. "
                    f"正確中文：{item['chinese'].strip()} "
                    f"（English: {item['english'].strip()}）</div>"
                )
            elif submode_code == "chi_to_eng_mc":
                # 給中文->英文(選)
                st.session_state.last_feedback = (
                    f"<div class='feedback-small feedback-wrong'>❌ Incorrect. "
                    f"正確英文：{item['english'].strip()} "
                    f"（中文：{item['chinese'].strip()}）</div>"
                )
            else:
                # 手寫
                st.session_state.last_feedback = (
                    f"<div class='feedback-small feedback-wrong'>❌ Incorrect. "
                    f"正確英文：{item['english'].strip()} "
                    f"（中文：{item['chinese'].strip()}）</div>"
                )

        st.rerun()
        return

    # 如果已經 submit 了 -> 這次按視為「下一題」
    else:
        # 進下一題
        st.session_state.cur_idx_in_round += 1
        st.session_state.submitted = False
        st.session_state.last_feedback = ""
        st.session_state.answer_cache = ""

        # 回合是否打完？
        if st.session_state.cur_idx_in_round >= len(st.session_state.cur_round_qidx):
            # 回合完整結束
            # 是否還可以下一回合？
            if st.session_state.round < MAX_ROUNDS:
                # 問要不要繼續
                st.session_state.ask_continue = True
            else:
                # 第三回合打完，整個結束
                st.session_state.quiz_done = True
                st.session_state.round = None

        st.rerun()
        return


# ===================== 回合結束：詢問是否繼續 =====================
def render_continue_prompt():
    st.subheader("本回合完成！")
    this_round_score = st.session_state.score_this_round
    this_round_total = len(st.session_state.cur_round_qidx)
    st.markdown(f"本回合成績：**{this_round_score} / {this_round_total}**")

    st.write("是否繼續下一回合？（最多三回合）")

    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Yes ▶ 下一回合"):
            # 進入下一回合
            st.session_state.round += 1
            st.session_state.ask_continue = False
            start_new_round()
            st.rerun()
    with col_no:
        if st.button("No ❌ 結束並檢視錯題"):
            st.session_state.ask_continue = False
            st.session_state.quiz_done = True
            st.session_state.round = None
            st.session_state.show_wrong_review = True
            st.rerun()


# ===================== 最後總結 + 錯題回顧 =====================
def render_final_summary():
    # 計算總成績
    total_answered = len(st.session_state.records)
    total_correct = sum(1 for rec in st.session_state.records if rec[4])
    acc = (total_correct / total_answered * 100) if total_answered else 0.0

    st.subheader("📊 總結")
    st.markdown(f"<h3>Total Answered: {total_answered}</h3>", unsafe_allow_html=True)
    st.markdown(f"<h3>Total Correct: {total_correct}</h3>", unsafe_allow_html=True)
    st.markdown(f"<h3>Accuracy: {acc:.1f}%</h3>", unsafe_allow_html=True)

    wrong_list = [r for r in st.session_state.records if not r[4]]
    if wrong_list:
        # 顯示一個按鈕才能打開錯題，避免一開始太多文字
        if st.button("📚 顯示本次錯題回顧"):
            st.session_state.show_wrong_review = True
            st.rerun()
    else:
        st.info("恭喜！沒有錯題 🎉")

    # 再玩一次 / 回到模式選擇
    st.markdown("---")
    if st.button("🔄 再玩一次（同模式）"):
        init_quiz_state()
        start_new_round()
        st.session_state.mode_locked = True
        st.rerun()

    if st.button("🧪 選別的模式"):
        st.session_state.mode_locked = False
        st.session_state.chosen_mode_label = None
        init_quiz_state()
        st.rerun()


def render_wrong_review():
    wrong_list = [r for r in st.session_state.records if not r[4]]
    if not wrong_list:
        st.info("沒有錯題 🎉")
        return

    st.subheader("❌ 錯題回顧")
    # records: (round, prompt, student_answer, correct_answer, is_correct, opts, submode_code)
    for idx, rec in enumerate(wrong_list, start=1):
        rnd, prompt_txt, stu_ans, corr_ans, _, _, submode_code = rec
        st.markdown(f"**#{idx} (回合 {rnd})**")
        if submode_code == "eng_to_chi_mc":
            # prompt_txt 是 English 單字
            st.write(f"英文題目：{prompt_txt}")
            st.write(f"你的中文答案：{stu_ans}")
            st.write(f"正確中文：{corr_ans}")
        else:
            # chi_to_eng_mc / chi_to_eng_input
            # prompt_txt 是 中文詞
            st.write(f"中文題目：{prompt_txt}")
            st.write(f"你的英文答案：{stu_ans}")
            st.write(f"正確英文：{corr_ans}")
        st.markdown("---")


# ===================== Page A：模式選擇 =====================
def render_mode_select_page():
    st.markdown("## 選擇練習模式")
    st.write("請選一種模式後開始作答：")

    chosen = st.radio(
        "練習模式",
        ALL_MODES,
        index=0,
        key="mode_pick_for_start"
    )



    if st.button("開始作答 ▶"):
        # 鎖模式
        st.session_state.chosen_mode_label = chosen
        st.session_state.mode_locked = True
        init_quiz_state()
        st.session_state.chosen_mode_label = chosen
        start_new_round()
        st.rerun()


# ===================== Page B：測驗頁 =====================
def render_quiz_page():
    # sidebar
    with st.sidebar:
        st.markdown("### 你的資訊")
        st.text_input("姓名", st.session_state.get("user_name", ""), key="user_name")
        st.text_input("班級", st.session_state.get("user_class", ""), key="user_class")
        st.text_input("座號", st.session_state.get("user_seat", ""), key="user_seat")

        st.markdown("---")
        st.write("模式已鎖定：")
        st.write(st.session_state.chosen_mode_label)

        if st.button("🔄 重新開始（重新選模式）"):
            st.session_state.mode_locked = False
            st.session_state.chosen_mode_label = None
            init_quiz_state()
            st.rerun()

    # 主區邏輯
    if st.session_state.quiz_done:
        # 整個遊戲結束
        render_final_summary()
        if st.session_state.show_wrong_review:
            st.markdown("---")
            render_wrong_review()
        return

    # 還沒結束整個遊戲，但一回合打完，正在問要不要繼續
    if st.session_state.ask_continue:
        render_continue_prompt()
        return

    # 回合中 (normal question flow)
    if st.session_state.round:
        render_top_card()
        qidx, submode_code, correct_answer, item, user_input = render_question_block()

        # 如果本題已經提交，顯示 feedback
        if st.session_state.submitted and st.session_state.last_feedback:
            st.markdown(st.session_state.last_feedback, unsafe_allow_html=True)

        # 主按鈕
        label_now = "下一題" if st.session_state.submitted else "送出答案"
        if st.button(label_now, key="action_btn"):
            handle_action(qidx, submode_code, correct_answer, item, user_input)

        # 題目提交後的小複習
        if st.session_state.submitted and st.session_state.records:
            last = st.session_state.records[-1]
            # last: (round, prompt_txt, stu_ans, correct_answer, is_correct, opts, submode_code)
            _, prompt_txt, _, corr, _, opts_disp, last_mode = last

            st.markdown("---")
            if last_mode == "eng_to_chi_mc":
                # prompt_txt 是英文，corr 是正確中文
                st.markdown(
                    f"**正確中文：{item['chinese'].strip()}** "
                    f"(English: {item['english'].strip()})"
                )
            else:
                # chi_to_eng_mc / chi_to_eng_input
                st.markdown(
                    f"**正確英文：{item['english'].strip()}** "
                    f"(中文：{item['chinese'].strip()})"
                )

            # 顯示本題兩個選項（若是選擇題）
            if last_mode in ["eng_to_chi_mc", "chi_to_eng_mc"] and opts_disp:
                st.markdown("**本題兩個選項：**")
                nice_list = []
                for opt in opts_disp:
                    opt_clean = opt.strip().lower()
                    match_item = None
                    for it in QUESTION_BANK:
                        if it["english"].strip().lower() == opt_clean or it["chinese"].strip() == opt.strip():
                            match_item = it
                            break
                    if match_item:
                        nice_list.append(
                            f"{match_item['english'].strip()} / {match_item['chinese'].strip()}"
                        )
                    else:
                        nice_list.append(opt.strip())
                st.markdown("、".join(nice_list))

    else:
        # 理論上不應該到這（round=None 但 quiz_done=False 情況少見）
        st.session_state.quiz_done = True
        st.rerun()


# ===================== Router =====================
if not st.session_state.mode_locked:
    render_mode_select_page()
else:
    render_quiz_page()
