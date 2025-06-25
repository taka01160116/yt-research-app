
import streamlit as st
from core import run_youtube_research
import json

st.set_page_config(page_title="YouTubeリサーチツール", layout="centered")
st.title("📊 YouTubeリサーチツール（GUI版）")

st.markdown("必要な情報を入力して「実行」ボタンを押してください。")

api_key = st.text_input("🔑 YouTube APIキー", type="password")
keywords = st.text_area("🔍 検索キーワード（カンマ区切りで複数可）", "2ch,切り抜き")
min_views = st.number_input("📈 最低再生回数", min_value=0, value=10000, step=1000)
days = st.number_input("📅 過去何日以内の動画を対象にするか", min_value=1, value=7)
sheet_url = st.text_input("📄 GoogleスプレッドシートのURL")
uploaded_file = st.file_uploader("📂 サービスアカウント（.jsonファイル）をアップロード", type="json")

if st.button("▶ 実行"):
    if not all([api_key, keywords, sheet_url, uploaded_file]):
        st.warning("すべての項目を入力・アップロードしてください。")
    else:
        service_account_info = json.load(uploaded_file)
        keywords_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        with st.spinner("データ取得中..."):
            try:
                result_count, sheet_link = run_youtube_research(
                    api_key=api_key,
                    keywords=keywords_list,
                    min_views=min_views,
                    days=days,
                    sheet_url=sheet_url,
                    service_account_info=service_account_info
                )
                st.success(f"{result_count} 件のデータを書き込みました！")
                st.markdown(f"🔗 [スプレッドシートを開く]({sheet_link})")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
