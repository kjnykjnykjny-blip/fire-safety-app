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

# [2] 용도 리스트 (협회 기준 상세)
USAGE_OPTIONS = {
    "1류": [
        "[1류] 복합건축물 (근생+주거 등)", 
        "[1류] 근린생활시설 (5천㎡ 이상)", 
        "[1류] 판매시설 (백화점, 마트)",
        "[1류] 문화집회시설",
        "[1류] 의료시설",
        "[1류] 숙박시설",
        "[1류] 노유자시설",
        "[1류] 위락시설"
    ],
    "2류": [
        "[2류] 공동주택 (아파트)", 
        "[2류] 업무시설 (오피스텔)", 
        "[2류] 공장", 
        "[2류] 주차장",
        "[2류] 항공기/자동차",
        "[2류] 방송통신/교육연구"
    ],
    "3류": ["[3류] 동식물/위험물/교정/묘지"],
    "4류": ["[4류] 기타"],
    "지하구": ["[특수] 지하구"]
}

# 계수 찾기 함수
def get_k_factor(selected_text):
    if "[1류]" in selected_text: return 1.1
    if "[2류]" in selected_text: return 1.0
    if "[3류]" in selected_text: return 0.9
    if "[4류]" in selected_text: return 0.8
    if "[특수]" in selected_text: return 2.0
    return 1.0

# [3] 점검 항목 DB (자동완성용)
DEFECT_DB = {
    "1-A-003": "소화기 미비치로 비치요함 (보행거리)",
    "1-A-007": "소화기 충압불량으로 교체요함",
    "1-A-008": "소화기 내용연수 경과로 교체요함",
    "32-C-021": "유도등 상시 (3선식의 경우 점검스위치 작동시) 점등 불량",
    "32-C-022": "유도등 시각장애(장애물 등으로 인한 시각장애 유무) 여부",
    "32-C-023": "비상전원 성능 적정 및 상용전원 차단 시 예비전원 자동전환 불량",
    "P-001": "소화전 펌프 기동 불량 (압력스위치 확인 요)",
    "S-001": "준비작동식 밸브(프리액션) 솔레노이드 고장",
    "D-001": "감지기 선로 단선 (발신기 LED 미점등)"
}

# --- 데이터 저장소 초기화 ---
if 'defects_list' not in st.session_state:
    st.session_state.defects_list = []
if 'estimate_items' not in st.session_state:
    st.session_state.estimate_items = []
if 'calc_result' not in st.session_state:
    st.session_state.calc_result = {}

st.title("🔥 소방점검 마스터 Pro")
st.caption("배치신고 | 견적산출 | 지적내역서")
st.divider()

# 탭 메뉴
tab1, tab2, tab3 = st.tabs(["🧮 1. 배치 확인", "🔨 2. 공사 견적", "📝 3. 지적 관리"])

# ==========================================
# [탭 1] 배치 확인
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

    # 좌우 나누기
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🏗️ 대상물 정보")
        target_name = st.text_input("대상명", placeholder="예: 갤럭시타워")
        
        # 용도 선택
        all_options = []
        for key in ["1류", "2류", "3류", "4류", "지하구"]:
            all_options.extend(USAGE_OPTIONS[key])
        selected_usage = st.selectbox("용도 분류", all_options)
        
        k_factor = get_k_factor(selected_usage)
        st.caption(f"적용 계수: {k_factor}")

        # 현황 입력
        input_area = st.number_input("연면적 (㎡)", value=0.0, step=100.0)
        input_apt = st.number_input("아파트 세대수", value=0, step=10)
        dist_km = st.number_input("이동 거리 (km)", value=0.0)

        # 감산 체크
        st.write("---")
        st.write("**설비 감산 (미설치 시 해제)**")
        has_sp = st.checkbox("스프링클러", value=True)
        has_sm = st.checkbox("제연설비", value=True)
        has_wa = st.checkbox("물분무등", value=True)
        
        inspection_type = st.radio("점검 종류", ["종합", "작동"], horizontal=True)

    with c2:
        st.subheader("📊 배치 결과")
        if st.button("계산 실행", type="primary", use_container_width=True):
            # 계산 로직
            load_area = input_area * k_factor
            load_apt = input_apt
            
            # 감산 적용 (오류 수정된 부분)
            red_rate = 0.0
            if not has_sp:
                red_rate += 0.1
            if not has_sm:
                red_rate += 0.1
            if not has_wa:
                red_rate += 0.1
            
            dist_pen = (dist_km / 5) * 0.02
            total_pen = red_rate + dist_pen
            
            std = LIMITS[inspection_type]
            
            # 최적 인력 찾기
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
            
            # 결과 저장
            res = {
                "name": target_name, 
                "main": 1, 
                "sub": best_sub if best_sub != -1 else 5, 
                "possible": (best_sub != -1)
            }
            st.session_state.calc_result = res
            
            if best_sub != -1:
                st.success(f"✅ [관리사 1명 + 보조 {best_sub}명] (1일)")
                st.progress(best_ratio, text=f"부하율: {best_ratio*100:.1f}%")
                st.caption(f"복합용도 합산 계산됨 ({target_name})")
            else:
                st.error("❌ 1일 점검 불가 (2일 소요)")
                st.write("인력을 최대로 늘려도 부족합니다.")

