import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# ------------------- 페이지 설정 -------------------
st.set_page_config(
    page_title="한국 AI·반도체 주식 분석",
    page_icon="🇰🇷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------- 커스텀 CSS -------------------
st.markdown("""
    <style>
    .stMetric {
        background-color: #1e222d;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #2d3139;
    }
    h1, h2, h3 { color: #fafafa; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e222d;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
    .category-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        margin-bottom: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------- 종목 카테고리 (한국 AI·반도체) -------------------
STOCK_CATEGORIES = {
    "🔷 반도체 대형주": {
        "삼성전자": "005930.KS",
        "SK하이닉스": "000660.KS",
        "삼성전자우": "005935.KS",
        "DB하이텍": "000990.KS",
    },
    "🔧 반도체 소부장(장비/소재)": {
        "한미반도체": "042700.KS",
        "이오테크닉스": "039030.KQ",
        "원익IPS": "240810.KQ",
        "솔브레인": "357780.KQ",
        "티씨케이": "064760.KQ",
        "리노공업": "058470.KQ",
        "심텍": "222800.KQ",
        "넥스틴": "348210.KQ",
        "하나마이크론": "067310.KQ",
        "이수페타시스": "007660.KS",
    },
    "🤖 AI·빅테크 플랫폼": {
        "네이버": "035420.KS",
        "카카오": "035720.KS",
        "삼성SDS": "018260.KS",
        "SK스퀘어": "402340.KS",
        "크래프톤": "259960.KS",
    },
    "🧠 AI 전문기업": {
        "솔트룩스": "304100.KQ",
        "셀바스AI": "108860.KQ",
        "코난테크놀로지": "402030.KQ",
        "알체라": "347860.KQ",
        "위세아이텍": "260970.KQ",
    },
    "📺 디스플레이/전자": {
        "LG전자": "066570.KS",
        "LG디스플레이": "034220.KS",
        "삼성전기": "009150.KS",
    },
}

# 전체 종목 딕셔너리 (검색용)
ALL_STOCKS = {}
for cat, stocks in STOCK_CATEGORIES.items():
    ALL_STOCKS.update(stocks)

# ------------------- 사이드바 -------------------
st.sidebar.title("🇰🇷 AI·반도체 주식 설정")
st.sidebar.markdown("---")

selected_category = st.sidebar.selectbox("📂 카테고리 선택", list(STOCK_CATEGORIES.keys()))
stocks_in_category = STOCK_CATEGORIES[selected_category]
selected_name = st.sidebar.selectbox("🏢 종목 선택", list(stocks_in_category.keys()))
ticker_symbol = stocks_in_category[selected_name]

st.sidebar.caption(f"티커: `{ticker_symbol}`")
st.sidebar.markdown("---")

# 기간 설정
period_options = {
    "1개월": "1mo", "3개월": "3mo", "6개월": "6mo",
    "1년": "1y", "2년": "2y", "5년": "5y", "최대": "max"
}
selected_period = st.sidebar.selectbox("📅 조회 기간", list(period_options.keys()), index=3)
period = period_options[selected_period]

st.sidebar.markdown("---")

# 벤치마크 비교
st.sidebar.subheader("📊 벤치마크 비교")
compare_kospi = st.sidebar.checkbox("KOSPI 지수와 비교", value=False)
compare_sox = st.sidebar.checkbox("필라델피아 반도체지수(SOX)와 비교", value=False)

st.sidebar.markdown("---")

# 기술적 지표 설정
st.sidebar.subheader("📈 기술적 지표")
show_ma = st.sidebar.checkbox("이동평균선 (MA)", value=True)
if show_ma:
    ma_short = st.sidebar.slider("단기 이평선", 5, 50, 20)
    ma_long = st.sidebar.slider("장기 이평선", 20, 200, 60)
else:
    ma_short, ma_long = 20, 60

show_bollinger = st.sidebar.checkbox("볼린저 밴드", value=False)
show_rsi = st.sidebar.checkbox("RSI", value=True)
show_macd = st.sidebar.checkbox("MACD", value=True)
show_volume = st.sidebar.checkbox("거래량", value=True)

st.sidebar.markdown("---")
st.sidebar.info("💡 데이터 출처: Yahoo Finance\n\n한국거래소(KRX) 종목 기준")

# ------------------- 데이터 로드 함수 -------------------
@st.cache_data(ttl=300)
def load_stock_data(ticker, period):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        info = stock.info
        return df, info
    except Exception:
        return None, None

@st.cache_data(ttl=300)
def load_benchmark(ticker, period):
    try:
        df = yf.Ticker(ticker).history(period=period)
        return df['Close']
    except Exception:
        return None

# ------------------- 기술적 지표 계산 -------------------
def calculate_indicators(df, ma_short, ma_long):
    df['MA_short'] = df['Close'].rolling(window=ma_short).mean()
    df['MA_long'] = df['Close'].rolling(window=ma_long).mean()

    df['BB_mid'] = df['Close'].rolling(window=20).mean()
    df['BB_std'] = df['Close'].rolling(window=20).std()
    df['BB_upper'] = df['BB_mid'] + (df['BB_std'] * 2)
    df['BB_lower'] = df['BB_mid'] - (df['BB_std'] * 2)

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']

    return df

# ------------------- 메인 타이틀 -------------------
st.title("🇰🇷 한국 AI·반도체 대표주 분석 대시보드")
st.markdown(f"**{selected_category}** › **{selected_name}** ({ticker_symbol})")

# ------------------- 데이터 로드 -------------------
with st.spinner("데이터를 불러오는 중..."):
    df, info = load_stock_data(ticker_symbol, period)

if df is None or df.empty:
    st.error("⚠️ 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

df = calculate_indicators(df, ma_short, ma_long)
df['Daily_return'] = df['Close'].pct_change() * 100
df['Cumulative_return'] = (1 + df['Close'].pct_change()).cumprod() - 1

# ------------------- 상단 정보 카드 -------------------
current_price = df['Close'].iloc[-1]
prev_price = df['Close'].iloc[-2] if len(df) > 1 else current_price
price_change = current_price - prev_price
price_change_pct = (price_change / prev_price) * 100 if prev_price != 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("종목명", selected_name)

with col2:
    st.metric(
        "현재가 (원)",
        f"{current_price:,.0f}",
        f"{price_change:+,.0f} ({price_change_pct:+.2f}%)"
    )

with col3:
    day_high = df['High'].iloc[-1]
    day_low = df['Low'].iloc[-1]
    st.metric("당일 고가/저가", f"{day_high:,.0f} / {day_low:,.0f}")

with col4:
    volume = df['Volume'].iloc[-1]
    st.metric("거래량", f"{volume:,.0f}")

with col5:
    market_cap = info.get('marketCap', 0) if info else 0
    if market_cap:
        if market_cap > 1e12:
            market_cap_str = f"{market_cap/1e12:.1f}조"
        else:
            market_cap_str = f"{market_cap/1e8:.0f}억"
        st.metric("시가총액", market_cap_str)
    else:
        st.metric("시가총액", "N/A")

st.markdown("---")

# ------------------- 탭 구성 -------------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 차트 분석", "📋 상세 정보", "🔍 섹터 비교", "📥 원본 데이터"])

# ===================== TAB 1: 차트 분석 =====================
with tab1:
    rows = 1
    row_heights = [0.5]
    subplot_titles = ["가격 차트"]

    if show_volume:
        rows += 1; row_heights.append(0.15); subplot_titles.append("거래량")
    if show_rsi:
        rows += 1; row_heights.append(0.15); subplot_titles.append("RSI")
    if show_macd:
        rows += 1; row_heights.append(0.2); subplot_titles.append("MACD")

    total = sum(row_heights)
    row_heights = [h/total for h in row_heights]

    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=row_heights, subplot_titles=subplot_titles
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'], name="가격",
            increasing_line_color='#ef5350', decreasing_line_color='#2196f3'
        ), row=1, col=1
    )

    if show_ma:
        fig.add_trace(go.Scatter(x=df.index, y=df['MA_short'], name=f"MA{ma_short}",
                       line=dict(color='#ffa726', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA_long'], name=f"MA{ma_long}",
                       line=dict(color='#42a5f5', width=1.5)), row=1, col=1)

    if show_bollinger:
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_upper'], name="BB 상단",
                       line=dict(color='rgba(173,204,255,0.4)', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_lower'], name="BB 하단",
                       line=dict(color='rgba(173,204,255,0.4)', width=1),
                       fill='tonexty', fillcolor='rgba(173,204,255,0.1)'), row=1, col=1)

    current_row = 1

    if show_volume:
        current_row += 1
        colors = ['#ef5350' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#2196f3'
                  for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="거래량", marker_color=colors),
                      row=current_row, col=1)

    if show_rsi:
        current_row += 1
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI",
                       line=dict(color='#ab47bc', width=1.5)), row=current_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=current_row, col=1)

    if show_macd:
        current_row += 1
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="MACD",
                       line=dict(color='#42a5f5', width=1.5)), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_signal'], name="Signal",
                       line=dict(color='#ffa726', width=1.5)), row=current_row, col=1)
        hist_colors = ['#ef5350' if v >= 0 else '#2196f3' for v in df['MACD_hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_hist'], name="Histogram",
                       marker_color=hist_colors), row=current_row, col=1)

    fig.update_layout(
        height=250 * rows + 200, template="plotly_dark",
        xaxis_rangeslider_visible=False, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=10), hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

    # 수익률 분석
    col1, col2 = st.columns(2)

    with col1:
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=df['Daily_return'].dropna(), nbinsx=50, marker_color='#42a5f5'
        ))
        fig_hist.update_layout(title="일일 수익률 분포", template="plotly_dark",
                       xaxis_title="수익률 (%)", yaxis_title="빈도", height=350)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=df.index, y=df['Cumulative_return'] * 100,
            fill='tozeroy', line=dict(color='#ef5350')
        ))
        fig_cum.update_layout(title="누적 수익률 (%)", template="plotly_dark",
                       xaxis_title="날짜", yaxis_title="누적 수익률 (%)", height=350)
        st.plotly_chart(fig_cum, use_container_width=True)

    # 벤치마크 비교
    if compare_kospi or compare_sox:
        st.markdown("---")
        st.subheader("📊 벤치마크 대비 성과")

        normalized_stock = df['Close'] / df['Close'].iloc[0] * 100
        fig_bench = go.Figure()
        fig_bench.add_trace(go.Scatter(
            x=df.index, y=normalized_stock, name=selected_name,
            line=dict(color='#ef5350', width=2)
        ))

        if compare_kospi:
            kospi = load_benchmark("^KS11", period)
            if kospi is not None:
                kospi_norm = kospi / kospi.iloc[0] * 100
                fig_bench.add_trace(go.Scatter(
                    x=kospi.index, y=kospi_norm, name="KOSPI",
                    line=dict(color='#42a5f5', width=1.5, dash='dash')
                ))

        if compare_sox:
            sox = load_benchmark("^SOX", period)
            if sox is not None:
                sox_norm = sox / sox.iloc[0] * 100
                fig_bench.add_trace(go.Scatter(
                    x=sox.index, y=sox_norm, name="필라델피아 반도체지수",
                    line=dict(color='#ffa726', width=1.5, dash='dot')
                ))

        fig_bench.update_layout(
            title="정규화된 상대 성과 비교 (시작=100)",
            template="plotly_dark", xaxis_title="날짜", yaxis_title="정규화 지수",
            height=400, hovermode='x unified'
        )
        st.plotly_chart(fig_bench, use_container_width=True)

# ===================== TAB 2: 상세 정보 =====================
with tab2:
    if info:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏢 회사 정보")
            st.write(f"**섹터:** {info.get('sector', 'N/A')}")
            st.write(f"**산업:** {info.get('industry', 'N/A')}")
            st.write(f"**국가:** {info.get('country', '대한민국')}")
            emp = info.get('fullTimeEmployees')
            st.write(f"**직원 수:** {emp:,}" if emp else "**직원 수:** N/A")
            website = info.get('website', '')
            if website:
                st.write(f"**웹사이트:** [{website}]({website})")

        with col2:
            st.subheader("💰 재무 지표")
            per = info.get('trailingPE')
            pbr = info.get('priceToBook')
            div_yield = info.get('dividendYield')
            st.write(f"**PER:** {per:.2f}" if per else "**PER:** N/A")
            st.write(f"**PBR:** {pbr:.2f}" if pbr else "**PBR:** N/A")
            st.write(f"**배당수익률:** {div_yield*100:.2f}%" if div_yield else "**배당수익률:** N/A")
            st.write(f"**52주 최고가:** {info.get('fiftyTwoWeekHigh', 'N/A'):,}" if info.get('fiftyTwoWeekHigh') else "**52주 최고가:** N/A")
            st.write(f"**52주 최저가:** {info.get('fiftyTwoWeekLow', 'N/A'):,}" if info.get('fiftyTwoWeekLow') else "**52주 최저가:** N/A")

        st.markdown("---")
        st.subheader("📊 기술 통계")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("평균 종가", f"{df['Close'].mean():,.0f}")
        with c2:
            st.metric("표준편차", f"{df['Close'].std():,.0f}")
        with c3:
            annual_vol = df['Daily_return'].std() * np.sqrt(252)
            st.metric("연간 변동성", f"{annual_vol:.2f}%")
        with c4:
            sharpe = (df['Daily_return'].mean() * 252) / (df['Daily_return'].std() * np.sqrt(252)) if df['Daily_return'].std() != 0 else 0
            st.metric("샤프 비율(근사)", f"{sharpe:.2f}")

        summary = info.get('longBusinessSummary', '')
        if summary:
            st.markdown("---")
            st.subheader("📝 회사 개요 (영문)")
            st.write(summary)
    else:
        st.warning("상세 정보를 불러올 수 없습니다.")

# ===================== TAB 3: 섹터 비교 =====================
with tab3:
    st.subheader(f"🔍 {selected_category} 내 종목 비교")

    compare_names = st.multiselect(
        "비교할 종목 선택 (같은 카테고리 또는 다른 카테고리 모두 선택 가능)",
        list(ALL_STOCKS.keys()),
        default=list(stocks_in_category.keys())[:min(4, len(stocks_in_category))]
    )

    if len(compare_names) >= 2:
        compare_data = {}
        with st.spinner("비교 데이터를 불러오는 중..."):
            for name in compare_names:
                t = ALL_STOCKS[name]
                d, _ = load_stock_data(t, period)
                if d is not None and not d.empty:
                    compare_data[name] = d['Close']

        if len(compare_data) >= 2:
            compare_df = pd.DataFrame(compare_data)
            returns_df = compare_df.pct_change().dropna()
            corr = returns_df.corr()

            fig_corr = go.Figure(data=go.Heatmap(
                z=corr.values, x=corr.columns, y=corr.columns,
                colorscale='RdBu_r', zmid=0,
                text=corr.round(2).values, texttemplate="%{text}",
                textfont={"size": 11}
            ))
            fig_corr.update_layout(title="수익률 상관관계", template="plotly_dark", height=450)
            st.plotly_chart(fig_corr, use_container_width=True)

            normalized = compare_df / compare_df.iloc[0] * 100
            fig_compare = go.Figure()
            for col in normalized.columns:
                fig_compare.add_trace(go.Scatter(
                    x=normalized.index, y=normalized[col], name=col, mode='lines'
                ))
            fig_compare.update_layout(
                title="정규화된 가격 비교 (시작=100)", template="plotly_dark",
                xaxis_title="날짜", yaxis_title="정규화 가격", height=450, hovermode='x unified'
            )
            st.plotly_chart(fig_compare, use_container_width=True)

            # 수익률 요약 테이블
            st.subheader("📋 기간 수익률 요약")
            summary_data = []
            for name in compare_data.keys():
                total_return = (compare_df[name].iloc[-1] / compare_df[name].iloc[0] - 1) * 100
                volatility = returns_df[name].std() * np.sqrt(252) * 100
                summary_data.append({
                    "종목명": name,
                    "기간 수익률(%)": round(total_return, 2),
                    "연간 변동성(%)": round(volatility, 2)
                })
            summary_table = pd.DataFrame(summary_data).sort_values("기간 수익률(%)", ascending=False)
            st.dataframe(summary_table, use_container_width=True, hide_index=True)
        else:
            st.warning("데이터를 불러오지 못했습니다.")
    else:
        st.info("👆 2개 이상의 종목을 선택하면 비교 분석을 확인할 수 있습니다.")

    st.markdown("---")
    st.subheader("📂 전체 종목 리스트")
    for cat, stocks in STOCK_CATEGORIES.items():
        with st.expander(cat):
            for name, ticker in stocks.items():
                st.write(f"- **{name}** (`{ticker}`)")

# ===================== TAB 4: 원본 데이터 =====================
with tab4:
    st.subheader("📥 원본 데이터 테이블")
    st.dataframe(df.sort_index(ascending=False), use_container_width=True, height=500)

    csv = df.to_csv().encode('utf-8-sig')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"{selected_name}_{ticker_symbol}_data.csv",
        mime="text/csv"
    )

# ------------------- 푸터 -------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "🇰🇷 한국 AI·반도체 대표주 분석 대시보드 | Made with Streamlit & Plotly | "
    "Data from Yahoo Finance"
    "</div>",
    unsafe_allow_html=True
)
