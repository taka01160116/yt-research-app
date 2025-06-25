import datetime
import requests
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

def run_youtube_research(api_key, keywords, min_views, days, sheet_url, service_account_info):
    youtube = build("youtube", "v3", developerKey=api_key)
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
            video_id = item["id"].get("videoId")
            if not video_id:
                continue

            video_response = youtube.videos().list(
                part="snippet,statistics",
                id=video_id
            ).execute()

            if not video_response["items"]:
                continue

            video = video_response["items"][0]
            view_count = int(video["statistics"].get("viewCount", 0))
            if view_count < min_views:
                continue

            # ✅ サムネイルURLを ytimg.com の静的URLに強制
            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

            title = video["snippet"]["title"]
            channel_title = video["snippet"]["channelTitle"]
            published_at = video["snippet"]["publishedAt"]

            videos.append([
                title,
                channel_title,
                published_at,
                view_count,
                f"https://www.youtube.com/watch?v={video_id}",
                f'=IMAGE("{thumbnail_url}", 4, 60, 215)'
            ])

    df = pd.DataFrame(videos, columns=[
        "タイトル",
        "チャンネル名",
        "投稿日",
        "再生回数",
        "動画URL",
        "サムネイル"
    ])

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=credentials)

    spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]
    sheet_name = "動画リサーチ結果"

    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
        ).execute()
    except Exception as e:
        print(f"シート作成スキップ（既に存在の可能性）: {e}")

    # ✅ ここが重要！valueInputOption を USER_ENTERED に
    values = [df.columns.tolist()] + df.values.tolist()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="USER_ENTERED",  # ← 関数として処理される
        body={"values": values}
    ).execute()

    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = next(s["properties"]["sheetId"] for s in sheet_metadata["sheets"] if s["properties"]["title"] == sheet_name)

    requests_body = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 5,  # サムネイル列（F列: index 5）
                    "endIndex": 6,
                },
                "properties": {"pixelSize": 215},
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
                "properties": {"pixelSize": 60},
                "fields": "pixelSize",
            }
        },
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests_body}
    ).execute()

    return len(df), f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
