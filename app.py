
import csv
import io
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from flask import Flask, request, render_template_string, make_response
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)

API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()

COUNTRIES = {
    "US": "미국",
    "GB": "영국",
    "JP": "일본",
    "CA": "캐나다",
    "AU": "호주",
    "IN": "인도",
    "BR": "브라질",
    "KR": "대한민국",
    "MX": "멕시코",
    "DE": "독일",
    "FR": "프랑스",
    "ES": "스페인",
    "IT": "이탈리아",
    "ID": "인도네시아",
    "PH": "필리핀",
    "TH": "태국",
}

LANGUAGES = {
    "US": "en", "GB": "en", "CA": "en", "AU": "en",
    "JP": "ja", "KR": "ko", "IN": "en", "BR": "pt",
    "MX": "es", "DE": "de", "FR": "fr", "ES": "es",
    "IT": "it", "ID": "id", "PH": "en", "TH": "th",
}

# Render 인스턴스 메모리에 최근 검색 결과를 보관합니다.
# 재배포나 서버 재시작 시 초기화될 수 있습니다.
LAST_RESULTS = {}


HTML = r"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Global Shorts Finder</title>
<style>
:root {
  color-scheme: dark;
  --bg: #0b1020;
  --panel: #131b2e;
  --panel2: #19243a;
  --text: #f4f7ff;
  --muted: #a8b4cb;
  --line: #2b3954;
  --accent: #70e1c1;
  --blue: #7ea7ff;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: radial-gradient(circle at top right, #17294a, var(--bg) 45%);
  color: var(--text);
  font-family: Arial, "Malgun Gothic", sans-serif;
}
main { max-width: 1250px; margin: auto; padding: 28px 18px 60px; }
h1 { margin: 0 0 8px; font-size: clamp(27px, 4vw, 42px); }
p { line-height: 1.6; }
.subtitle { color: var(--muted); margin-top: 0; }
.panel {
  background: rgba(19, 27, 46, .96);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 20px;
  margin-top: 18px;
}
.formgrid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 15px;
}
.field { display: flex; flex-direction: column; gap: 7px; }
label { font-size: 13px; color: #d5deef; }
input, select {
  width: 100%;
  min-width: 0;
  padding: 12px;
  border-radius: 10px;
  color: var(--text);
  background: #0d1527;
  border: 1px solid #354562;
  font-size: 14px;
}
.checkrow {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 17px;
  color: #d8e2f3;
  font-size: 14px;
  line-height: 1.5;
}
.checkrow input { width: auto; margin-top: 4px; }
.help { color: var(--muted); font-size: 12px; line-height: 1.6; }
button, .btn {
  display: inline-block;
  border: 0;
  border-radius: 10px;
  padding: 12px 17px;
  background: var(--accent);
  color: #071a19;
  font-weight: 800;
  text-decoration: none;
  cursor: pointer;
  font-size: 14px;
}
button:hover, .btn:hover { filter: brightness(1.08); }
.actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.secondary { background: #263854; color: white; }
.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.stat {
  padding: 15px;
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: 13px;
}
.stat strong { display: block; font-size: 24px; margin-top: 7px; }
.stat span { color: var(--muted); font-size: 12px; }
.alert {
  border-radius: 12px;
  padding: 13px 15px;
  background: #35251a;
  border: 1px solid #81542f;
  color: #ffe0bc;
  line-height: 1.6;
  margin-top: 16px;
}
.error {
  background: #3b2028;
  border-color: #9d4456;
  color: #ffd8df;
}
.result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.results {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 15px;
  margin-top: 16px;
}
.video {
  background: #10192b;
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  min-width: 0;
}
.thumb {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  background: #202c40;
}
.video-body { padding: 13px; }
.video h3 { font-size: 15px; line-height: 1.5; margin: 0 0 8px; }
.video h3 a { color: var(--text); text-decoration: none; }
.video h3 a:hover { color: var(--accent); }
.meta { color: var(--muted); font-size: 12px; line-height: 1.8; }
.views { color: var(--accent); font-size: 17px; font-weight: 800; margin: 9px 0 4px; }
.tag {
  display: inline-block;
  font-size: 11px;
  padding: 4px 7px;
  border-radius: 6px;
  background: #203c3b;
  color: #9df5df;
  margin-top: 8px;
}
.empty { color: var(--muted); text-align: center; padding: 32px 10px; }
footer { color: var(--muted); font-size: 12px; margin-top: 22px; line-height: 1.7; }
@media (max-width: 850px) {
  .formgrid, .results { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  main { padding: 20px 12px 40px; }
  .panel { padding: 14px; }
  .formgrid, .results, .stats { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<main>
  <h1>🌎 Global Shorts Finder</h1>
  <p class="subtitle">국가별 해외 쇼츠 후보를 찾고 조회수 100만 회 이상인 영상을 확인하세요.</p>

  <section class="panel">
    <form method="get" action="/">
      <div class="formgrid">
        <div class="field">
          <label for="q">검색어</label>
          <input id="q" name="q" value="{{ q }}" placeholder="예: funny animals, street food" required>
        </div>
        <div class="field">
          <label for="country">검색 국가</label>
          <select id="country" name="country">
            {% for code, name in countries.items() %}
            <option value="{{ code }}" {% if code == country %}selected{% endif %}>{{ name }} ({{ code }})</option>
            {% endfor %}
          </select>
        </div>
        <div class="field">
          <label for="days">게시 기간</label>
          <select id="days" name="days">
            <option value="7" {% if days == "7" %}selected{% endif %}>최근 7일</option>
            <option value="30" {% if days == "30" %}selected{% endif %}>최근 30일</option>
            <option value="90" {% if days == "90" %}selected{% endif %}>최근 90일</option>
            <option value="365" {% if days == "365" %}selected{% endif %}>최근 1년</option>
            <option value="0" {% if days == "0" %}selected{% endif %}>전체 기간</option>
          </select>
        </div>
        <div class="field">
          <label for="min_views">최소 조회수</label>
          <select id="min_views" name="min_views">
            <option value="1000000" {% if min_views == "1000000" %}selected{% endif %}>100만 회 이상</option>
            <option value="500000" {% if min_views == "500000" %}selected{% endif %}>50만 회 이상</option>
            <option value="100000" {% if min_views == "100000" %}selected{% endif %}>10만 회 이상</option>
            <option value="0" {% if min_views == "0" %}selected{% endif %}>조회수 제한 없음</option>
          </select>
        </div>
        <div class="field">
          <label for="pages">검색 페이지 수</label>
          <select id="pages" name="pages">
            <option value="1" {% if pages == 1 %}selected{% endif %}>1페이지 · 최대 50개 후보</option>
            <option value="2" {% if pages == 2 %}selected{% endif %}>2페이지 · 최대 100개 후보</option>
            <option value="3" {% if pages == 3 %}selected{% endif %}>3페이지 · 최대 150개 후보</option>
            <option value="5" {% if pages == 5 %}selected{% endif %}>5페이지 · 최대 250개 후보</option>
          </select>
        </div>
        <div class="field">
          <label for="order">검색 정렬</label>
          <select id="order" name="order">
            <option value="relevance" {% if order == "relevance" %}selected{% endif %}>관련성 우선 · 추천</option>
            <option value="date" {% if order == "date" %}selected{% endif %}>최신순</option>
          </select>
        </div>
      </div>

      <label class="checkrow">
        <input type="checkbox" name="strict" value="1" {% if strict %}checked{% endif %}>
        <span>
          <strong>채널 국가 엄격 필터</strong><br>
          채널에 공개된 국가 정보가 선택 국가와 일치하는 영상만 표시합니다.
          <span class="help">국가 정보가 없거나 일치하지 않는 채널은 제외되므로 결과가 크게 줄 수 있습니다.</span>
        </span>
      </label>

      <div class="actions">
        <button type="submit">🔎 쇼츠 검색</button>
        <a class="btn secondary" href="/">초기화</a>
      </div>
      <p class="help">
        페이지를 1개 늘릴 때마다 YouTube 검색 API 사용량이 추가됩니다.
        5페이지 검색은 검색 API 호출을 최대 5회 사용합니다.
      </p>
    </form>
  </section>

  {% if error %}
  <div class="alert error"><strong>검색 오류</strong><br>{{ error }}</div>
  {% endif %}

  {% if searched %}
  <section class="panel">
    <div class="result-head">
      <div>
        <h2 style="margin:0 0 5px;">검색 결과</h2>
        <div class="help">{{ countries.get(country, country) }} · 검색어: {{ q }}</div>
      </div>
      {% if export_id %}
      <a class="btn secondary" href="/export/{{ export_id }}">CSV 다운로드</a>
      {% endif %}
    </div>

    <div class="stats" style="margin-top:16px;">
      <div class="stat"><span>검색 후보 영상</span><strong>{{ candidate_count }}</strong></div>
      <div class="stat"><span>조건에 맞는 영상</span><strong>{{ results|length }}</strong></div>
      <div class="stat"><span>조회수 기준</span><strong>{{ min_views_label }}</strong></div>
    </div>

    {% if strict %}
    <div class="alert">
      엄격 필터가 켜져 있습니다. YouTube 채널의 공개 국가 정보가 없는 경우에도 해당 채널이 제외됩니다.
    </div>
    {% endif %}

    {% if results %}
    <div class="results">
      {% for v in results %}
      <article class="video">
        <a href="{{ v.url }}" target="_blank" rel="noopener noreferrer">
          <img class="thumb" src="{{ v.thumbnail }}" alt="영상 썸네일" loading="lazy">
        </a>
        <div class="video-body">
          <h3><a href="{{ v.url }}" target="_blank" rel="noopener noreferrer">{{ v.title }}</a></h3>
          <div class="meta">
            채널: {{ v.channel }}<br>
            게시일: {{ v.published }}<br>
            길이: {{ v.duration_label }}<br>
            채널 국가: {{ v.channel_country_label }}
          </div>
          <div class="views">{{ "{:,}".format(v.views) }}회 조회</div>
          <span class="tag">쇼츠 후보 · 3분 이하</span>
        </div>
      </article>
      {% endfor %}
    </div>
    {% else %}
    <div class="empty">
      조건에 맞는 영상이 없습니다.<br>
      검색 페이지를 늘리거나 게시 기간을 넓히고, 필요하면 조회수 기준을 낮춰 보세요.
    </div>
    {% endif %}
  </section>
  {% endif %}

  <footer>
    안내: YouTube 검색 API가 반환한 후보 중 영상 길이, 조회수, 선택한 필터 조건으로 결과를 구성합니다.
    YouTube의 국가 검색은 해당 국가에서 시청 가능한 영상을 중심으로 하며, 영상 제작자의 국적이나 실제 촬영 국가를 보장하지 않습니다.
    쇼츠 여부는 길이 기준으로 추정하므로 일반 영상이 포함될 수 있습니다.
  </footer>
</main>
</body>
</html>
"""


def parse_duration_seconds(duration):
    """ISO 8601 형식의 영상 길이를 초 단위로 변환합니다."""
    match = re.fullmatch(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration or ""
    )
    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def format_duration(seconds):
    minutes, seconds = divmod(seconds, 60)
    if minutes:
        return f"{minutes}:{seconds:02d}"
    return f"0:{seconds:02d}"


def format_published(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return value or "정보 없음"


def get_youtube_client():
    if not API_KEY:
        raise RuntimeError(
            "Render 환경 변수 YOUTUBE_API_KEY가 설정되지 않았습니다. "
            "Render 대시보드의 Environment 메뉴에서 API 키를 확인해 주세요."
        )

    return build(
        "youtube",
        "v3",
        developerKey=API_KEY,
        cache_discovery=False
    )


def search_video_candidates(youtube, query, country, days, pages, order):
    """검색 API를 여러 페이지 호출해 중복 없는 영상 ID 목록을 수집합니다."""
    published_after = None
    if days > 0:
        published_after = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).isoformat(timespec="seconds").replace("+00:00", "Z")

    found = {}
    page_token = None

    for _ in range(pages):
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "regionCode": country,
            "relevanceLanguage": LANGUAGES.get(country, "en"),
            "videoDuration": "short",
            "maxResults": 50,
            "order": order,
        }

        if published_after:
            params["publishedAfter"] = published_after

        if page_token:
            params["pageToken"] = page_token

        response = youtube.search().list(**params).execute()

        for item in response.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if video_id and video_id not in found:
                found[video_id] = item.get("snippet", {})

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return found


def fetch_video_details(youtube, candidate_snippets):
    """후보 영상의 실제 조회수, 길이, 썸네일 정보를 가져옵니다."""
    video_ids = list(candidate_snippets.keys())
    videos = {}

    for start in range(0, len(video_ids), 50):
        batch = video_ids[start:start + 50]
        response = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(batch),
            maxResults=50
        ).execute()

        for item in response.get("items", []):
            videos[item["id"]] = item

    return videos


def fetch_channel_countries(youtube, videos):
    """채널에 공개된 국가 정보를 조회합니다."""
    channel_ids = list({
        item.get("snippet", {}).get("channelId")
        for item in videos.values()
        if item.get("snippet", {}).get("channelId")
    })

    countries = {}

    for start in range(0, len(channel_ids), 50):
        batch = channel_ids[start:start + 50]
        response = youtube.channels().list(
            part="snippet",
            id=",".join(batch),
            maxResults=50
        ).execute()

        for item in response.get("items", []):
            countries[item["id"]] = item.get("snippet", {}).get("country", "")

    return countries


def build_results(youtube, candidates, country, min_views, strict):
    videos = fetch_video_details(youtube, candidates)
    channel_countries = fetch_channel_countries(youtube, videos)
    results = []

    for video_id, item in videos.items():
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content = item.get("contentDetails", {})

        try:
            views = int(statistics.get("viewCount", 0))
        except (TypeError, ValueError):
            views = 0

        duration_seconds = parse_duration_seconds(content.get("duration", ""))

        # 쇼츠 후보를 최대 3분 길이로 제한합니다.
        if duration_seconds <= 0 or duration_seconds > 180:
            continue

        if views < min_views:
            continue

        channel_id = snippet.get("channelId", "")
        channel_country = channel_countries.get(channel_id, "")

        if strict and channel_country != country:
            continue

        thumbnails = snippet.get("thumbnails", {})
        thumbnail = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
            or ""
        )

        results.append({
            "video_id": video_id,
            "title": snippet.get("title", "제목 없음"),
            "channel": snippet.get("channelTitle", "채널 정보 없음"),
            "published": format_published(snippet.get("publishedAt", "")),
            "views": views,
            "duration_seconds": duration_seconds,
            "duration_label": format_duration(duration_seconds),
            "thumbnail": thumbnail,
            "url": f"https://www.youtube.com/shorts/{video_id}",
            "channel_country": channel_country,
            "channel_country_label": COUNTRIES.get(
                channel_country,
                channel_country or "공개 정보 없음"
            ),
        })

    results.sort(key=lambda item: item["views"], reverse=True)
    return results


def render_page(**overrides):
    defaults = {
        "q": "",
        "country": "US",
        "days": "30",
        "min_views": "1000000",
        "pages": 3,
        "order": "relevance",
        "strict": False,
        "searched": False,
        "results": [],
        "candidate_count": 0,
        "error": "",
        "export_id": "",
    }
    defaults.update(overrides)

    min_views = int(defaults["min_views"])
    if min_views >= 1_000_000:
        defaults["min_views_label"] = f"{min_views // 1_000_000}백만 회 이상"
    elif min_views >= 1_000:
        defaults["min_views_label"] = f"{min_views // 1_000}천 회 이상"
    else:
        defaults["min_views_label"] = "제한 없음"

    return render_template_string(
        HTML,
        countries=COUNTRIES,
        **defaults
    )


@app.route("/", methods=["GET"])
def index():
    q = request.args.get("q", "").strip()
    country = request.args.get("country", "US").upper()
    days_raw = request.args.get("days", "30")
    min_views_raw = request.args.get("min_views", "1000000")
    pages_raw = request.args.get("pages", "3")
    order = request.args.get("order", "relevance")
    strict = request.args.get("strict") == "1"

    if country not in COUNTRIES:
        country = "US"

    try:
        days = int(days_raw)
        if days not in (0, 7, 30, 90, 365):
            days = 30
    except ValueError:
        days = 30

    try:
        min_views = int(min_views_raw)
        if min_views not in (0, 100000, 500000, 1000000):
            min_views = 1000000
    except ValueError:
        min_views = 1000000

    try:
        pages = int(pages_raw)
        if pages not in (1, 2, 3, 5):
            pages = 3
    except ValueError:
        pages = 3

    if order not in ("relevance", "date"):
        order = "relevance"

    if not q:
        return render_page(
            q=q, country=country, days=str(days),
            min_views=str(min_views), pages=pages,
            order=order, strict=strict
        )

    if len(q) > 200:
        return render_page(
            q=q[:200], country=country, days=str(days),
            min_views=str(min_views), pages=pages,
            order=order, strict=strict,
            error="검색어는 200자 이내로 입력해 주세요."
        )

    try:
        youtube = get_youtube_client()

        candidates = search_video_candidates(
            youtube=youtube,
            query=q,
            country=country,
            days=days,
            pages=pages,
            order=order
        )

        results = build_results(
            youtube=youtube,
            candidates=candidates,
            country=country,
            min_views=min_views,
            strict=strict
        )

        export_id = uuid.uuid4().hex
        LAST_RESULTS[export_id] = results

        # 메모리 사용량이 커지지 않도록 최근 검색 20개만 유지합니다.
        while len(LAST_RESULTS) > 20:
            LAST_RESULTS.pop(next(iter(LAST_RESULTS)))

        return render_page(
            q=q,
            country=country,
            days=str(days),
            min_views=str(min_views),
            pages=pages,
            order=order,
            strict=strict,
            searched=True,
            results=results,
            candidate_count=len(candidates),
            export_id=export_id
        )

    except RuntimeError as exc:
        return render_page(
            q=q, country=country, days=str(days),
            min_views=str(min_views), pages=pages,
            order=order, strict=strict,
            error=str(exc)
        )
    except HttpError as exc:
        status = getattr(exc.resp, "status", "알 수 없음")
        if status == 403:
            message = (
                "YouTube API 요청이 거부되었습니다. API 키, YouTube Data API v3 활성화 여부, "
                "할당량 초과 여부를 확인해 주세요."
            )
        elif status == 400:
            message = "YouTube 검색 요청이 올바르지 않습니다. 검색어를 바꿔 다시 시도해 주세요."
        else:
            message = f"YouTube API 오류가 발생했습니다. HTTP 상태 코드: {status}"
        return render_page(
            q=q, country=country, days=str(days),
            min_views=str(min_views), pages=pages,
            order=order, strict=strict, error=message
        )
    except Exception as exc:
        app.logger.exception("검색 처리 중 오류 발생")
        return render_page(
            q=q, country=country, days=str(days),
            min_views=str(min_views), pages=pages,
            order=order, strict=strict,
            error=f"검색 중 오류가 발생했습니다: {exc}"
        )


@app.route("/export/<export_id>", methods=["GET"])
def export_csv(export_id):
    results = LAST_RESULTS.get(export_id)

    if results is None:
        return (
            "검색 결과가 만료되었거나 서버가 재시작되었습니다. "
            "사이트에서 다시 검색한 뒤 CSV를 다운로드해 주세요.",
            404
        )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "제목", "채널", "조회수", "게시일",
        "영상 길이", "채널 국가", "영상 URL"
    ])

    for item in results:
        writer.writerow([
            item["title"],
            item["channel"],
            item["views"],
            item["published"],
            item["duration_label"],
            item["channel_country_label"],
            item["url"],
        ])

    # Excel에서 한글이 깨지지 않도록 UTF-8 BOM을 추가합니다.
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        'attachment; filename="global_shorts_results.csv"'
    )
    return response


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
