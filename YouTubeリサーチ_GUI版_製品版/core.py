
def run_youtube_research(api_key, keywords, min_views, days, sheet_url, service_account_info):
    published_after = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat("T") + "Z"
    videos = []

    for keyword in keywords:
        search_response = youtube.search().list(
            q=keyword,
            part="id,snippet",
            maxResults=50,
            order="date",
            publishedAfter=published_after,
            type="video"
        ).execute()

        for item in search_response["items"]:
            video_id = item["id"]["videoId"]
            video_response = youtube.videos().list(
                part="snippet,statistics",
                id=video_id
            ).execute()

            video = video_response["items"][0]
            view_count = int(video["statistics"].get("viewCount", 0))
            if view_count < min_views:
                continue

            thumbnail_url = video["snippet"]["thumbnails"]["high"]["url"]
            title = video["snippet"]["title"]
            channel_title = video["snippet"]["channelTitle"]
            published_at = video["snippet"]["publishedAt"]

            # サムネイル取得＆base64エンコード（サイズ変更）
            response = requests.get(thumbnail_url)
            img = Image.open(BytesIO(response.content))
            img = img.resize((240, 135))  # ←ここを「元のさらに半分」に
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            videos.append({
                "タイトル": title,
                "チャンネル名": channel_title,
                "投稿日": published_at,
                "再生回数": view_count,
                "動画URL": f"https://www.youtube.com/watch?v={video_id}",
                "サムネイル": f'=IMAGE("data:image/png;base64,{img_base64}")'
            })

    df = pd.DataFrame(videos)

    # Google Sheets 書き込み
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]
    sheet_name = "動画リサーチ結果"

    # シート作成（存在しなければ）
    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
        ).execute()
    except:
        pass

    # 値の書き込み
    values = [df.columns.tolist()] + df.values.tolist()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

    # サムネイル用に列幅と行高調整（列幅：430px / 行高：120px）
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = next(s["properties"]["sheetId"] for s in sheet_metadata["sheets"] if s["properties"]["title"] == sheet_name)

    requests_body = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 5,
                    "endIndex": 6,
                },
                "properties": {"pixelSize": 430},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": len(df) + 1,
                },
                "properties": {"pixelSize": 120},  # ←ここを半分に変更
                "fields": "pixelSize",
            }
        },
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests_body}
    ).execute()

from googleapiclient.discovery import build
