import streamlit as st
import pandas as pd
from datetime import date
import time

# --- 페이지 설정 (레이아웃 넓게) ---
st.set_page_config(page_title="소방점검 마스터 Pro", page_icon="🔥", layout="wide")

# ==========================================
# [0] 기초 데이터 및 함수
# ==========================================

# 1. 법적 기준
LIMITS = {
    "종합": {"area_base": 8000, "area_inc": 2000, "apt_base": 250, "apt_inc": 60},
    "작동": {"area_base": 10000, "area_inc": 2500, "apt_base": 250, "apt_inc": 60}
}

# 2. 용도 리스트
USAGE_OPTIONS = {
    "1류": ["[1류] 복합건축물", "[1류] 근생(5천㎡↑)", "[1류] 판매", "[1류] 의료/숙박", "[1류] 노유자"],
    "2류": ["[2류] 아파트", "[2류] 업무", "[2류] 공장", "[2류] 주차장", "[2류] 교육연구"],
    "3류": ["[3류] 동식물/교정/묘지"],
    "4류": ["[4류] 기타"],
    "지하구": ["[특수] 지하구"]
}

def get_k_factor(text):
    if "[1류]" in text: return 1.1
    if "[2류]" in text: return 1.0
    if "[3류]" in text: return 0.9
    if "[특수]" in text: return 2.0
    return 1.0

# 3. 지적항목 DB
DEFECT_DB = {
    "1-A-003": "소화기 미비치로 비치요함 (보행거리)",
    "1-A-007": "소화기 충압불량으로 교체요함",
    "32-C-021": "유도등 상시 점등 불량 (3선식 포함)",
    "32-C-022": "유도등 시각장애(적재물) 발생",
    "32-C-023": "유도등 예비전원 불량",
    "P-001": "소화전 펌프 기동 불량 (압력스위치 확인)",
    "D-001": "감지기 선로 단선 (발신기 LED 미점등)"
}

# --- 세션 초기화 (저장소 생성) ---
if 'saved_estimates' not in st.session_state:
    st.session_state.saved_estimates = {} # 견적서 보관함
if 'saved_reports' not in st.session_state:
    st.session_state.saved_reports = {} # 지적내역서 보관함

# 현재 작업 중인 임시 데이터
if 'est_items' not in st.session_state: st.session_state.est_items = []
if 'defect_items' not in st.session_state: st.session_state.defect_items = []
if 'est_info' not in st.session_state: 
    st.session_state.est_info = {"target": "", "person": "", "tel": "", "note": ""}

# ==========================================
# [사이드바] 문서 보관함 & 불러오기
# ==========================================
with st.sidebar:
    st.title("🗂️ 문서 보관함")
    st.markdown("---")
    
    # 1. 견적서 목록
    st.subheader("💰 저장된 견적서")
    if st.session_state.saved_estimates:
        est_keys = list(st.session_state.saved_estimates.keys())
        selected_est = st.selectbox("견적서 선택", ["(선택하세요)"] + est_keys)
        
        if selected_est != "(선택하세요)":
            if st.button("📂 견적 불러오기"):
                data = st.session_state.saved_estimates[selected_est]
                st.session_state.est_info = data['info']
                st.session_state.est_items = data['items']
                st.success(f"'{selected_est}' 불러옴!")
                time.sleep(0.5)
                st.rerun()
            
            if st.button("🗑️ 견적 삭제"):
                del st.session_state.saved_estimates[selected_est]
                st.rerun()
    else:
        st.caption("저장된 견적서가 없습니다.")

    st.markdown("---")

    # 2. 지적내역서 목록
    st.subheader("📝 저장된 지적서")
    if st.session_state.saved_reports:
        rep_keys = list(st.session_state.saved_reports.keys())
        selected_rep = st.selectbox("지적서 선택", ["(선택하세요)"] + rep_keys)
        
        if selected_rep != "(선택하세요)":
            if st.button("📂 지적서 불러오기"):
                st.session_state.defect_items = st.session_state.saved_reports[selected_rep]
                st.success(f"'{selected_rep}' 불러옴!")
                time.sleep(0.5)
                st.rerun()
            
            if st.button("🗑️ 지적서 삭제"):
                del st.session_state.saved_reports[selected_rep]
                st.rerun()
    else:
        st.caption("저장된 지적서가 없습니다.")

# ==========================================
# [메인] 타이틀
# ==========================================
st.title("🔥 소방점검 마스터 Pro")
st.caption("배치신고 | 견적관리(저장/출력) | 지적내역서")
st.divider()

tab1, tab2, tab3 = st.tabs(["🧮 1. 배치 확인", "🔨 2. 공사 견적", "📝 3. 지적 관리"])

