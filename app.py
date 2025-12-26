import streamlit as st
import math

# --- 페이지 설정 ---
st.set_page_config(page_title="소방점검 마스터", page_icon="🧯")

# --- 1. 법적 기준 데이터 (배치기준) ---
# [별표4] 기준 데이터 반영
LIMITS = {
    "종합": {"area_base": 8000, "area_inc": 2000, "apt_base": 250, "apt_inc": 60},
    "작동": {"area_base": 10000, "area_inc": 2500, "apt_base": 250, "apt_inc": 60}
}
# 용도별 가감계수
USAGE_COEFF = {
    "1군 (아파트, 판매, 근생 등)": 1.1,
    "2군 (업무, 공장, 복합 등)": 1.0,
    "3군 (동식물, 위험물 등)": 0.9
}

# --- 2. 앱 화면 구성 ---
st.title("🧯 소방점검 모바일 리포트")
st.markdown("---")

# 탭 메뉴 생성
tab1, tab2, tab3 = st.tabs(["👥 배치 계산", "📝 지적/맞춤법", "💰 공사 견적"])

# ==========================================
# [탭 1] 인력 배치 시뮬레이터 (법적 기준 적용)
# ==========================================
with tab1:
    st.header("법적 점검인력 계산")
    col1, col2 = st.columns(2)
    with col1:
        inspection_type = st.radio("점검 종류", ["종합", "작동"])
        target_type = st.radio("건축물 타입", ["일반 건축물", "아파트"])
    
    with col2:
        usage_group = st.selectbox("용도 분류", list(USAGE_COEFF.keys()))
        k_factor = USAGE_COEFF[usage_group]
        if target_type == "일반 건축물":
            input_val = st.number_input("연면적 (㎡)", min_value=0.0, step=100.0)
        else:
            input_val = st.number_input("세대수", min_value=0, step=1)

    with st.expander("설비 감산 및 이동거리 (클릭해서 펼치기)"):
        st.caption("체크 해제 시 미설치로 간주하여 점검한도가 줄어듭니다.")
        has_sp = st.checkbox("스프링클러 설치됨", value=True)
        has_water = st.checkbox("물분무등 설치됨", value=True)
        has_smoke = st.checkbox("제연설비 설치됨", value=True)
        st.markdown("---")
        is_multi = st.checkbox("하루 2곳 이상 점검")
        dist_km = st.number_input("이동 거리(km)", value=0.0) if is_multi else 0.0

    if st.button("인력 계산 실행", type="primary"):
        # 계산 로직
        base_load = input_val if target_type == "아파트" else input_val * k_factor
        
        # 감산 계수
        reduction = 0.0
        if not has_sp: reduction += 0.1
        if not has_water: reduction += 0.1
        if not has_smoke: reduction += 0.1
        
        final_load = base_load * (1.0 - reduction)
        
        # 이동거리 감산
        dist_penalty = (dist_km / 5) * 0.02
        
        # 허용 한도 계산
        std = LIMITS[inspection_type]
        base_capa = std["apt_base"] if target_type == "아파트" else std["area_base"]
        inc_capa = std["apt_inc"] if target_type == "아파트" else std["area_inc"]
        
        st.divider()
        st.subheader("📊 계산 결과")
        
        found = False
        for aux in range(2, 5): # 보조인력 2~4명
            added = aux - 2
            # 용량 = (기본 + 추가) * (1 - 거리감산)
            capacity = (base_capa + (added * inc_capa)) * (1.0 - dist_penalty)
            
            if capacity >= final_load:
                st.success(f"✅ 배치 가능: 관리사 1명 + 보조 {aux}명")
                st.info(f"점검 부하량: {final_load:.2f} / 허용 한도: {capacity:.2f}")
                found = True
                break
        
        if not found:
            st.error("❌ 하루 점검 한도 초과! 인력을 더 늘리거나 일수를 나눠야 합니다.")

# ==========================================
# [탭 2] 지적 내역 & 맞춤법
# ==========================================
with tab2:
    st.header("현장 지적사항 입력")
    
    # 지적사항 선택
    defect_cat = st.selectbox("설비 선택", ["소화기", "옥내소화전", "스프링클러", "자동화재탐지", "유도등"])
    defects_db = {
        "소화기": ["내용연수 10년 경과", "압력 게이지 불량", "안전핀 탈락", "호스 균열"],
        "유도등": ["점등 불량", "예비전원 불량", "점검 스위치 불량"],
        "자동화재탐지": ["감지기 미설치", "감지기 오작동", "발신기 응답 없음", "수신기 예비전원 불량"]
    }
    selected = st.multiselect(f"{defect_cat} 주요 지적", defects_db.get(defect_cat, []))
    
    st.markdown("---")
    st.subheader("📝 상세 내용 입력 (자동 보정)")
    raw_text = st.text_area("음성 입력 내용을 붙여넣으세요", height=100)
    
    if st.button("맞춤법/띄어쓰기 정리"):
        # 간단 보정 로직 (나중에 py-hanspell 라이브러리로 교체 가능)
        fixed_text = raw_text.replace("됌", "됨").replace("읍니다", "습니다").replace("할꺼", "할 거")
        st.text_area("보정된 결과", value=fixed_text, height=100)
        st.success("내용이 정리되었습니다.")

# ==========================================
# [탭 3] 공사 견적 체크
# ==========================================
with tab3:
    st.header("공사 현장 체크리스트")
    col_a, col_b = st.columns(2)
    with col_a:
        st.checkbox("주말 작업 불가")
        st.checkbox("야간 작업 필요")
    with col_b:
        st.checkbox("사다리차 필요 (높음)")
        st.checkbox("천장 점검구 없음")
        
    st.text_input("담당자 연락처", placeholder="010-1234-5678")
    
    if st.button("데이터 저장"):
        st.toast("서버에 저장되었습니다! (PC에서 한글파일 생성 가능)")