# ==========================================
# [탭 2] 공사 견적
# ==========================================
with tab2:
    st.header("🔨 공사 견적서 산출")
    
    col_e1, col_e2 = st.columns(2)
    
    with col_e1:
        st.subheader("항목 입력")
        item_name = st.text_input("공사명/품명", placeholder="예: 펌프 교체")
        mat_cost = st.number_input("재료비 (원)", value=0, step=1000)
        lab_cost = st.number_input("노무비 (원)", value=0, step=10000)
        count = st.number_input("수량", value=1, min_value=1)
        
        if st.button("항목 추가"):
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

    with col_e2:
        st.subheader("💰 견적서 미리보기")
        
        st.write("**[할증 옵션]**")
        chk_night = st.checkbox("야간 작업 (노무비 50% 할증)")
        chk_high = st.checkbox("고소차/사다리차 사용")
        ladder_cost = 0
        if chk_high:
            ladder_cost = st.number_input("장비비 (원)", value=150000, step=10000)
        
        st.markdown("---")
        
        if st.session_state.estimate_items:
            df_est = pd.DataFrame(st.session_state.estimate_items)
            st.dataframe(df_est, hide_index=True, use_container_width=True)
            
            total_mat = 0
            total_lab = 0
            for item in st.session_state.estimate_items:
                total_mat += item["재료비"] * item["수량"]
                total_lab += item["노무비"] * item["수량"]
            
            if chk_night:
                total_lab = int(total_lab * 1.5)
                st.caption("※ 야간 할증 적용")
                
            final_total = total_mat + total_lab + ladder_cost
            
            st.write(f"- 재료비: {total_mat:,}원")
            st.write(f"- 노무비: {total_lab:,}원")
            st.write(f"- 장비비: {ladder_cost:,}원")
            st.metric(label="총 견적금액", value=f"{final_total:,} 원")
            
            if st.button("초기화"):
                st.session_state.estimate_items = []
                st.rerun()

# ==========================================
# [탭 3] 지적 관리
# ==========================================
with tab3:
    st.header("📝 지적내역서")
    
    col_in, col_list = st.columns([1, 1.5])
    
    with col_in:
        d_code = st.text_input("점검 코드", placeholder="예: 32-C-021")
        
        auto_msg = DEFECT_DB.get(d_code, "")
        if auto_msg: st.info(f"매칭: {auto_msg}")
            
        d_loc = st.text_input("위치", placeholder="예: 1층")
        d_desc = st.text_area("내용", value=auto_msg, height=100)
        
        if st.button("지적사항 저장"):
            if d_desc:
                st.session_state.defects_list.append(
                    {"코드": d_code, "위치": d_loc, "내용": d_desc}
                )
                st.success("저장됨")
    
    with col_list:
        if st.session_state.defects_list:
            st.dataframe(pd.DataFrame(st.session_state.defects_list), hide_index=True)
            if st.button("리스트 비우기"):
                st.session_state.defects_list = []
                st.rerun()
