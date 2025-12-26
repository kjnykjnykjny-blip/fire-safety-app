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
            if not has_wa: red_rate += 0.1
            dist_pen = (dist_km / 5) * 0.02
            total_pen = red_rate + dist_pen
            
            std = LIMITS[inspection_type]
            
            st.markdown(f"**{target_name} ({selected_usage})**")
            
            best_sub = -1
            best_ratio = 0
            
            for sub in range(0, 6):
                capa_area = (std["area_base"] + sub*std["area_inc"]) * (1.0 - total_pen)
                capa_apt = (std["apt_base"] + sub*std["apt_inc"]) * (1.0 - total_pen)
                
                usage = 0.0
                if capa_area > 0: usage += load_area / capa_area
                if capa_apt > 0: usage += load_apt / capa_apt
                
                if usage <= 1.0:
                    best_sub = sub
                    best_ratio = usage
                    break
            
            if best_sub != -1:
                st.success(f"✅ [관리사 1명 + 보조 {best_sub}명] (1일)")
                st.progress(best_ratio, text=f"부하율: {best_ratio*100:.1f}%")
                st.caption(f"*복합용도 부하율 계산됨 ({load_area:.0f}/{capa_area:.0f} + {load_apt}/{capa_apt:.0f})")
            else:
                st.error("❌ 1일 점검 불가 (2일 소요)")

# ==========================================
# [탭 2] 공사 견적 (수정됨: 실제 공사비 산출)
# ==========================================
with tab2:
    st.header("🔨 공사 견적서 산출")
    st.caption("지적사항에 대한 보수 공사 비용을 계산합니다.")
    
    col_e1, col_e2 = st.columns([1, 1])
    
    with col_e1:
        st.subheader("항목 추가")
        item_name = st.text_input("공사명/품명", placeholder="예: 펌프 메카니컬 씰 교체")
        
        c_cost1, c_cost2 = st.columns(2)
        mat_cost = c_cost1.number_input("재료비 (원)", value=0, step=1000)
        lab_cost = c_cost2.number_input("노무비 (원)", value=0, step=10000)
        
        count = st.number_input("수량", value=1, min_value=1)
        
        if st.button("견적 항목 추가"):
            if item_name:
                total = (mat_cost + lab_cost) * count
                st.session_state.estimate_items.append({
                    "품명": item_name,
                    "재료비": mat_cost,
                    "노무비": lab_cost,
                    "수량": count,
                    "합계": total
                })
                st.success("추가됨")
            else:
                st.warning("품명을 입력하세요")

    with col_e2:
        st.subheader("💰 견적서 미리보기")
        
        # 할증 옵션 (아까 말씀하신 부분)
        st.write("**작업 조건 할증**")
        chk_night = st.checkbox("야간 작업 (노무비 50% 할증)")
        chk_high = st.checkbox("고소 작업/사다리차 사용 (별도 비용)")
        ladder_cost = 0
        if chk_high:
            ladder_cost = st.number_input("사다리차 비용 (원)", value=150000, step=10000)
        
        st.markdown("---")
        
        if len(st.session_state.estimate_items) > 0:
            df_est = pd.DataFrame(st.session_state.estimate_items)
            st.dataframe(df_est, hide_index=True)
            
            # 총계 계산
            sum_mat = df_est["재료비"].sum() * df_est["수량"].sum() # 단순합계가 아니라 행별 계산 필요하지만 약식
            # 정확한 합계 재계산
            total_mat = 0
            total_lab = 0
            for item in st.session_state.estimate_items:
                total_mat += item["재료비"] * item["수량"]
                total_lab += item["노무비"] * item["수량"]
            
            if chk_night:
                total_lab = int(total_lab * 1.5)
                st.caption("※ 야간 할증 적용됨")
                
            final_total = total_mat + total_lab + ladder_cost
            
            st.write(f"**- 재료비 소계:** {total_mat:,} 원")
            st.write(f"**- 노무비 소계:** {total_lab:,} 원")
            if chk_high:
                st.write(f"**- 장비비(사다리):** {ladder_cost:,} 원")
            
            st.markdown("### 🧾 총 견적금액: " + f":blue[{final_total:,} 원]")
            
            if st.button("견적 초기화"):
                st.session_state.estimate_items = []
                st.rerun()
        else:
            st.info("왼쪽에서 항목을 추가해주세요.")

# ==========================================
# [탭 3] 지적 관리 (자동저장 유지)
# ==========================================
with tab3:
    st.header("📝 지적내역서 (자동 저장)")
    
    col_in, col_list = st.columns([1, 1.5])
    
    with col_in:
        d_code = st.text_input("점검 코드 (PDF 기준)", placeholder="예: 32-C-021")
        
        auto_msg = DEFECT_DB.get(d_code, "")
        if auto_msg: st.success(f"매칭: {auto_msg}")
            
        d_loc = st.text_input("위치", placeholder="예: 1층 로비")
        d_desc = st.text_area("내용", value=auto_msg, height=100)
        
        if st.button("지적사항 추가"):
            if d_desc:
                st.session_state.defects_list.append(
                    {"코드": d_code, "위치": d_loc, "내용": d_desc}
                )
    
    with col_list:
        if st.session_state.defects_list:
            st.dataframe(pd.DataFrame(st.session_state.defects_list), hide_index=True)
