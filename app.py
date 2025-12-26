import streamlit as st
import pandas as pd
from datetime import date

# --- 페이지 설정 ---
st.set_page_config(page_title="소방점검 마스터", page_icon="👨‍🚒", layout="wide")

# --- 1. 법적 기준 데이터 ---
LIMITS = {
    "종합": {"area_base": 8000, "area_inc": 2000, "apt_base": 250, "apt_inc": 60},
    "작동": {"area_base": 10000, "area_inc": 2500, "apt_base": 250, "apt_inc": 60}
}

# [갤럭시타워 배치확인서 반영] 1류~5류
USAGE_COEFF = {
    "1류 (계수 1.1)": 1.1,
    "2류 (계수 1.0)": 1.0,
    "3류 (계수 0.9)": 0.9,
    "4류 (계수 0.8)": 0.8,
    "5류 (계수 0.7)": 0.7,
    "지하구 (계수 2.0)": 2.0
}

GRADE_INFO = {
    "1류 (계수 1.1)": "근생, 위락, 문화집회, 의료, 판매, 복합건축물 등",
    "2류 (계수 1.0)": "아파트, 업무, 공장, 주차장 등",
    "3류 (계수 0.9)": "동식물, 위험물, 교정, 묘지 등",
    "4류 (계수 0.8)": "기타",
    "5류 (계수 0.7)": "기타",
    "지하구 (계수 2.0)": "지하구"
}

st.title("👨‍🚒 소방점검 통합 시스템")
st.markdown("배치확인부터 지적사항 관리까지 한 번에 처리합니다.")
st.divider()

# 탭 메뉴 (이름 심플하게 변경)
tab1, tab2 = st.tabs(["🧮 1. 배치 확인", "📝 2. 지적 관리"])

# ==========================================
# [탭 1] 배치 확인 (기존 기능 유지)
# ==========================================
with tab1:
    with st.expander("📂 [대상처 엑셀] 불러오기", expanded=False):
        uploaded_file = st.file_uploader("엑셀 파일 업로드", type=['xlsx', 'xls'])
        df = None
        if uploaded_file:
            try:
                df = pd.read_excel(uploaded_file)
                st.success(f"{len(df)}개 대상처 로딩 완료")
            except:
                st.error("엑셀 오류")

    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("🏗️ 대상물 정보")
        chk_date = st.date_input("점검 일자", date.today())

        # 대상처 선택
        selected_row = None
        if df is not None:
            target_list = df.iloc[:, 0].astype(str).tolist()
            target_name = st.selectbox("점검 대상", target_list)
            selected_row = df[df.iloc[:, 0] == target_name].iloc[0]
        else:
            target_name = st.text_input("대상명", placeholder="예: 갤럭시타워")

        inspection_type = st.radio("점검 구분", ["종합점검", "작동점검"], horizontal=True)

        with st.container(border=True):
            grade_key = st.selectbox("용도 구분", list(USAGE_COEFF.keys()), index=0)
            k_factor = USAGE_COEFF[grade_key]

            c1, c2 = st.columns(2)
            # 엑셀 자동 매칭
            def_area = 0.0
            def_apt = 0
            def_dist = 0.0
            if selected_row is not None:
                for col in df.columns:
                    c_str = str(col)
                    if "연면적" in c_str or "면적" in c_str: 
                        try: def_area = float(selected_row[col])
                        except: pass
                    if "세대" in c_str:
                        try: def_apt = int(selected_row[col])
                        except: pass
                    if "거리" in c_str:
                        try: def_dist = float(selected_row[col])
                        except: pass

            with c1:
                input_area = st.number_input("연면적 (㎡)", value=def_area, step=100.0, format="%.2f")
            with c2:
                input_apt = st.number_input("아파트 세대수", value=def_apt, step=10)
            
            dist_km = st.number_input("이동 거리 (km)", value=def_dist, step=1.0)

            st.markdown("---")
            st.write("**설비 감산 (미설치 시 체크 해제)**")
            # 앱 편의상: 체크=설치됨(정상)
            chk1, chk2, chk3 = st.columns(3)
            has_sp = chk1.checkbox("스프링클러", value=False)
            has_smoke = chk2.checkbox("제연설비", value=False)
            has_water = chk3.checkbox("물분무등", value=False)

    with right_col:
        st.subheader("📊 배치 결과")
        if st.button("계산 실행", type="primary", use_container_width=True):
            load_area = input_area * k_factor
            load_apt = input_apt 
            
            reduction_rate = 0.0
            if not has_sp: reduction_rate += 0.1
            if not has_smoke: reduction_rate += 0.1
            if not has_water: reduction_rate += 0.1
            
            dist_penalty = (dist_km / 5) * 0.02
            
            std_key = "종합" if "종합" in inspection_type else "작동"
            std = LIMITS[std_key]
            
            st.markdown(f"**{target_name}** ({chk_date})")
            st.info(f"부하량: {input_area:,.2f}㎡ / {input_apt}세대")
            
            found = False
            for sub in range(0, 6):
                capa_area = std["area_base"] + (sub * std["area_inc"])
                capa_apt = std["apt_base"] + (sub * std["apt_inc"])
                
                real_capa_area = capa_area * (1.0 - reduction_rate) * (1.0 - dist_penalty)
                real_capa_apt = capa_apt * (1.0 - reduction_rate) * (1.0 - dist_penalty)
                
                usage_ratio = 0.0
                if real_capa_area > 0: usage_ratio += (load_area / real_capa_area)
                if real_capa_apt > 0: usage_ratio += (load_apt / real_capa_apt)
                
                if usage_ratio <= 1.0:
                    st.success(f"✅ **[관리사 + 보조 {sub}명]** 가능")
                    st.progress(usage_ratio, text=f"부하율: {usage_ratio*100:.1f}%")
                    found = True
                    break
            
            if not found:
                st.error("❌ 인력 부족 (2일 점검 권장)")

