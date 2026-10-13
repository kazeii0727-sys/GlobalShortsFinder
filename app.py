
import os
import csv
import io
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from flask import Flask, request, render_template_string, Response

app = Flask(__name__)

API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

COUNTRIES = {
    "US": "미국",
    "GB": "영국",
    "JP": "일본",
    "CA": "캐나다",
    "AU": "호주",
    "IN": "인도",
    "BR": "브라질",
    "KR": "한국",
}

LANGUAGE_BY_COUNTRY = {
    "US": "en",
    "GB": "en",
    "JP": "ja",
    "CA": "en",
    "AU": "en",
    "IN": "en",
    "BR": "pt",
    "KR": "ko",
}

PAGE = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Global Shorts Finder</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    background: #10131b;
    color: #f1f5f9;
    font-family: Arial, sans-serif;
}
main { max-width: 1150px; margin: auto; padding: 24px; }
h1 { font-size: 28px; }
.sub { color: #aab4c5; margin-bottom: 24px; }
.panel {
    background: #1b2130;
    padding: 20px;
    border-radius: 14px;
    margin-bottom: 20px;
}
form {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 15px;
}
label {
    display: block;
    margin-bottom: 7px;
    font-size: 14px;
    color: #cbd5e1;
}
input, select {
    width: 100%;
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #3b4558;
    background: #101723;
    color: white;
}
button {
    grid-column: 1 / -1;
    padding: 14px;
    background: #ef4444;
    border: 0;
    border-radius: 8px;
    color: white;
    font-weight: bold;
    font-size: 16px;
    cursor: pointer;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
    gap: 18px;
}
.card {
    background: #1b2130;
    border-radius: 12px;
    overflow: hidden;
}
.card img {
    width: 100%;
    aspect-ratio: 16 / 9;
    object-fit: cover;
}
.content { padding: 15px; }
.content h3 { font-size: 16px; line-height: 1.5; }
.meta {
    font-size: 13px;
    color: #b8c2d2;
    line-height: 1.9;
    overflow-wrap: anywhere;
}
a { color: #93c5fd; text-decoration: none; }
.notice {
    background: #332819;
    color: #fcd9a0;
    padding: 14px;
    border-radius: 9px;
    margin: 15px 0;
    overflow-wrap: anywhere;
}
.error { background: #422329; color: #fecaca; }
.stats { line-height: 1.9; }
.country-tag {
    display: inline-block;
    background: #153e35;
    color: #86efac;
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 12px;
    margin-top: 5px;
}
@media (max-width: 600px) {
    main { padding: 14px; }
    form { grid-template-columns: 1fr; }
    .grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<main>
<h1>🌎 Global Shorts Finder</h1>
<div class="sub">
국가별 해외 유튜브 쇼츠 발굴 · 채널 국가 확인 필터 적용
</div>

<div class="panel">
<form method="get" action="/">
<div>
<label>검색 국가</label>
<select name="country">
{% for code, name in countries.items() %}
<option value="{{ code }}"
{% if code == country %}selected{% endif %}>
{{ name }} ({{ code }})
</option>
{% endfor %}
</select>
</div>

<div>
<label>검색어 또는 주제</label>
<input name="q" value="{{ q }}"
placeholder="예: funny animals, dance, AI" required>
</div>

<div>
<label>게시 기간</label>
<select name="days">
{% for n, label in [
(1, '최근 24시간'),
(7, '최근 7일'),
(30, '최근 30일'),
(90, '최근 90일')
] %}
<option value="{{ n }}"
{% if n == days %}selected{% endif %}>
{{ label }}
</option>
{% endfor %}
</select>
</div>

<div>
<label>최소 조회수</label>
<select name="minimum">
{% for n, label in [
(1000000, '100만 회 이상'),
(5000000, '500만 회 이상'),
(10000000, '1,000만 회 이상')
] %}
<option value="{{ n }}"
{% if n == minimum %}selected{% endif %}>
{{ label }}
</option>
{% endfor %}
</select>
</div>

<div>
<label>정렬 기준</label>
<select name="order">
<option value="viewCount"
{% if order == 'viewCount' %}selected{% endif %}>
조회수순
</option>
<option value="date"
{% if order == 'date' %}selected{% endif %}>
최신순
</option>
</select>
</div>

<button type="submit">🔎 선택 국가의 쇼츠 검색하기</button>
</form>
</div>

{% if message %}
<div class="notice {% if error %}error{% endif %}">
{{ message }}
</div>
{% endif %}

{% if searched and not error %}
<div class="panel stats">
검색 국가: <b>{{ countries[country] }} ({{ country }})</b><br>
검색 결과: <b>{{ results|length }}개</b><br>
최소 조회수: <b>{{ "{:,}".format(minimum) }}회</b><br>
국가 필터: <b>채널 공개 국가가 선택 국가와 일치하는 영상</b>

{% if results %}
<p><a href="{{ export_url }}">📥 검색 결과 CSV 다운로드</a></p>
{% endif %}

<p class="meta">
검색 지역 및 언어 설정을 YouTube API에 전달하고,
채널이 공개한 국가 정보가 선택 국가와 일치하는지 확인합니다.
국가를 공개하지 않은 채널은 결과에서 제외됩니다.
채널 국가 정보는 영상 촬영 장소나 시청자 국가와 반드시 같지는 않습니다.
API가 반환한 영상 중 조건에 맞는 결과만 표시합니다.
</p>
</div>

<div class="grid">
{% for v in results %}
<div class="card">
<a href="{{ v.url }}" target="_blank" rel="noopener">
<img src="{{ v.thumbnail }}" alt="영상 썸네일" loading="lazy">
</a>
<div class="content">
<h3>
<a href="{{ v.url }}" target="_blank" rel="noopener">
{{ v.title }}
</a>
</h3>
<div class="meta">
채널: {{ v.channel }}<br>
채널 국가: {{ countries.get(v.channel_country, v.channel_country) }}<br>
조회수: <b>{{ "{:,}".format(v.views) }}</b><br>
게시일: {{ v.published }}<br>
영상 길이: {{ v.duration }}<br>
분류: {{ v.kind }}
</div>
<span class="country-tag">국가 확인 완료</span>
<p>
<a href="{{ v.url }}" target="_blank" rel="noopener">
▶ 유튜브에서 보기
</a>
</p>
</div>
</div>
{% endfor %}
</div>

{% if not results %}
<div class="panel">
선택한 국가의 채널 중 조건에 맞는 영상이 없습니다.<br><br>
검색어를 영어 또는 해당 국가의 언어로 바꾸거나,
게시 기간을 늘리고 최소 조회수를 낮춰 다시 검색해 보세요.
국가를 공개하지 않은 채널은 국가 확인이 되지 않아 제외됩니다.
</div>
{% endif %}
{% endif %}
</main>
</body>
</html>
"""


def duration_seconds(value):
    match = re.fullmatch(
        r"PT(?:(\\d+)H)?(?:(\\d+)M)?(?:(\\d+)S)?",
        value or ""
    )
    if not match:
        return 0

    hours, minutes, seconds = (
        int(part or 0) for part in match.groups()
    )
    return hours * 3600 + minutes * 60 + seconds


def duration_label(seconds):
    minutes, seconds = divmod(seconds, 60)

    if minutes >= 60:
        hours, minutes = divmod(minutes, 60)
        return f"{hours}시간 {minutes}분"

    return f"{minutes}분 {seconds}초"


def chunks(values, size=50):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def search_videos(country, query, days, minimum, order):
    from googleapiclient.discovery import build

    youtube = build(
        "youtube",
        "v3",
        developerKey=API_KEY,
        cache_discovery=False
    )

    published_after = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).isoformat(timespec="seconds").replace("+00:00", "Z")

    # 국가별 지역 및 언어 관련성을 검색 요청에 적용합니다.
    search_response = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        videoDuration="short",
        order=order,
        regionCode=country,
        relevanceLanguage=LANGUAGE_BY_COUNTRY.get(country, "en"),
        publishedAfter=published_after,
        maxResults=50
    ).execute()

    search_items = search_response.get("items", [])
    video_ids = []
    channel_ids = []

    for item in search_items:
        video_id = item.get("id", {}).get("videoId")
        channel_id = item.get("snippet", {}).get("channelId")

        if video_id and video_id not in video_ids:
            video_ids.append(video_id)

        if channel_id and channel_id not in channel_ids:
            channel_ids.append(channel_id)

    if not video_ids or not channel_ids:
        return []

    # 채널이 공개한 국가 정보를 조회합니다.
    channel_country = {}

    for channel_batch in chunks(channel_ids):
        response = youtube.channels().list(
            part="snippet",
            id=",".join(channel_batch),
            maxResults=50
        ).execute()

        for channel in response.get("items", []):
            snippet = channel.get("snippet", {})
            channel_country[channel["id"]] = snippet.get("country", "")

    # 국가 정보가 선택 국가와 일치하는 채널만 허용합니다.
    matching_channel_ids = {
        channel_id
        for channel_id, channel_code in channel_country.items()
        if channel_code == country
    }

    if not matching_channel_ids:
        return []

    results = []

    for video_batch in chunks(video_ids):
        details_response = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_batch),
            maxResults=50
        ).execute()

        for item in details_response.get("items", []):
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            content = item.get("contentDetails", {})

            channel_id = snippet.get("channelId", "")

            if channel_id not in matching_channel_ids:
                continue

            views = int(statistics.get("viewCount", 0))

            if views < minimum:
                continue

            seconds = duration_seconds(content.get("duration", ""))

            thumbnails = snippet.get("thumbnails", {})
            thumbnail_data = (
                thumbnails.get("high")
                or thumbnails.get("medium")
                or thumbnails.get("default")
                or {}
            )

            if seconds <= 180:
                kind = "쇼츠 후보 · 화면 비율 확인 필요"
            else:
                kind = "일반 영상 가능성 높음"

            results.append({
                "title": snippet.get("title", ""),
                "channel": snippet.get("channelTitle", ""),
                "channel_country": country,
                "views": views,
                "published": snippet.get("publishedAt", "")[:10],
                "duration": duration_label(seconds),
                "kind": kind,
                "thumbnail": thumbnail_data.get("url", ""),
                "url": "https://www.youtube.com/watch?v=" + item["id"],
                "video_id": item["id"]
            })

    # API 결과 중복을 제거합니다.
    unique_results = {}
    for video in results:
        unique_results[video["video_id"]] = video

    results = list(unique_results.values())

    if order == "viewCount":
        results.sort(key=lambda video: video["views"], reverse=True)
    else:
        results.sort(
            key=lambda video: video["published"],
            reverse=True
        )

    return results


def read_search_options():
    country = request.args.get("country", "US")
    if country not in COUNTRIES:
        country = "US"

    query = request.args.get("q", "viral shorts").strip()[:150]

    try:
        days = int(request.args.get("days", "7"))
    except ValueError:
        days = 7

    if days not in (1, 7, 30, 90):
        days = 7

    try:
        minimum = int(request.args.get("minimum", "1000000"))
    except ValueError:
        minimum = 1000000

    if minimum not in (1000000, 5000000, 10000000):
        minimum = 1000000

    order = request.args.get("order", "viewCount")
    if order not in ("viewCount", "date"):
        order = "viewCount"

    return country, query, days, minimum, order


def perform_search(country, query, days, minimum, order):
    if not query:
        raise ValueError("검색어를 입력해 주세요.")

    if not API_KEY:
        raise RuntimeError(
            "YouTube API 키가 설정되지 않았습니다. "
            "Render 환경 변수 YOUTUBE_API_KEY를 확인해 주세요."
        )

    return search_videos(country, query, days, minimum, order)


@app.route("/")
def index():
    country, query, days, minimum, order = read_search_options()

    results = []
    message = ""
    error = False
    searched = bool(request.args)

    if searched:
        try:
            results = perform_search(
                country, query, days, minimum, order
            )
            if not results:
                message = (
                    "조건에 맞는 국가 확인 영상이 없습니다. "
                    "검색어, 게시 기간 또는 최소 조회수를 바꿔보세요."
                )
        except ValueError as exc:
            message = str(exc)
            error = True
        except RuntimeError as exc:
            message = str(exc)
            error = True
        except Exception as exc:
            app.logger.exception("YouTube search failed")
            message = (
                "검색에 실패했습니다. YouTube API 키, API 활성화 상태, "
                "쿼터 및 요청 설정을 확인해 주세요. "
                f"오류 유형: {type(exc).__name__}"
            )
            error = True

    export_url = "/export?" + urlencode({
        "country": country,
        "q": query,
        "days": days,
        "minimum": minimum,
        "order": order
    })

    return render_template_string(
        PAGE,
        countries=COUNTRIES,
        country=country,
        q=query,
        days=days,
        minimum=minimum,
        order=order,
        results=results,
        message=message,
        error=error,
        searched=searched,
        export_url=export_url
    )


@app.route("/export")
def export():
    country, query, days, minimum, order = read_search_options()

    try:
        results = perform_search(
            country, query, days, minimum, order
        )
    except Exception:
        app.logger.exception("CSV export failed")
        return (
            "CSV 생성에 실패했습니다. API 키와 검색 조건을 확인해 주세요.",
            502
        )

    output = io.StringIO(newline="")
    writer = csv.writer(output)

    writer.writerow([
        "제목",
        "채널",
        "채널 국가",
        "조회수",
        "게시일",
        "영상 길이",
        "분류",
        "영상 URL"
    ])

    for video in results:
        writer.writerow([
            video["title"],
            video["channel"],
            video["channel_country"],
            video["views"],
            video["published"],
            video["duration"],
            video["kind"],
            video["url"]
        ])

    csv_content = "\\ufeff" + output.getvalue()

    return Response(
        csv_content,
        content_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
                "attachment; filename=global_shorts_results.csv"
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
