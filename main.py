import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ------------------- 페이지 설정 -------------------
st.set_page_config(
    page_title="주식 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------- 커스텀 CSS -------------------
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e222d;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #2d3139;
    }
    h1, h2, h3 {
        color: #fafafa;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e222d;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------- 사이드바 -------------------
st.sidebar.title("⚙️ 설정")
st.sidebar.markdown("---")

# 인기 종목 프리셋
preset_stocks = {
    "애플 (AAPL)": "AAPL",
    "테슬라 (TSLA)": "TSLA",
    "엔비디아 (NVDA)": "NVDA",
    "마이크로소프트 (MSFT)": "MSFT",
    "아마존 (AMZN)": "AMZN",
    "구글 (GOOGL)": "GOOGL",
    "메타 (META)": "META",
    "삼성전자 (005930.KS)": "005930.KS",
    "SK하이닉스 (000660.KS)": "000660.KS",
    "카카오 (035720.KS)": "035720.KS",
    "직접 입력": "custom"
}

selected_preset = st.sidebar.selectbox("종목 선택", list(preset_stocks.keys()))

if preset_stocks[selected_preset] == "custom":
    ticker_symbol = st.sidebar.text_input("티커 심볼 입력 (예: AAPL, 005930.KS)", "AAPL").upper()
else:
    ticker_symbol = preset_stocks[selected_preset]

st.sidebar.markdown("---")

# 기간 설정
period_options = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y",
    "최대": "max"
}
selected_period = st.sidebar.selectbox("조회 기간", list(period_options.keys()), index=3)
period = period_options[selected_period]

st.sidebar.markdown("---")

# 이동평균선 설정
st.sidebar.subheader("📊 기술적 지표")
show_ma = st.sidebar.checkbox("이동평균선 (MA)", value=True)
if show_ma:
    ma_short = st.sidebar.slider("단기 이평선", 5, 50, 20)
    ma_long = st.sidebar.slider("장기 이평선", 20, 200, 60)

show_bollinger = st.sidebar.checkbox("볼린저 밴드", value=False)
show_rsi = st.sidebar.checkbox("RSI", value=True)
show_macd = st.sidebar.checkbox("MACD", value=True)
show_volume = st.sidebar.checkbox("거래량", value=True)

st.sidebar.markdown("---")
st.sidebar.info("💡 데이터 출처: Yahoo Finance")

# ------------------- 데이터 로드 함수 -------------------
@st.cache_data(ttl=300)
def load_stock_data(ticker, period):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        info = stock.info
        return df, info
    except Exception as e:
        return None, None

@st.cache_data(ttl=300)
def get_recommendations(ticker):
    try:
        stock = yf.Ticker(ticker)
        return stock.recommendations
    except:
        return None

# ------------------- 기술적 지표 계산 -------------------
def calculate_indicators(df, ma_short, ma_long):
    df['MA_short'] = df['Close'].rolling(window=ma_short).mean()
    df['MA_long'] = df['Close'].rolling(window=ma_long).mean()

    # 볼린저 밴드
    df['BB_mid'] = df['Close'].rolling(window=20).mean()
    df['BB_std'] = df['Close'].rolling(window=20).std()
    df['BB_upper'] = df['BB_mid'] + (df['BB_std'] * 2)
    df['BB_lower'] = df['BB_mid'] - (df['BB_std'] * 2)

    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']

    return df

# ------------------- 메인 타이틀 -------------------
st.title("📈 인터랙티브 주식 분석 대시보드")
st.markdown(f"**{ticker_symbol}** 종목의 실시간 데이터 분석")

# ------------------- 데이터 로드 -------------------
with st.spinner("데이터를 불러오는 중..."):
    df, info = load_stock_data(ticker_symbol, period)

if df is None or df.empty:
    st.error("⚠️ 데이터를 불러올 수 없습니다. 티커 심볼을 확인해주세요.")
    st.stop()

df = calculate_indicators(df, ma_short if show_ma else 20, ma_long if show_ma else 60)

# ------------------- 상단 정보 카드 -------------------
current_price = df['Close'].iloc[-1]
prev_price = df['Close'].iloc[-2] if len(df) > 1 else current_price
price_change = current_price - prev_price
price_change_pct = (price_change / prev_price) * 100 if prev_price != 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    company_name = info.get('shortName', ticker_symbol) if info else ticker_symbol
    st.metric("종목명", company_name)

with col2:
    currency = info.get('currency', 'USD') if info else 'USD'
    st.metric(
        "현재가",
        f"{current_price:,.2f} {currency}",
        f"{price_change:+,.2f} ({price_change_pct:+.2f}%)"
    )

