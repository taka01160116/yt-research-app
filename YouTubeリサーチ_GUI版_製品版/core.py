import datetime
import requests
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import isodate

def parse_duration(duration):
    try:
        return int(isodate.parse_duration(duration).total_seconds())
    except:
        return 0

def run_youtube_research(api_key, keywords, min_views, days, sheet_url, service_account_info):
    youtube = build("youtube", "v3", developerKey=api_key)
    published_after = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).isoformat("T") + "Z"
    videos = []
    seen_ids = set()  # ✅ 重複排除のためのセット
    channel_cache = {}

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

            video_response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids)
            ).execute()

            for video in video_response["items"]:
                video_id = video["id"]

                if video_id in seen_ids:
                    continue  # ✅ 既に追加済みならスキップ
                seen_ids.add(video_id)

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

                if channel_id not in channel_cache:
                    try:
                        ch_response = youtube.channels().list(
                            part="statistics",
                            id=channel_id
                        ).execute()
                        sub_count = ch_response["items"][0]["statistics"].get("subscriberCount", "非公開")
                        if sub_count != "非公開":
                            sub_count_int = int(sub_count)
                            sub_count = f"{sub_count_int:,}"
                        else:
                            sub_count_int = 0
                        channel_cache[channel_id] = (sub_count, sub_count_int)
                    except:
                        channel_cache[channel_id] = ("取得失敗", 0)

                subscriber_count_str, subscriber_count_int = channel_cache[channel_id]

                if subscriber_count_int > 0 and view_count < subscriber_count_int * 3:
                    continue

                videos.append([
                    title,
                    channel_title,
                    subscriber_count_str,
                    view_count,
                    published_at,
                    f"https://www.youtube.com/watch?v={video_id}",
                    f'=IMAGE("{thumbnail_url}", 4, 135, 240)'
                ])

            next_page_token = search_response.get("nextPageToken")
            if not next_page_token:
                break

    if not videos:
        return 0, "検索結果が0件のため、スプレッドシートは作成されませんでした。"

    df = pd.DataFrame(videos, columns=[
        "タイトル",
        "チャンネル名",
        "チャンネル登録者",
        "再生回数",
        "投稿日",
        "動画URL",
        "サムネイル"
    ])
    df.sort_values("再生回数", ascending=False, inplace=True)

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=credentials)

    spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]
    sheet_name = "動画リサーチ結果_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
    ).execute()

    values = [df.columns.tolist()] + df.values.tolist()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": values}
    ).execute()

    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = next(s["properties"]["sheetId"] for s in sheet_metadata["sheets"] if s["properties"]["title"] == sheet_name)

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
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
        }
    ).execute()

    return len(df), f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