# ==========================================
# [탭 1] 배치 확인 (기존 기능 유지)
# ==========================================
with tab1:
    col_1, col_2 = st.columns(2)
    with col_1:
        st.subheader("🏗️ 대상물 정보")
        target = st.text_input("대상명 (배치용)", placeholder="예: 갤럭시타워")
        usage_cat = st.selectbox("용도 분류", [x for v in USAGE_OPTIONS.values() for x in v])
        k = get_k_factor(usage_cat)
        
        c1, c2 = st.columns(2)
        area = c1.number_input("연면적 (㎡)", value=0.0, step=100.0)
        apt = c2.number_input("세대수", value=0)
        dist = st.number_input("거리 (km)", value=0.0)
        
        chk_sp = st.checkbox("SP설비", True)
        chk_sm = st.checkbox("제연", True)
        chk_wa = st.checkbox("물분무", True)

    with col_2:
        st.subheader("📊 결과 분석")
        insp_type = st.radio("점검 구분", ["종합", "작동"], horizontal=True)
        if st.button("계산 실행"):
            load = (area * k) + apt # 단순화된 계산식
            
            # 감산
            pen = 0.0
            if not chk_sp: pen += 0.1
            if not chk_sm: pen += 0.1
            if not chk_wa: pen += 0.1
            pen += (dist/5)*0.02
            
            std = LIMITS[insp_type]
            
            best_sub = -1
            for sub in range(6):
                capa = (std["area_base"] + sub*std["area_inc"]) * (1.0 - pen) # 면적기준 근사치
                if capa >= load:
                    best_sub = sub
                    break
            
            if best_sub != -1:
                st.success(f"✅ 관리사 1명 + 보조 {best_sub}명 가능")
                st.info(f"부하량: {load:.0f} / 한도: {capa:.0f}")
            else:
                st.error("❌ 1일 점검 불가")

# ==========================================
# [탭 2] 공사 견적 (저장/출력 기능 강화)
# ==========================================
with tab2:
    st.header("🔨 공사 견적서 작성")
    
    # 1. 정보 입력
    with st.expander("📝 고객 및 현장 정보 입력", expanded=True):
        c_i1, c_i2 = st.columns(2)
        t_name = c_i1.text_input("공사 대상명", value=st.session_state.est_info['target'])
        t_person = c_i2.text_input("담당자/연락처", value=st.session_state.est_info['person'])
        t_note = st.text_area("특이사항 (천고, 공사조건 등)", value=st.session_state.est_info['note'])
        
        # 입력값 세션에 업데이트
        st.session_state.est_info.update({"target": t_name, "person": t_person, "note": t_note})

    # 2. 항목 추가
    st.divider()
    c_add1, c_add2, c_add3, c_add4, c_add5 = st.columns([2,1,1,1,1])
    in_item = c_add1.text_input("품명", key="est_item")
    in_spec = c_add2.text_input("규격", key="est_spec")
    in_unit = c_add3.selectbox("단위", ["식", "EA", "개소", "m", "set"], key="est_unit")
    in_qty = c_add4.number_input("수량", min_value=1.0, step=1.0, key="est_qty")
    in_price = c_add5.number_input("단가(합계)", step=1000, key="est_price")
    
    if st.button("➕ 항목 추가"):
        if in_item:
            st.session_state.est_items.append({
                "품명": in_item, "규격": in_spec, "단위": in_unit,
                "수량": in_qty, "단가": in_price, "금액": in_qty * in_price
            })
            st.rerun()

    # 3. 리스트 및 저장/출력
    st.divider()
    if st.session_state.est_items:
        df = pd.DataFrame(st.session_state.est_items)
        st.dataframe(df, hide_index=True, use_container_width=True)
        total_amt = df['금액'].sum()
        st.markdown(f"### 💰 총 견적금액: {int(total_amt):,} 원")
        
        col_act1, col_act2, col_act3 = st.columns(3)
        
        # [기능 1] 저장하기
        with col_act1:
            save_name = st.text_input("저장할 이름", value=f"{t_name} 견적서")
            if st.button("💾 보관함에 저장"):
                st.session_state.saved_estimates[save_name] = {
                    "info": st.session_state.est_info,
                    "items": st.session_state.est_items
                }
                st.success(f"'{save_name}' 저장 완료! (왼쪽 사이드바 확인)")
        
        # [기능 2] 초기화
        with col_act2:
            if st.button("🔄 새로 작성"):
                st.session_state.est_items = []
                st.session_state.est_info = {"target": "", "person": "", "tel": "", "note": ""}
                st.rerun()

        # [기능 3] 인쇄 화면 (HTML 생성)
        st.write("---")
        st.subheader("🖨️ 인쇄/출력 미리보기")
        
        # HTML 테이블 생성
        html_rows = ""
        for idx, row in df.iterrows():
            html_rows += f"""
            <tr>
                <td style='border:1px solid #ddd; padding:8px;'>{idx+1}</td>
                <td style='border:1px solid #ddd; padding:8px;'>{row['품명']}</td>
                <td style='border:1px solid #ddd; padding:8px;'>{row['규격']}</td>
                <td style='border:1px solid #ddd; padding:8px; text-align:center;'>{row['단위']}</td>
                <td style='border:1px solid #ddd; padding:8px; text-align:center;'>{row['수량']}</td>
                <td style='border:1px solid #ddd; padding:8px; text-align:right;'>{int(row['단가']):,}</td>
                <td style='border:1px solid #ddd; padding:8px; text-align:right;'>{int(row['금액']):,}</td>
            </tr>
            """
            
        print_html = f"""
        <div style="padding:20px; border:1px solid #333; background:white; color:black;">
            <h1 style="text-align:center;">견  적  서</h1>
            <table style="width:100%; margin-bottom:20px;">
                <tr>
                    <td><b>공사명:</b> {t_name}</td>
                    <td style="text-align:right;"><b>날짜:</b> {date.today()}</td>
                </tr>
                <tr>
                    <td><b>담당자:</b> {t_person}</td>
                    <td style="text-align:right;"><b>합계:</b> {int(total_amt):,} 원 (VAT별도)</td>
                </tr>
            </table>
            <div style="margin-bottom:10px; font-size:12px; color:#555;">
                * 참고사항: {t_note}
            </div>
            <table style="width:100%; border-collapse:collapse; text-align:left;">
                <tr style="background-color:#f2f2f2;">
                    <th style="border:1px solid #333; padding:8px;">No</th>
                    <th style="border:1px solid #333; padding:8px;">품명</th>
                    <th style="border:1px solid #333; padding:8px;">규격</th>
                    <th style="border:1px solid #333; padding:8px;">단위</th>
                    <th style="border:1px solid #333; padding:8px;">수량</th>
                    <th style="border:1px solid #333; padding:8px;">단가</th>
                    <th style="border:1px solid #333; padding:8px;">금액</th>
                </tr>
                {html_rows}
            </table>
            <br>
            <p style="text-align:center;">위와 같이 견적합니다.</p>
            <p style="text-align:center; font-weight:bold;">가람방재 (대표 서흥원)</p>
        </div>
        """
        
        # HTML 렌더링
        with st.expander("📄 인쇄용 뷰 열기 (클릭)", expanded=False):
            st.markdown(print_html, unsafe_allow_html=True)
            st.info("👆 위 내용을 마우스로 드래그해서 복사하거나, 브라우저 인쇄(Ctrl+P) 기능을 사용하세요.")