with col3:
    day_high = df['High'].iloc[-1]
    day_low = df['Low'].iloc[-1]
    st.metric("당일 고가/저가", f"{day_high:,.2f} / {day_low:,.2f}")

with col4:
    volume = df['Volume'].iloc[-1]
    st.metric("거래량", f"{volume:,.0f}")

with col5:
    market_cap = info.get('marketCap', 0) if info else 0
    if market_cap:
        if market_cap > 1e12:
            market_cap_str = f"{market_cap/1e12:.2f}T"
        elif market_cap > 1e9:
            market_cap_str = f"{market_cap/1e9:.2f}B"
        else:
            market_cap_str = f"{market_cap/1e6:.2f}M"
        st.metric("시가총액", market_cap_str)
    else:
        st.metric("시가총액", "N/A")

st.markdown("---")

# ------------------- 탭 구성 -------------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 차트 분석", "📋 상세 정보", "📉 통계 분석", "🔍 원본 데이터"])

# ===================== TAB 1: 차트 분석 =====================
with tab1:
    # 서브플롯 개수 계산
    rows = 1
    row_heights = [0.5]
    subplot_titles = ["가격 차트"]

    if show_volume:
        rows += 1
        row_heights.append(0.15)
        subplot_titles.append("거래량")
    if show_rsi:
        rows += 1
        row_heights.append(0.15)
        subplot_titles.append("RSI")
    if show_macd:
        rows += 1
        row_heights.append(0.2)
        subplot_titles.append("MACD")

    # 비율 재조정
    total = sum(row_heights)
    row_heights = [h/total for h in row_heights]

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=subplot_titles
    )

    # 캔들스틱 차트
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="가격",
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1
    )

    # 이동평균선
    if show_ma:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['MA_short'], name=f"MA{ma_short}",
                       line=dict(color='#ffa726', width=1.5)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['MA_long'], name=f"MA{ma_long}",
                       line=dict(color='#42a5f5', width=1.5)),
            row=1, col=1
        )

    # 볼린저 밴드
    if show_bollinger:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['BB_upper'], name="BB 상단",
                       line=dict(color='rgba(173,204,255,0.4)', width=1)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['BB_lower'], name="BB 하단",
                       line=dict(color='rgba(173,204,255,0.4)', width=1),
                       fill='tonexty', fillcolor='rgba(173,204,255,0.1)'),
            row=1, col=1
        )

    current_row = 1

    # 거래량
    if show_volume:
        current_row += 1
        colors = ['#26a69a' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ef5350'
                  for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df.index, y=df['Volume'], name="거래량", marker_color=colors),
            row=current_row, col=1
        )

    # RSI
    if show_rsi:
        current_row += 1
        fig.add_trace(
            go.Scatter(x=df.index, y=df['RSI'], name="RSI",
                       line=dict(color='#ab47bc', width=1.5)),
            row=current_row, col=1
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=current_row, col=1)

    # MACD
    if show_macd:
        current_row += 1
        fig.add_trace(
            go.Scatter(x=df.index, y=df['MACD'], name="MACD",
                       line=dict(color='#42a5f5', width=1.5)),
            row=current_row, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=df['MACD_signal'], name="Signal",
                       line=dict(color='#ffa726', width=1.5)),
            row=current_row, col=1
        )
        hist_colors = ['#26a69a' if val >= 0 else '#ef5350' for val in df['MACD_hist']]
        fig.add_trace(
            go.Bar(x=df.index, y=df['MACD_hist'], name="Histogram", marker_color=hist_colors),
            row=current_row, col=1
        )

    fig.update_layout(
        height=250 * rows + 200,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

    # 가격 변화 히스토그램 & 수익률 차트
    col1, col2 = st.columns(2)

    with col1:
        df['Daily_return'] = df['Close'].pct_change() * 100
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=df['Daily_return'].dropna(),
            nbinsx=50,
            marker_color='#42a5f5'
        ))
        fig_hist.update_layout(
            title="일일 수익률 분포",
            template="plotly_dark",
            xaxis_title="수익률 (%)",
            yaxis_title="빈도",
            height=350
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        df['Cumulative_return'] = (1 + df['Close'].pct_change()).cumprod() - 1
        fig_cum = go.Figure()
        fig_cum.add_trace(go.Scatter(
            x=df.index, y=df['Cumulative_return'] * 100,
            fill='tozeroy',
            line=dict(color='#26a69a')
        ))
        fig_cum.update_layout(
            title="누적 수익률 (%)",
            template="plotly_dark",
            xaxis_title="날짜",
            yaxis_title="누적 수익률 (%)",
            height=350
        )
        st.plotly_chart(fig_cum, use_container_width=True)

# ===================== TAB 2: 상세 정보 =====================
with tab2:
    if info:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🏢 회사 정보")
            st.write(f"**섹터:** {info.get('sector', 'N/A')}")
            st.write(f"**산업:** {info.get('industry', 'N/A')}")
            st.write(f"**국가:** {info.get('country', 'N/A')}")
            st.write(f"**직원 수:** {info.get('fullTimeEmployees', 'N/A'):,}" if info.get('fullTimeEmployees') else "**직원 수:** N/A")
            website = info.get('website', '')
            if website:
                st.write(f"**웹사이트:** [{website}]({website})")

        with col2:
            st.subheader("💰 재무 지표")
            st.write(f"**PER:** {info.get('trailingPE', 'N/A')}")
            st.write(f"**PBR:** {info.get('priceToBook', 'N/A')}")
            st.write(f"**배당수익률:** {info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "**배당수익률:** N/A")
            st.write(f"**52주 최고가:** {info.get('fiftyTwoWeekHigh', 'N/A')}")
            st.write(f"**52주 최저가:** {info.get('fiftyTwoWeekLow', 'N/A')}")

        st.markdown("---")
        st.subheader("📝 회사 개요")
        summary = info.get('longBusinessSummary', '정보 없음')
        st.write(summary)
    else:
        st.warning("상세 정보를 불러올 수 없습니다.")

# ===================== TAB 3: 통계 분석 =====================
with tab3:
    st.subheader("📊 기술 통계")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("평균 종가", f"{df['Close'].mean():,.2f}")
    with col2:
        st.metric("표준편차", f"{df['Close'].std():,.2f}")
    with col3:
        annual_vol = df['Daily_return'].std() * np.sqrt(252)
        st.metric("연간 변동성", f"{annual_vol:.2f}%")
    with col4:
        sharpe = (df['Daily_return'].mean() * 252) / (df['Daily_return'].std() * np.sqrt(252)) if df['Daily_return'].std() != 0 else 0
        st.metric("샤프 비율 (근사)", f"{sharpe:.2f}")

    st.markdown("---")

    # 상관관계 히트맵 (다중 종목 비교)
    st.subheader("🔗 종목 비교 분석")
    compare_tickers = st.multiselect(
        "비교할 종목 추가 선택",
        list(preset_stocks.values())[:-1],
        default=[ticker_symbol] if ticker_symbol in list(preset_stocks.values()) else []
    )

    if len(compare_tickers) >= 2:
        compare_data = {}
        for t in compare_tickers:
            d, _ = load_stock_data(t, period)
            if d is not None and not d.empty:
                compare_data[t] = d['Close']

        if len(compare_data) >= 2:
            compare_df = pd.DataFrame(compare_data)
            returns_df = compare_df.pct_change().dropna()
            corr = returns_df.corr()

            fig_corr = go.Figure(data=go.Heatmap(
                z=corr.values,
                x=corr.columns,
                y=corr.columns,
                colorscale='RdBu',
                zmid=0,
                text=corr.round(2).values,
                texttemplate="%{text}",
                textfont={"size": 12}
            ))
            fig_corr.update_layout(
                title="수익률 상관관계",
                template="plotly_dark",
                height=400
            )
            st.plotly_chart(fig_corr, use_container_width=True)

            # 정규화된 가격 비교
            normalized = compare_df / compare_df.iloc[0] * 100
            fig_compare = go.Figure()
            for col in normalized.columns:
                fig_compare.add_trace(go.Scatter(
                    x=normalized.index, y=normalized[col], name=col, mode='lines'
                ))
            fig_compare.update_layout(
                title="정규화된 가격 비교 (시작=100)",
                template="plotly_dark",
                xaxis_title="날짜",
                yaxis_title="정규화 가격",
                height=400
            )
            st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.info("👆 2개 이상의 종목을 선택하면 비교 분석을 확인할 수 있습니다.")

# ===================== TAB 4: 원본 데이터 =====================
with tab4:
    st.subheader("🔍 원본 데이터 테이블")
    st.dataframe(df.sort_index(ascending=False), use_container_width=True, height=500)

    csv = df.to_csv().encode('utf-8')
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"{ticker_symbol}_data.csv",
        mime="text/csv"
    )

# ------------------- 푸터 -------------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>"
    "Made with ❤️ using Streamlit & Plotly | Data from Yahoo Finance"
    "</div>",
    unsafe_allow_html=True
)
