import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 計算ロジック ---
def calculate_usage_advanced(total_bill, amp, r1, r2, r3, fuel_adj, renewable_tax):
    amp_rates = {10: 311.52, 15: 467.28, 20: 623.04, 30: 934.56, 40: 1246.08, 50: 1557.60, 60: 1869.12}
    basic_fee = amp_rates.get(amp, 0)
    real_rates = [r + fuel_adj + renewable_tax for r in [r1, r2, r3]]
    remaining = total_bill - basic_fee
    if remaining <= 0: return 0.0
    usage = 0.0
    if remaining <= 120 * real_rates[0]: return remaining / real_rates[0]
    usage += 120; remaining -= 120 * real_rates[0]
    if remaining <= 180 * real_rates[1]: return usage + (remaining / real_rates[1])
    usage += 180; remaining -= 180 * real_rates[1]
    usage += remaining / real_rates[2]
    return usage

def get_bill_from_usage(usage, amp, r1, r2, r3, fuel_adj, renewable_tax):
    amp_rates = {10: 311.52, 15: 467.28, 20: 623.04, 30: 934.56, 40: 1246.08, 50: 1557.60, 60: 1869.12}
    bill = amp_rates.get(amp, 0)
    real_rates = [r + fuel_adj + renewable_tax for r in [r1, r2, r3]]
    if usage <= 120: bill += usage * real_rates[0]
    elif usage <= 300: bill += (120 * real_rates[0]) + (usage - 120) * real_rates[1]
    else: bill += (120 * real_rates[0]) + (180 * real_rates[1]) + (usage - 300) * real_rates[2]
    return bill

# --- メイン UI ---
st.set_page_config(page_title="太陽光・蓄電池診断", layout="wide")

st.markdown("""
    <style>
    @media print {
        section[data-testid="stSidebar"] { display: none !important; }
        .stTabs [data-baseweb="tab-list"] { display: none !important; }
        div[data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    }
    h1 { font-size: 1.6rem !important; margin-bottom: 0.5rem !important; }
    h2 { font-size: 1.2rem !important; margin-top: 1.5rem !important; margin-bottom: 1.0rem !important; }
    .stMetric { background-color: #f8f9fa; border-radius: 5px; padding: 5px; }
    </style>
    """, unsafe_allow_html=True)

# サイドバー設定
with st.sidebar:
    st.header("📋 詳細パラメータ設定")
    customer_name = st.text_input("お客様名", value="サンプル")
    solar_kw = st.number_input("太陽光パネル容量 (kW)", value=5.5)
    solar_gen = st.number_input("月間想定発電量 (kWh)", value=450)
    battery_capacity = st.number_input("蓄電容量 (kWh)", value=9.8)
    bill = st.number_input("現在の月額請求 (円)", value=15000)
    amp = st.selectbox("契約アンペア", [10, 15, 20, 30, 40, 50, 60], index=3)
    sell_price = st.number_input("売電単価 (円)", value=16.0)
    st.divider()
    fuel_adj = st.number_input("燃料費調整額", value=4.80)
    renew_tax = st.number_input("再エネ賦課金", value=3.49)
    r1, r2, r3 = 30.0, 36.6, 40.69
    self_consume_rate = st.slider("日中の自家消費率 (%)", 0, 100, 35)

# --- 計算 ---
current_usage = calculate_usage_advanced(bill, amp, r1, r2, r3, fuel_adj, renew_tax)
usage_day, usage_night = current_usage * 0.3, current_usage * 0.7
monthly_battery_limit = battery_capacity * 0.88 * 30
actual_self_consume_day = min(usage_day, solar_gen * (self_consume_rate / 100))
excess_solar = max(0, solar_gen - actual_self_consume_day)
actual_self_consume_night = min(usage_night, excess_solar, monthly_battery_limit)
total_self_consume = actual_self_consume_day + actual_self_consume_night
sold_kwh = solar_gen - total_self_consume
new_usage = max(0, current_usage - total_self_consume)
new_bill = get_bill_from_usage(new_usage, amp, r1, r2, r3, fuel_adj, renew_tax)
sell_revenue = sold_kwh * sell_price
net_cost = new_bill - sell_revenue
total_benefit = (bill - new_bill) + sell_revenue

# --- 紙面レイアウト ---
st.title(f"☀️ {customer_name} 様：太陽光・蓄電池 導入効果診断書")