# ==========================================
# [탭 3] 지적 관리 (저장/출력 기능 강화)
# ==========================================
with tab3:
    st.header("📝 지적내역서 작성")

    c_d1, c_d2 = st.columns([1, 2])
    with c_d1:
        d_code = st.text_input("코드", placeholder="예: 32-C-021")
        if d_code in DEFECT_DB: st.caption(f"자동: {DEFECT_DB[d_code]}")
        d_loc = st.text_input("위치", placeholder="1층 복도")
        d_txt = st.text_area("내용", value=DEFECT_DB.get(d_code, ""))
        
        if st.button("⬇️ 지적 추가"):
            st.session_state.defect_items.append({"코드": d_code, "위치": d_loc, "내용": d_txt})
            st.rerun()

    with c_d2:
        if st.session_state.defect_items:
            df_d = pd.DataFrame(st.session_state.defect_items)
            st.dataframe(df_d, hide_index=True, use_container_width=True)
            
            # 저장 및 출력
            st.write("---")
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                rep_name = st.text_input("지적서 이름", value=f"{date.today()} 지적사항")
                if st.button("💾 지적서 저장"):
                    st.session_state.saved_reports[rep_name] = st.session_state.defect_items
                    st.success("보관함 저장 완료!")

            with col_s2:
                if st.button("🗑️ 리스트 비우기"):
                    st.session_state.defect_items = []
                    st.rerun()

            # 인쇄 뷰
            with st.expander("📄 인쇄용 지적내역서 보기"):
                defect_html = f"""
                <div style="padding:20px; background:white; color:black; border:1px solid #333;">
                    <h2 style="text-align:center;">소방시설 지적내역서</h2>
                    <table style="width:100%; border-collapse:collapse;">
                        <tr style="background:#eee;">
                            <th style="border:1px solid #333; padding:5px;">코드</th>
                            <th style="border:1px solid #333; padding:5px;">위치</th>
                            <th style="border:1px solid #333; padding:5px;">지적 내용</th>
                        </tr>
                """
                for row in st.session_state.defect_items:
                    defect_html += f"""
                        <tr>
                            <td style="border:1px solid #333; padding:5px;">{row['코드']}</td>
                            <td style="border:1px solid #333; padding:5px;">{row['위치']}</td>
                            <td style="border:1px solid #333; padding:5px;">{row['내용']}</td>
                        </tr>
                    """
                defect_html += "</table></div>"
                st.markdown(defect_html, unsafe_allow_html=True)
