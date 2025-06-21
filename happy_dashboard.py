import streamlit as st
import pandas as pd
from datetime import date, datetime
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import openai

# 🔐 환경변수 로딩
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Supabase 연결
supabase: Client = create_client(supabase_url, supabase_key)

# OpenAI 연결
client = openai.OpenAI(api_key=openai_api_key)

# 햅삐 생일
baby_birthday = pd.to_datetime("2025-07-10")

# 로그인 체크
if "user" not in st.session_state:
    st.set_page_config(page_title="햅삐 대시보드 로그인", layout="wide")
    st.title("🍼 햅삐 성장 대시보드 - 로그인")

    with st.form("login_form"):
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")
        login_submit = st.form_submit_button("로그인")

        if login_submit:
            try:
                auth_response = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                st.session_state.user = auth_response.user
                st.success("로그인 성공!")
                st.rerun()
            except Exception as e:
                st.error("로그인 실패! 이메일 또는 비밀번호를 확인하세요.")
    st.stop()

# 로그인 이후 대시보드
st.set_page_config(page_title="햅삐 성장 대시보드", layout="wide")
st.title("🍼 햅삐 성장 대시보드")

# 생일 정보 상단 표시
st.info(f"👶 햅삐 탄생일: {baby_birthday.date()} (기준일로부터 {(date.today() - baby_birthday.date()).days}일 지남)")

# 오늘의 기록 입력
with st.form("entry_form"):
    st.subheader("📋 오늘의 기록 입력")
    col1, col2, col3 = st.columns(3)
    with col1:
        entry_date = st.date_input("날짜", value=date.today())
        height_cm = st.number_input("키 (cm)", min_value=30.0, max_value=100.0, step=0.1)
        weight_kg = st.number_input("몸무게 (kg)", min_value=2.0, max_value=20.0, step=0.1)
    with col2:
        sleep_hours = st.number_input("수면 시간", min_value=0.0, max_value=24.0, step=0.5)
        formula_ml = st.number_input("분유량 (ml)", min_value=0, max_value=2000, step=10)
        diaper_changes = st.number_input("기저귀 교체 횟수", min_value=0, max_value=20, step=1)
    with col3:
        hospital_visit = st.text_input("병원 방문 내용")

    gen_diary = st.checkbox("GPT로 일기 자동 생성")
    note_input = st.text_area("하루 요약 메모 (직접 입력 시 GPT 미사용)", "")

    submitted = st.form_submit_button("✅ 기록 저장하기")

    if submitted:
        new_entry = {
            "date": str(entry_date),
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "sleep_hours": sleep_hours,
            "formula_ml": formula_ml,
            "diaper_changes": diaper_changes,
            "hospital_visit": hospital_visit,
            "note": note_input
        }

        if gen_diary or not note_input:
            age_days = (entry_date - baby_birthday.date()).days
            age_weeks = round(age_days / 7, 1)

            # 최근 7일 평균
            recent = df[df["date"] >= pd.to_datetime(entry_date) - pd.Timedelta(days=7)]
            avg_height = recent["height_cm"].mean()
            avg_weight = recent["weight_kg"].mean()
            avg_sleep = recent["sleep_hours"].mean()
            avg_formula = recent["formula_ml"].mean()

            # 대한민국 남아 생후 일수별 평균 (예시: 간략화된 데이터)
            korea_avg = {
                30: {"height": 54.7, "weight": 4.5},
                60: {"height": 58.4, "weight": 5.6},
                90: {"height": 61.4, "weight": 6.4},
                120: {"height": 63.9, "weight": 7.0},
                150: {"height": 65.9, "weight": 7.5},
                180: {"height": 67.6, "weight": 7.9},
                210: {"height": 69.2, "weight": 8.3},
                240: {"height": 70.6, "weight": 8.6}
            }
            nearest_day = min(korea_avg.keys(), key=lambda x: abs(x - age_days))
            avg_korea_height = korea_avg[nearest_day]["height"]
            avg_korea_weight = korea_avg[nearest_day]["weight"]

            prompt = f"""
            오늘은 생후 {age_days}일차 ({age_weeks}주차)인 햅삐의 성장 기록입니다.

            오늘의 측정 값:
- 키: {height_cm}cm
- 몸무게: {weight_kg}kg
- 수면 시간: {sleep_hours}시간
- 분유 섭취량: {formula_ml}ml

            최근 7일 평균 (햅삐 개인 기준):
- 키: {avg_height:.1f}cm
- 몸무게: {avg_weight:.1f}kg
- 수면 시간: {avg_sleep:.1f}시간
- 분유 섭취량: {avg_formula:.0f}ml

            대한민국 남아 평균 (생후 {nearest_day}일 기준 예상값):
- 키: {avg_korea_height:.1f}cm
- 몸무게: {avg_korea_weight:.1f}kg

            위 데이터를 기반으로,
1. 오늘 햅삐의 성장 기록이 이전 흐름과 비교해 어떠한지
2. 대한민국 평균 성장 기준과 비교하여 잘 자라고 있는지
를 종합적으로 평가해줘.

            결과는 2~3문장 이내로 자연스럽고 따뜻한 피드백 형식으로 작성해줘.
(예: “햅삐는 평균보다 약간 큰 편으로, 안정적인 수면과 섭취량을 유지하고 있어요.”)
            """

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200
            )
            new_entry["note"] = response.choices[0].message.content.strip()

        supabase.table("baby_growth").insert(new_entry).execute()
        st.success("기록이 저장되었습니다!")