st.info(f"【試算条件】 太陽光：{solar_kw}kW ／ 蓄電池：{battery_capacity}kWh ／ 売電単価：{sell_price}円 ／ 元の電気代：{bill:,}円")

m1, m2, m3, m4 = st.columns(4)
m1.metric("推定の元使用量", f"{current_usage:.1f} kWh")
m2.metric("導入後買電量", f"{new_usage:.1f} kWh")
m3.metric("月間経済効果", f"{int(total_benefit):,} 円")
m4.metric("実質負担額", f"{int(net_cost):,} 円")

tab1, tab2 = st.tabs(["📊 月間シミュレーション", "📉 25年長期予測"])

with tab1:
    st.subheader("導入前後の比較（月間）")
    g1, g2 = st.columns(2)
    # グラフ上部の余白(t)を増やして見出しとの重なりを防止
    common_layout = dict(height=420, margin=dict(t=70, b=40, l=40, r=40), legend=dict(orientation="h", y=1.1))
    
    with g1:
        fig_usage = go.Figure()
        fig_usage.add_trace(go.Bar(name='元の買電量', x=['導入前'], y=[current_usage], text=[f"{current_usage:.0f}"], textposition='auto', marker_color='gray', width=0.4))
        fig_usage.add_trace(go.Bar(name='導入後の買電量', x=['導入後'], y=[new_usage], text=[f"{new_usage:.0f}"], textposition='auto', marker_color='orange', width=0.4))
        fig_usage.add_trace(go.Bar(name='削減量(自家消費)', x=['導入後'], y=[total_self_consume], text=[f"{total_self_consume:.0f}"], textposition='auto', marker_color='green', width=0.4))
        fig_usage.update_layout(title="使用量内訳 (kWh)", barmode='stack', **common_layout)
        st.plotly_chart(fig_usage, use_container_width=True)

    with g2:
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(name='支払額', x=['導入前', '導入後'], y=[bill, new_bill], text=[f"{int(bill)}", f"{int(new_bill)}"], textposition='auto', marker_color='indianred', width=0.4))
        fig_cost.add_trace(go.Bar(name='売電利益', x=['導入前', '導入後'], y=[0, sell_revenue], text=["", f"{int(sell_revenue)}"], textposition='auto', marker_color='skyblue', width=0.4))
        fig_cost.update_layout(title="コスト・収益比較 (円)", barmode='group', **common_layout)
        st.plotly_chart(fig_cost, use_container_width=True)
    
    st.write(f"※蓄電池実効容量制限（月間 {monthly_battery_limit:.1f} kWh）に基づき、夜間の買電削減量を算出しています。")

with tab2:
    st.subheader("25年間の累積コスト予測（1年刻み）")
    years_list = [f"{y}" for y in range(1, 26)]
    no_solar_cum = [bill * 12 * y for y in range(1, 26)]
    with_solar_cum = [net_cost * 12 * y for y in range(1, 26)]
    
    fig_long = go.Figure()
    fig_long.add_trace(go.Bar(name='導入なし', x=years_list, y=no_solar_cum, marker_color='lightgray'))
    fig_long.add_trace(go.Bar(name='導入あり', x=years_list, y=with_solar_cum, marker_color='orange'))
    fig_long.update_layout(height=480, barmode='group', yaxis_title="累積コスト(円)", legend=dict(orientation="h", y=1.1), margin=dict(t=60))
    fig_long.update_traces(texttemplate='%{y:,.0f}', textposition='outside', textangle=-90, textfont_size=8)
    st.plotly_chart(fig_long, use_container_width=True)
    st.success(f"25年間で想定される合計メリット： 約 {int(no_solar_cum[-1] - with_solar_cum[-1]):,} 円")

# ご指定の免責事項を反映
st.markdown(f"""
---
**【免責事項・ご確認事項】**
* 本シミュレーションは、{customer_name} 様から提供いただいた請求額および2026年2月時点の料金体系に基づく推定値です。
* 将来の発電量・売電収益を保証するものではありません。実際の数値は天候、パネルの経年劣化、電力会社の価格改定、および燃料費調整額の変動等により変化します。
* 蓄電池の性能、充放電ロス、および実効容量は理論値に基づいて計算しており、実際の運用環境とは異なる場合があります。
* 本結果により生じた如何なる不利益についても、制作者および提供者は一切の責任を負いかねます。最終判断は自己責任でお願いいたします。

""")
