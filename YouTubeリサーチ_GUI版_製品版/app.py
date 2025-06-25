
import streamlit as st
from core import run_youtube_research
import json

st.set_page_config(page_title="YouTubeリサーチツール", layout="centered")
st.title("📊 YouTubeリサーチツール�E�EUI版！E)

st.markdown("忁E��な惁E��を�E力して「実行」�Eタンを押してください、E)

api_key = st.text_input("🔑 YouTube APIキー", type="password")
keywords = st.text_area("🔍 検索キーワード（カンマ区刁E��で褁E��可�E�E, "2ch,刁E��抜き")
min_views = st.number_input("📈 最低�E生回数", min_value=0, value=10000, step=1000)
days = st.number_input("📅 過去何日以冁E�E動画を対象にするぁE, min_value=1, value=7)
sheet_url = st.text_input("📄 GoogleスプレチE��シート�EURL")
uploaded_file = st.file_uploader("📂 サービスアカウント！Ejsonファイル�E�をアチE�EローチE, type="json")

if st.button("▶ 実衁E):
    if not all([api_key, keywords, sheet_url, uploaded_file]):
        st.warning("すべての頁E��を�E力�EアチE�Eロードしてください、E)
    else:
        service_account_info = json.load(uploaded_file)
        keywords_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        with st.spinner("チE�Eタ取得中..."):
            try:
                result_count, sheet_link = run_youtube_research(
                    api_key=api_key,
                    keywords=keywords_list,
                    min_views=min_views,
                    days=days,
                    sheet_url=sheet_url,
                    service_account_info=service_account_info
                )
                st.success(f"{result_count} 件のチE�Eタを書き込みました�E�E)
                st.markdown(f"🔗 [スプレチE��シートを開く]({sheet_link})")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