# 데이터 불러오기
res = supabase.table("baby_growth").select("*").order("date").execute()
df = pd.DataFrame(res.data)

if not df.empty:
    st.subheader("📈 성장 차트")
    col1, col2 = st.columns(2)
    with col1:
        st.line_chart(df.set_index("date")["height_cm"])
    with col2:
        st.line_chart(df.set_index("date")["weight_kg"])

    st.subheader("🛌 수면 & 분유 추이")
    col3, col4 = st.columns(2)
    with col3:
        st.bar_chart(df.set_index("date")["sleep_hours"])
    with col4:
        st.bar_chart(df.set_index("date")["formula_ml"])

    st.subheader("🧷 기저귀 교체 추이")
    st.bar_chart(df.set_index("date")["diaper_changes"])

    st.subheader("🏥 병원 방문 기록")
    hospital_df = df[df["hospital_visit"].str.strip() != ""]
    if hospital_df.empty:
        st.info("기록된 병원 방문이 없습니다.")
    else:
        st.dataframe(hospital_df[["date", "hospital_visit"]].set_index("date"))

    st.subheader("📝 하루 요약 메모")
    st.dataframe(df[["date", "note"]].set_index("date"))

    # ✏️ 수정 및 삭제 기능
    st.subheader("✏️ 기록 수정 및 삭제")
    editable_df = st.data_editor(
        df[["id", "date", "height_cm", "weight_kg", "sleep_hours", "formula_ml", "diaper_changes", "hospital_visit", "note"]],
        use_container_width=True,
        num_rows="dynamic",
        disabled=["id", "date"]
    )

    if st.button("📝 수정사항 저장"):
        original_ids = set(df["id"])
        updated_ids = set(editable_df["id"])

        # 수정 처리
        for _, row in editable_df.iterrows():
            supabase.table("baby_growth").update({
                "height_cm": row["height_cm"],
                "weight_kg": row["weight_kg"],
                "sleep_hours": row["sleep_hours"],
                "formula_ml": row["formula_ml"],
                "diaper_changes": row["diaper_changes"],
                "hospital_visit": row["hospital_visit"],
                "note": row["note"]
            }).eq("id", row["id"]).execute()

        # 삭제 처리
        deleted_ids = original_ids - updated_ids
        for del_id in deleted_ids:
            supabase.table("baby_growth").delete().eq("id", del_id).execute()

        st.success("수정 및 삭제가 완료되었습니다!")
        st.rerun()

    # 📥 기록 다운로드
    st.subheader("📥 기록 다운로드")
    csv_data = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📄 CSV로 다운로드",
        data=csv_data,
        file_name="happy_dashboard_data.csv",
        mime="text/csv"
    )

    # 🗓️ 주간 요약 자동 생성 (사용자 요청 시 실행)
    st.subheader("🗓️ 주간 요약 리포트 (GPT 생성)")

    if st.button("📝 이번 주 요약 리포트 생성하기"):
        df["date"] = pd.to_datetime(df["date"])
        last_week = df[df["date"] >= pd.Timestamp.today() - pd.Timedelta(days=7)]

        if last_week.empty:
            st.info("최근 7일간 기록이 부족합니다.")
        else:
            summary_prompt = f"""
            다음은 지난 7일간 아기 성장 기록입니다:\n
            {last_week[['date', 'height_cm', 'weight_kg', 'sleep_hours', 'formula_ml', 'diaper_changes', 'hospital_visit']].to_string(index=False)}\n
            이 데이터를 바탕으로 전체적인 경과와 인상적인 점을 중심으로 주간 요약 리포트를 작성해줘.
            분량은 3~5문장 정도로 자연스럽게, 부모에게 보고하는 느낌으로 써줘.
            """

            with st.spinner("GPT가 리포트를 작성 중입니다..."):
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": summary_prompt}],
                    temperature=0.7,
                    max_tokens=500
                )
                weekly_report = response.choices[0].message.content.strip()
                st.success("요약 완료!")
                st.markdown(f"📝 **주간 리포트:**\n\n{weekly_report}")
