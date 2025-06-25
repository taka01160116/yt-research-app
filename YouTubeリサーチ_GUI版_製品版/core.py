import datetime
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import isodate
import re

def run_youtube_research(api_key, keywords, min_views, days, sheet_url, service_account_info):
    youtube = build("youtube", "v3", developerKey=api_key)
    published_after = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat("T") + "Z"
    videos = []

    for keyword in keywords:
        next_page_token = None
        while True:
            search_response = youtube.search().list(
                q=keyword,
                part="id",
                maxResults=50,
                order="date",
                type="video",
                publishedAfter=published_after,
                pageToken=next_page_token
            ).execute()

            video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
            if not video_ids:
                break

            video_response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()

            for item in video_response["items"]:
                try:
                    duration = isodate.parse_duration(item["contentDetails"]["duration"]).total_seconds()
                    if duration < 190:
                        continue
                    view_count = int(item["statistics"].get("viewCount", 0))
                    channel_id = item["snippet"]["channelId"]

                    channel_response = youtube.channels().list(
                        part="statistics,snippet",
                        id=channel_id
                    ).execute()

                    channel = channel_response["items"][0]
                    subscriber_count = int(channel["statistics"].get("subscriberCount", 0))
                    if view_count < subscriber_count * 3:
                        continue

                    video_id = item["id"]
                    channel_title = item["snippet"]["channelTitle"]
                    published_at = item["snippet"]["publishedAt"]
                    title = item["snippet"]["title"]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"

                    videos.append({
                        "タイトル": title,
                        "チャンネル名": channel_title,
                        "チャンネル登録者数": f"{subscriber_count:,}",
                        "再生回数": f"{view_count / 10000:.2f}万 回視聴",
                        "投稿日": published_at[:10],
                        "URL": video_url,
                        "検索ワード": keyword,
                        "サムネイル": f'=IMAGE("{thumbnail_url}", 4, 120, 215)'
                    })
                except Exception:
                    continue

            next_page_token = search_response.get("nextPageToken")
            if not next_page_token:
                break

    df = pd.DataFrame(videos)
    if df.empty:
        return 0, sheet_url

    sheet_id = sheet_url.split("/d/")[1].split("/")[0]
    sheet_name = "リサーチ結果_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    credentials = service_account.Credentials.from_service_account_info(service_account_info)
    service = build("sheets", "v4", credentials=credentials)

    # 新しいシート作成
    sheet_body = {
        "requests": [{
            "addSheet": {"properties": {"title": sheet_name}}
        }]
    }
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=sheet_body).execute()

    # 値の書き込み
    body = {
        "values": [df.columns.tolist()] + df.values.tolist()
    }
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

    # 対象シートのシートID取得
    meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    sheet_gid = next((s["properties"]["sheetId"] for s in meta["sheets"] if s["properties"]["title"] == sheet_name), 0)

    # セルサイズ調整
    requests = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_gid,
                    "dimension": "COLUMNS",
                    "startIndex": len(df.columns) - 1,
                    "endIndex": len(df.columns),
                },
                "properties": {"pixelSize": 215},
                "fields": "pixelSize",
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_gid,
                    "dimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": len(df) + 1,
                },
                "properties": {"pixelSize": 120},
                "fields": "pixelSize",
            }
        }
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": requests}
    ).execute()

    return len(df), f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid={sheet_gid}"
