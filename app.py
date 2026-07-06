# -*- coding: utf-8 -*-
"""서울시 폭염대응 시설 대시보드 — 무더위쉼터 + 그늘막 통합 (Streamlit + pandas)"""

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# 서울 중심 좌표 (더블클릭 시 원상복귀 기준점)
SEOUL_CENTER = {"latitude": 37.5665, "longitude": 126.9780, "zoom": 10.2}


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def render_map(points_df):
    """deck.gl 커스텀 지도. 더블클릭하면 서울 중심으로 초기화된다."""
    records = [
        {
            "position": [float(r["lon"]), float(r["lat"])],
            "color": _hex_to_rgb(r["color"]),
            "radius": float(r["size"]),
        }
        for _, r in points_df.iterrows()
    ]
    data_json = json.dumps(records)
    view_json = json.dumps(SEOUL_CENTER)
    html = f"""
    <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet"/>
    <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
    <script src="https://unpkg.com/deck.gl@8.9.36/dist.min.js"></script>
    <div id="deck-map" style="position:relative;width:100%;height:520px;border-radius:8px;overflow:hidden;"></div>
    <div style="font-size:12px;color:#888;margin-top:4px;">💡 지도를 더블클릭하면 서울 중심으로 원상복귀됩니다.</div>
    <script>
      const DATA = {data_json};
      const INITIAL_VIEW_STATE = Object.assign(
        {{pitch: 0, bearing: 0}}, {view_json});
      const scatter = new deck.ScatterplotLayer({{
        id: 'points',
        data: DATA,
        getPosition: d => d.position,
        getFillColor: d => d.color,
        getRadius: d => d.radius,
        radiusUnits: 'meters',
        radiusMinPixels: 3,
        radiusMaxPixels: 60,
        opacity: 0.75,
        stroked: true,
        getLineColor: [255, 255, 255],
        lineWidthMinPixels: 0.5,
      }});
      const deckgl = new deck.DeckGL({{
        container: 'deck-map',
        mapStyle: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
        initialViewState: INITIAL_VIEW_STATE,
        controller: {{doubleClickZoom: false}},
        layers: [scatter],
      }});
      // 더블클릭 → 서울 중심으로 부드럽게 원상복귀 (매번 동작)
      let _resetTick = 0;
      document.getElementById('deck-map').addEventListener('dblclick', (e) => {{
        e.preventDefault();
        e.stopPropagation();
        // 미세한 zoom 지터로 매 클릭마다 새로운 목표값을 만들어 전환을 강제
        _resetTick += 1;
        deckgl.setProps({{
          initialViewState: Object.assign({{}}, INITIAL_VIEW_STATE, {{
            zoom: INITIAL_VIEW_STATE.zoom + (_resetTick % 2) * 1e-6,
            transitionDuration: 700,
            transitionInterpolator: new deck.FlyToInterpolator(),
          }})
        }});
      }});
    </script>
    """
    components.html(html, height=560)


CSV_PATH = "서울시 무더위쉼터.csv"
SHADE_PATH = "폭염저감시설_그늘막_2026년.csv"

SHELTER = "무더위쉼터"
SHADE = "그늘막"

# ── 2025년 폭염으로 인한 온열질환 신고현황 연보 (질병관리청) 반영 ──
# 서울 광역 합계: 신고 378명 / 사망 3명  (표25. 지역별 진료결과별 신고현황)
# 자치구별 사망자수: 표4. 2025년 온열질환 추정 사망 신고사례에서 서울 사례 집계
#   → 중랑구·강동구·관악구 각 1명 (총 3명)
# ※ 자치구별 '신고수'는 연보에 광역(시도) 단위까지만 있어 미제공(서울 합계 378명만 존재)
SEOUL_HEAT_2025 = {"신고수": 378, "사망자수": 3}
SEOUL_GU_DEATHS_2025 = {"중랑구": 1, "강동구": 1, "관악구": 1}

