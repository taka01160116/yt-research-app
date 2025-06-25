
import streamlit as st
from core import run_youtube_research
import json

st.set_page_config(page_title="YouTube繝ｪ繧ｵ繝ｼ繝√ヤ繝ｼ繝ｫ", layout="centered")
st.title("投 YouTube繝ｪ繧ｵ繝ｼ繝√ヤ繝ｼ繝ｫ・・UI迚茨ｼ・)

st.markdown("蠢・ｦ√↑諠・ｱ繧貞・蜉帙＠縺ｦ縲悟ｮ溯｡後阪・繧ｿ繝ｳ繧呈款縺励※縺上□縺輔＞縲・)

api_key = st.text_input("泊 YouTube API繧ｭ繝ｼ", type="password")
keywords = st.text_area("剥 讀懃ｴ｢繧ｭ繝ｼ繝ｯ繝ｼ繝会ｼ医き繝ｳ繝槫玄蛻・ｊ縺ｧ隍・焚蜿ｯ・・, "2ch,蛻・ｊ謚懊″")
min_views = st.number_input("嶋 譛菴主・逕溷屓謨ｰ", min_value=0, value=10000, step=1000)
days = st.number_input("套 驕主悉菴墓律莉･蜀・・蜍慕判繧貞ｯｾ雎｡縺ｫ縺吶ｋ縺・, min_value=1, value=7)
sheet_url = st.text_input("塘 Google繧ｹ繝励Ξ繝・ラ繧ｷ繝ｼ繝医・URL")
uploaded_file = st.file_uploader("唐 繧ｵ繝ｼ繝薙せ繧｢繧ｫ繧ｦ繝ｳ繝茨ｼ・json繝輔ぃ繧､繝ｫ・峨ｒ繧｢繝・・繝ｭ繝ｼ繝・, type="json")

if st.button("笆ｶ 螳溯｡・):
    if not all([api_key, keywords, sheet_url, uploaded_file]):
        st.warning("縺吶∋縺ｦ縺ｮ鬆・岼繧貞・蜉帙・繧｢繝・・繝ｭ繝ｼ繝峨＠縺ｦ縺上□縺輔＞縲・)
    else:
        service_account_info = json.load(uploaded_file)
        keywords_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
        with st.spinner("繝・・繧ｿ蜿門ｾ嶺ｸｭ..."):
            try:
                result_count, sheet_link = run_youtube_research(
                    api_key=api_key,
                    keywords=keywords_list,
                    min_views=min_views,
                    days=days,
                    sheet_url=sheet_url,
                    service_account_info=service_account_info
                )
                st.success(f"{result_count} 莉ｶ縺ｮ繝・・繧ｿ繧呈嶌縺崎ｾｼ縺ｿ縺ｾ縺励◆・・)
                st.markdown(f"迫 [繧ｹ繝励Ξ繝・ラ繧ｷ繝ｼ繝医ｒ髢九￥]({sheet_link})")
            except Exception as e:
                st.error(f"繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆: {e}")
