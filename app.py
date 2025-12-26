import streamlit as st
import pandas as pd
from datetime import date

# --- 페이지 설정 ---
st.set_page_config(page_title="소방점검 마스터 Pro", page_icon="🔥", layout="wide")

# --- 1. 법적 기준 데이터 ---
LIMITS = {
    "종합": {"area_base": 8000, "area_inc": 2000, "apt_base": 250, "apt_inc": 60},
    "작동": {"area_base": 10000, "area_inc": 2500, "apt_base": 250, "apt_inc": 60}
}

# [수정] 용도 리스트 (1류, 2류 명시 + 세부 용도 포함)
# 협회 스크린샷처럼 등급과 용도를 같이 보여줍니다.
USAGE_OPTIONS = {
    "1류": [
        "[1류] 복합건축물 (근생+주거 등)", 
        "[1류] 근린생활시설 (연면적 5천㎡ 이상 등)", 
        "[1류] 판매시설 (백화점, 대형마트)",
        "[1류] 문화집회시설 (영화관 등)",
        "[1류] 의료시설 (종합병원)",
        "[1류] 숙박시설 (호텔)",
        "[1류] 노유자시설",
        "[1류] 위락시설"
    ],
    "2류": [
        "[2류] 공동주택 (아파트)", 
        "[2류] 업무시설 (오피스텔)", 
        "[2류] 공장", 
        "[2류] 주차장",
        "[2류] 항공기/자동차관련",
        "[2류] 방송통신/교육연구"
    ],
    "3류": ["[3류] 동식물관련", "[3류] 교정/군사", "[3류] 묘지/장례"],
    "4류": ["[4류] 기타 해당사항"],
    "지하구": ["[특수] 지하구"]
}

# 계수 매핑
def get_k_factor(selected_text):
    if "[1류]" in selected_text: return 1.1
    if "[2류]" in selected_text: return 1.0
    if "[3류]" in selected_text: return 0.9
    if "[4류]" in selected_text: return 0.8
    if "[특수]" in selected_text: return 2.0
    return 1.0

# [3] 점검 항목 DB (PDF 기반 자동완성)
DEFECT_DB = {
    "1-A-003": "소화기 미비치 (보행거리 초과)",
    "1-A-007": "소화기 충압 불량 (게이지 불량)",
    "32-C-021": "유도등 상시 점등 불량 (3선식 포함)",
    "32-C-022": "유도등 시각장애 발생 (가려짐 등)",
    "32-C-023": "유도등 예비전원 불량 (배터리 방전)",
    "P-001": "소화전 펌프 기동 불량 (압력스위치 확인 요)",
    "S-001": "준비작동식 밸브(프리액션) 솔레노이드 고장",
    "D-001": "감지기 선로 단선 (발신기 LED 미점등)"
}

# --- 세션 상태 초기화 ---
if 'defects_list' not in st.session_state:
    st.session_state.defects_list = []
if 'estimate_items' not in st.session_state:
    st.session_state.estimate_items = []

st.title("🔥 소방점검 마스터 Pro")
st.caption("배치신고 | 공사견적 | 지적내역서")
st.divider()

# 탭 구성
tab1, tab2, tab3 = st.tabs(["🧮 1. 배치 확인", "🔨 2. 공사 견적", "📝 3. 지적 관리"])

# ==========================================
# [탭 1] 배치 확인 (1류/2류 명확화)
# ==========================================
with tab1:
    with st.expander("📂 엑셀 불러오기", expanded=False):
        uploaded_file = st.file_uploader("대상처 엑셀 파일", type=['xlsx', 'xls'])
        df = None
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.success(f"{len(df)}개 로딩됨")
            except: pass

    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("🏗️ 대상물 정보")
        target_name = st.text_input("대상명", placeholder="예: 갤럭시타워")
        
        # [수정] 용도 선택 (1류, 2류 리스트 통합 표시)
        all_options = []
        for key in ["1류", "2류", "3류", "4류", "지하구"]:
            all_options.extend(USAGE_OPTIONS[key])
            
        selected_usage = st.selectbox("용도 분류 (협회 기준)", all_options, index=0)
        k_factor = get_k_factor(selected_usage)
        st.info(f"👉 적용 계수: {k_factor} ({selected_usage.split(']')[0]}])")

        # 현황 입력
        col_i1, col_i2 = st.columns(2)
        input_area = col_i1.number_input("연면적 (㎡)", value=0.0, step=100.0)
        input_apt = col_i2.number_input("아파트 세대수", value=0, step=10)
        
        dist_km = st.number_input("이동 거리 (km)", value=0.0)

        st.write("설비 감산 (미설치 시 체크해제)")
        ck1, ck2, ck3 = st.columns(3)
        has_sp = ck1.checkbox("SP", value=True)
        has_sm = ck2.checkbox("제연", value=True)
        has_wa = ck3.checkbox("물분무", value=True)
        
        inspection_type = st.radio("점검 종류", ["종합", "작동"], horizontal=True)

    with c2:
        st.subheader("📊 배치 결과")
        if st.button("계산 실행", type="primary", use_container_width=True):
            load_area = input_area * k_factor
            load_apt = input_apt
            
            # 감산율
            red_rate = 0.0
            if not has_sp: red_rate += 0.1
            if not has_sm: red_rate += 0.1
            if not has_wa