# ==========================================
# [탭 2] 지적 관리 (심플하게 변경됨)
# ==========================================
with tab2:
    st.header("📝 지적사항 입력 (자동완성)")
    st.caption("점검 코드를 넣으면 표준 문구가 자동으로 완성됩니다.")
    
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        defect_code = st.text_input("점검 코드", placeholder="예: 32-C-021")
        defect_loc = st.text_input("세부 위치", placeholder="예: 1층 복도")
        defect_cat = st.selectbox("설비 분류", ["소화설비", "경보설비", "피난설비", "유도등", "기타"])

    with col_result:
        # 지적사항 표준 DB (계속 추가 가능)
        desc_db = {
            "32-C-002": "피난기구의 부착 위치 및 부착 방법 부적정",
            "32-C-003": "피난기구(지지대 포함) 변형/손상/부식",
            "32-C-004": "피난기구 위치표시/사용방법 표지 미부착",
            "32-C-005": "피난유도선 변형/손상 또는 점등 불량",
            "32-C-021": "유도등 상시 점등 불량 (3선식 포함)",
            "32-C-022": "유도등 시각장애 발생 (가려짐 등)",
            "32-C-023": "유도등 예비전원 불량 (배터리 방전)",
            "1-A-003": "소화기 미비치 (보행거리 초과)",
            "1-A-007": "소화기 충압 불량 (게이지 불량)"
        }
        
        # 코드 매칭 시 자동 완성, 아니면 빈칸
        auto_text = desc_db.get(defect_code, "")
        
        # 여기서 바로 수정 가능
        final_text = st.text_area("지적 내용 (자동 입력됨)", value=auto_text, height=120)
        
        if st.button("저장하기", type="primary"):
            if final_text:
                save_msg = f"📌 [{defect_code}] {defect_cat}\n- 위치: {defect_loc}\n- 내용: {final_text}"
                st.success("리스트에 저장되었습니다!")
                st.code(save_msg) # 나중에 엑셀 저장 기능 붙일 곳
            else:
                st.warning("내용을 입력해주세요.")