# ── 폭염 심각도·강도 증가 추이 (질병관리청 연보 표2, 기상청) ──
HEAT_TREND_YEARS = list(range(2011, 2026))
HEAT_PATIENTS = [443, 984, 1189, 556, 1056, 2125, 1574, 4526,
                 1841, 1078, 1376, 1564, 2818, 3704, 4460]   # 연도별 온열질환자 수(명)
HEATWAVE_DAYS = [6.5, 14.0, 16.6, 6.6, 9.6, 22.0, 13.5, 31.0,
                 12.9, 7.7, 11.8, 10.6, 14.2, 30.1, 29.7]      # 연도별 전국 폭염일수(일)

st.set_page_config(page_title="서울시 폭염대응시설", page_icon="🌤️", layout="wide")


def _extract_gu(addr):
    """도로명주소 문자열에서 자치구(○○구) 추출."""
    if isinstance(addr, str):
        for token in addr.split():
            if token.endswith("구") and len(token) >= 2:
                return token
    return "기타"


@st.cache_data
def load_shelter(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="cp949")
    df.columns = [c.strip() for c in df.columns]
    for col in ["시설면적", "이용가능인원", "경도", "위도"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["자치구"] = df["도로명주소"].apply(_extract_gu)
    out = pd.DataFrame({
        "데이터종류": SHELTER,
        "명칭": df["쉼터명칭"],
        "자치구": df["자치구"],
        "세부유형": df["시설구분1"],
        "도로명주소": df["도로명주소"],
        "lat": df["위도"],
        "lon": df["경도"],
    })
    return out


@st.cache_data
def load_shade(path: str) -> pd.DataFrame:
    # 엑셀 원본을 정리해 저장한 CSV (헤더/좌표 정제 완료)
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df[df["연번"].notna()].copy()
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    out = pd.DataFrame({
        "데이터종류": SHADE,
        "명칭": df["설치장소명"],
        "자치구": df["시군구"].astype(str).str.strip(),
        "세부유형": df["종류"],
        "도로명주소": df["도로명주소"],
        "lat": df["위도"],
        "lon": df["경도"],
    })
    return out


shelter = load_shelter(CSV_PATH)
shade = load_shade(SHADE_PATH)
all_df = pd.concat([shelter, shade], ignore_index=True)

# ── 페이지 선택 (좌측 사이드바 탭) ─────────────────────────
PAGE1 = "🌤️ 서울시 폭염대응시설 현황"
PAGE2 = "🔥 폭염 정보 (점점 심각해지는 폭염)"

st.sidebar.title("📑 페이지")
page = st.sidebar.radio("페이지 선택", [PAGE1, PAGE2], label_visibility="collapsed")
st.sidebar.divider()


# ══════════════════════════════════════════════════════════
# 1페이지 · 서울시 폭염대응시설 현황 (메인)
# ══════════════════════════════════════════════════════════
if page == PAGE1:
    st.title(PAGE1)
    st.caption(
        f"무더위쉼터 {len(shelter):,}개 · 그늘막 {len(shade):,}개 · 합계 {len(all_df):,}개"
    )

    # ── 서비스 목적 ──
    st.info(
        "🎯 **서비스 목적**\n\n"
        "기후변화로 인해 폭염 발생 빈도와 강도가 증가하는 상황에서, 공공데이터를 활용하여 "
        "지역별 폭염 대응시설(무더위쉼터, 그늘막 등)의 위치와 정보를 한눈에 확인할 수 있는 "
        "서비스를 제공함으로써, 폭염으로부터 시민의 안전을 확보하고 신속한 대피를 지원하는 것을 목적으로 한다."
    )

    # ── 사이드바 필터 ──
    st.sidebar.header("🔎 필터")
    sel_kinds = st.sidebar.multiselect(
        "데이터종류", [SHELTER, SHADE], default=[SHELTER, SHADE])
    gu_list = sorted(g for g in all_df["자치구"].dropna().unique() if g != "기타")
    sel_gu = st.sidebar.multiselect("자치구", gu_list, default=[])
    keyword = st.sidebar.text_input("명칭 검색", "")

    # ── 필터 적용 ──
    fdf = all_df.copy()
    if sel_kinds:
        fdf = fdf[fdf["데이터종류"].isin(sel_kinds)]
    if sel_gu:
        fdf = fdf[fdf["자치구"].isin(sel_gu)]
    if keyword:
        fdf = fdf[fdf["명칭"].astype(str).str.contains(keyword, case=False, na=False)]

    # ── 요약 지표 ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 시설", f"{len(fdf):,}")
    c2.metric("무더위쉼터", f"{(fdf['데이터종류'] == SHELTER).sum():,}")
    c3.metric("그늘막", f"{(fdf['데이터종류'] == SHADE).sum():,}")
    c4.metric("자치구 수", f"{fdf['자치구'].nunique():,}")

    st.divider()

    # ── 자치구별 시설 수 비교 ──
    st.subheader("🏙️ 자치구별 시설 수 비교 (무더위쉼터 & 그늘막)")

    pivot = (
        fdf.pivot_table(index="자치구", columns="데이터종류",
                        values="명칭", aggfunc="count", fill_value=0)
        .drop(index="기타", errors="ignore")
    )
    for k in (SHELTER, SHADE):
        if k not in pivot.columns:
            pivot[k] = 0
    pivot = pivot[[c for c in (SHELTER, SHADE) if c in pivot.columns]]
    pivot["합계"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("합계", ascending=False)

    st.caption("두 시설이 모두 있는 자치구는 막대가 나란히 표시됩니다. (🟠 무더위쉼터 · 🟢 그늘막)")
    chart_df = pivot.drop(columns="합계")
    bar_colors = [{SHELTER: "#F4A6A0", SHADE: "#9BD4C7"}[c] for c in chart_df.columns]
    st.bar_chart(chart_df, color=bar_colors)

    if SHELTER in pivot.columns and SHADE in pivot.columns:
        both = pivot[(pivot[SHELTER] > 0) & (pivot[SHADE] > 0)]
        st.markdown(
            f"**무더위쉼터와 그늘막이 모두 있는 자치구: {len(both)}곳**  "
            f"(전체 {pivot.shape[0]}개 자치구 중)"
        )
        st.dataframe(
            both.rename_axis("자치구").reset_index(),
            width="stretch", hide_index=True,
        )

    st.divider()

    # ── 통합 지도 ──
    st.subheader("🗺️ 통합 위치 지도")
    st.caption(f"🟠 {SHELTER}   🟢 {SHADE}   🔴 온열질환 사망(자치구별)")

    geo = all_df.dropna(subset=["lat", "lon"])
    geo = geo[geo["lat"].between(37.0, 38.0) & geo["lon"].between(126.0, 128.0)]
    gu_center = geo.groupby("자치구")[["lat", "lon"]].mean()

    map_df = fdf.dropna(subset=["lat", "lon"]).copy()
    map_df = map_df[map_df["lat"].between(37.0, 38.0) & map_df["lon"].between(126.0, 128.0)]
    facility_pts = map_df[["lat", "lon"]].copy()
    facility_pts["color"] = map_df["데이터종류"].map({SHELTER: "#F4A6A0", SHADE: "#9BD4C7"})
    facility_pts["size"] = 30

    layers = [facility_pts]
    death_rows = []
    for gu, cnt in SEOUL_GU_DEATHS_2025.items():
        if gu in gu_center.index and (not sel_gu or gu in sel_gu):
            death_rows.append({
                "lat": gu_center.loc[gu, "lat"],
                "lon": gu_center.loc[gu, "lon"],
                "color": "#D7263D",
                "size": 250 * cnt,
            })
    if death_rows:
        layers.append(pd.DataFrame(death_rows))

    final_map = pd.concat(layers, ignore_index=True)
    if len(final_map):
        render_map(final_map)
    else:
        st.info("표시할 위치 데이터가 없습니다.")

    st.divider()

    # ── 상세 목록 ──
    st.subheader("📋 상세 목록")
    st.dataframe(
        fdf[["데이터종류", "명칭", "자치구", "세부유형", "도로명주소"]],
        width="stretch", hide_index=True,
    )
    st.download_button(
        "⬇️ 필터 결과 CSV 다운로드",
        fdf.to_csv(index=False).encode("utf-8-sig"),
        file_name="폭염대응시설_필터결과.csv",
        mime="text/csv",
    )


# ══════════════════════════════════════════════════════════
# 2페이지 · 폭염 정보 (점점 심각해지는 폭염)
# ══════════════════════════════════════════════════════════
else:
    st.title(PAGE2)
    st.caption("기후변화로 폭염의 빈도·강도가 갈수록 심해지고 있습니다.")

    # ── 폭염 심각도·강도 증가 추이 ──
    st.subheader("📈 폭염 심각도·강도, 갈수록 심해지고 있습니다")

    k1, k2, k3 = st.columns(3)
    k1.metric("2025 여름 평균기온", "25.7℃", "평년 23.7℃ (+2.0℃)", delta_color="off")
    k2.metric("2025 폭염일수", "29.7일", "평년 10.5일", delta_color="off")
    k3.metric("2025 열대야일수", "24.5일", "평년 6.3일", delta_color="off")

    trend = pd.DataFrame(
        {"온열질환자 수(명)": HEAT_PATIENTS, "폭염일수(일)": HEATWAVE_DAYS},
        index=HEAT_TREND_YEARS,
    )
    trend.index.name = "연도"

    tc1, tc2 = st.columns(2)
    with tc1:
        st.caption("연도별 온열질환자 수 (명)")
        st.line_chart(trend["온열질환자 수(명)"], color="#E4572E")
    with tc2:
        st.caption("연도별 전국 폭염일수 (일)")
        st.line_chart(trend["폭염일수(일)"], color="#F4A6A0")

    st.caption(
        "자료: 질병관리청 「2025년 폭염으로 인한 온열질환 신고현황 연보」(표2) · 기상청. "
        "감시 시작(2011년) 이후 폭염일수와 온열질환자 수가 뚜렷한 증가 추세를 보이며, "
        "2018년(폭염일수 31일)·2024년(30.1일)·2025년(29.7일)에 역대급 폭염이 반복 발생. "
        "2025년 여름 전국 평균기온은 1973년 관측 이후 역대 1위를 기록."
    )

    st.divider()

    # ── 2025년 서울 온열질환 신고현황 ──
    st.subheader("🌡️ 2025년 서울 온열질환 신고현황 (질병관리청 연보)")

    m1, m2, m3 = st.columns(3)
    m1.metric("서울 온열질환 신고수", f"{SEOUL_HEAT_2025['신고수']:,}명")
    m2.metric("서울 온열질환 사망자수", f"{SEOUL_HEAT_2025['사망자수']:,}명")
    m3.metric("사망 발생 자치구", f"{len(SEOUL_GU_DEATHS_2025)}곳")

    st.caption(
        "⚠️ 연보의 신고수는 광역(시도) 단위까지만 집계되어 서울 합계(378명)만 존재합니다. "
        "자치구별 세부 수치는 '추정 사망 신고사례'의 사망자수만 확인 가능합니다."
    )

    death_df = (
        pd.Series(SEOUL_GU_DEATHS_2025, name="사망자수")
        .rename_axis("자치구").reset_index()
        .sort_values("사망자수", ascending=False)
    )
    st.markdown("**자치구별 온열질환 사망자수**")
    st.dataframe(death_df, width="stretch", hide_index=True)
