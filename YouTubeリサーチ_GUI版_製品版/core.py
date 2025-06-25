import datetime
import requests
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import isodate
from collections import defaultdict

def parse_duration(duration):
    try:
        return int(isodate.parse_duration(duration).total_seconds())
    except:
        return 0

def run_youtube_research(api_key, keywords, min_views, days, sheet_url, service_account_info):
    youtube = build("youtube", "v3", developerKey=api_key)
    published_after = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat("T") + "Z"
    videos = []
    channel_cache = {}  # channel_id → subscriber_count

    for keyword in keywords:
        next_page_token = None
        while True:
            search_response = youtube.search().list(
                q=keyword,
                part="id,snippet",
                maxResults=50,
                order="date",
                publishedAfter=published_after,
                type="video",
                pageToken=next_page_token
            ).execute()

            video_ids = []
            video_snippet_map = {}

            for item in search_response["items"]:
                video_id = item["id"].get("videoId")
                if not video_id:
                    continue
                video_ids.append(video_id)
                video_snippet_map[video_id] = item["snippet"]

            if not video_ids:
                break

            # まとめて videos.list（最大50件）
            video_response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()

            for video in video_response["items"]:
                video_id = video["id"]
                snippet = video_snippet_map.get(video_id)
                if not snippet:
                    continue

                view_count = int(video["statistics"].get("viewCount", 0))
                duration = video["contentDetails"]["duration"]
                total_seconds = parse_duration(duration)

                if view_count < min_views or total_seconds < 190:
                    continue

                title = video["snippet"]["title"]
                channel_title = video["snippet"]["channelTitle"]
                published_at = video["snippet"]["publishedAt"]
                thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                channel_id = video["snippet"]["channelId"]

                # チャンネル登録者数の取得（キャッシュあり）
                if channel_id not in channel_cache:
                    try:
                        channel_response = youtube.channels().list(
                            part="statistics",
                            id=channel_id
                        ).execute()
                        subscriber_count = channel_response["items"][0]["statistics"].get("subscriberCount", "非公開")
                        if subscriber_count != "非公開":
                            subscriber_count = f"{int(subscriber_count):,}"
                        channel_cache[channel_id] = subscriber_count
                    except:
                        channel_cache[channel_id] = "取得失敗"

                subscriber_count = channel_cache[channel_id]

                videos.append([
                    title,
                    channel_title,
                    subscriber_count,
                    view_count,
                    published_at,
                    f"https://www.youtube.com/watch?v={video_id}",
                    f'=IMAGE("https://i.ytimg.com/vi/{video_id}/hqdefault.jpg", 4, 135, 240)'
                ])

            next_page_token = search_response.get("nextPageToken")
            if not next_page_token:
                break

    df = pd.DataFrame(videos, columns=[
        "タイトル",
        "チャンネル名",
        "チャンネル登録者",
        "再生回数",
        "投稿日",
        "動画URL",
        "サムネイル"
    ])

    # Google Sheets 書き出し
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=credentials)

    spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sheet_name = f"動画リサーチ結果_{now}"

    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
        ).execute()
    except Exception as e:
        print(f"シート作成スキップ: {e}")

    values = [df.columns.tolist()] + df.values.tolist()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values}
    ).execute()

    # サムネイル列サイズ調整（画像潰れ防止）
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = next(s["properties"]["sheetId"] for s in sheet_metadata["sheets"] if s["properties"]["title"] == sheet_name)

    requests_body = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 6,
                    "endIndex": 7,
                },
                "properties": {"pixelSize": 240},
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
                "properties": {"pixelSize": 135},
                "fields": "pixelSize",
            }
        }
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests_body}
    ).execute()

    return len(df), f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
