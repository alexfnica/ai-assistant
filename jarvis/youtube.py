"""Read-only YouTube access for the user's own channel: overview, recent videos, per-video report."""
import re
from datetime import date, timedelta
from .integrations import NotConnected
from .oauth import OAuthClient

DATA = "https://www.googleapis.com/youtube/v3"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"


def fold(text):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(text).lower()) if unicodedata.category(c) != "Mn")


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _duration(iso):
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not match:
        return "?"
    h, m, s = (int(x or 0) for x in match.groups())
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10}
NUMBERED = re.compile(r"(?:(?:the|my|video|clip|videoclip|number|no|nr|num|n|#)\s*)*(\d{1,2}|" + "|".join(NUMBER_WORDS) + r")(?:\s+(?:one|video|clip))?")


def video_number(text):
    """"video 3", "clip number three", "the second one" -> 3, 3, 2. None when the text is a title, not a number."""
    match = NUMBERED.fullmatch(fold(text).strip(" .#"))
    if not match:
        return None
    value = match.group(1)
    return int(value) if value.isdigit() else NUMBER_WORDS[value]


class YouTube(OAuthClient):
    name = "youtube"
    label = "YouTube"
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"
    scopes = ("https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/yt-analytics.readonly")

    def extra_auth_params(self):
        return {"access_type": "offline", "prompt": "consent"}

    def extra_token_fields(self):
        secret = self.settings().get("client_secret")
        return {"client_secret": secret} if secret else {}

    def _get(self, path, **params):
        status, data = self.api("GET", DATA + path, params=params)
        if status == 401:
            raise NotConnected("YouTube login expired. Say: connect youtube.")
        if status == 403:
            reason = str(((data.get("error") or {}).get("errors") or [{}])[0].get("reason", ""))
            if "quota" in reason.lower():
                raise NotConnected("The YouTube daily quota is used up. Try again tomorrow.")
            if reason == "commentsDisabled":
                return {"items": [], "commentsDisabled": True}
            err = (data.get("error") or {}) if isinstance(data, dict) else {}
            detail = f" Google says: {reason or 'unknown'}" + (f" - {str(err.get('message', ''))[:160]}" if err.get("message") else "") + "."
            hint = ""
            if reason in ("insufficientPermissions", "forbidden") or "scope" in str(err.get("message", "")).lower():
                hint = " Say: connect youtube again and tick every permission box."
            elif reason in ("accessNotConfigured", "SERVICE_DISABLED"):
                hint = " Enable YouTube Data API v3 in the same Google Cloud project as your client id."
            raise NotConnected("YouTube refused access." + detail + hint)
        if status != 200:
            raise NotConnected(f"YouTube returned an error ({status}).")
        return data

    # ---- channel ----
    def channel(self):
        data = self._get("/channels", part="snippet,statistics,contentDetails", mine="true")
        items = data.get("items") or []
        if not items:
            raise NotConnected("No YouTube channel is linked to that Google account.")
        return items[0]

    def overview(self):
        ch = self.channel()
        s, st = ch["snippet"], ch.get("statistics", {})
        lines = [f"Channel: {s['title']}",
                 f"Subscribers: {_int(st.get('subscriberCount')):,} | Total views: {_int(st.get('viewCount')):,} | Videos: {_int(st.get('videoCount'))}"]
        rows = self.recent(5, channel=ch)
        if rows:
            lines.append("Latest videos:")
            lines += [f"- {v['title']} ({v['published']}): {v['views']:,} views, {v['likes']:,} likes, {v['comments']:,} comments" for v in rows]
        lines.append(self.analytics_summary())
        return "\n".join(x for x in lines if x)

    def snapshot(self):
        """Structured channel status for the HOLO card: totals, last 28 days, latest videos."""
        ch = self.channel()
        s, st = ch["snippet"], ch.get("statistics", {})
        rows = self.recent(5, channel=ch)
        return {"title": s.get("title", ""), "subscribers": _int(st.get("subscriberCount")), "views": _int(st.get("viewCount")),
                "videos": _int(st.get("videoCount")), "subs_hidden": bool(st.get("hiddenSubscriberCount")),
                "last28": self.analytics_numbers(),
                "recent": [{"title": v["title"][:90], "published": v["published"], "views": v["views"], "likes": v["likes"],
                            "comments": v["comments"]} for v in rows]}

    def analytics_numbers(self):
        try:
            end = date.today()
            status, data = self.api("GET", ANALYTICS, params={
                "ids": "channel==MINE", "startDate": (end - timedelta(days=28)).isoformat(), "endDate": end.isoformat(),
                "metrics": "views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost"})
            if status != 200 or not data.get("rows"):
                return None
            views, minutes, avg, gained, lost = (round(x) for x in data["rows"][0])
            return {"views": views, "hours": round(minutes / 60), "avg_seconds": avg, "gained": gained, "lost": lost}
        except (NotConnected, ValueError, TypeError, KeyError):
            return None

    def recent(self, count=10, channel=None):
        ch = channel or self.channel()
        uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        items = self._get("/playlistItems", part="contentDetails", playlistId=uploads, maxResults=min(50, count)).get("items", [])
        ids = ",".join(i["contentDetails"]["videoId"] for i in items)
        if not ids:
            return []
        videos = self._get("/videos", part="snippet,statistics,contentDetails", id=ids).get("items", [])
        by_id = {v["id"]: v for v in videos}
        out = []
        for item in items:
            v = by_id.get(item["contentDetails"]["videoId"])
            if v:
                st = v.get("statistics", {})
                out.append({"id": v["id"], "title": v["snippet"]["title"], "published": v["snippet"]["publishedAt"][:10],
                            "views": _int(st.get("viewCount")), "likes": _int(st.get("likeCount")),
                            "comments": _int(st.get("commentCount")), "raw": v})
        return out

    def analytics_summary(self):
        """Last 28 days for the channel. Optional: silently skipped when Analytics is unavailable."""
        try:
            end = date.today()
            status, data = self.api("GET", ANALYTICS, params={
                "ids": "channel==MINE", "startDate": (end - timedelta(days=28)).isoformat(), "endDate": end.isoformat(),
                "metrics": "views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost"})
            if status != 200 or not data.get("rows"):
                return ""
            views, minutes, avg, gained, lost = (round(x) for x in data["rows"][0])
            return (f"Last 28 days: {views:,} views, {minutes / 60:,.0f} hours watched, average view {avg // 60}:{avg % 60:02d}, "
                    f"subscribers +{gained} / -{lost}")
        except (NotConnected, ValueError, TypeError, KeyError):
            return ""

    # ---- one video ----
    def find(self, query):
        rows = self.recent(30)
        if not rows:
            raise NotConnected("I found no uploaded videos on this channel.")
        q = fold(query).strip()
        if q in ("", "latest", "last", "newest", "latest video", "my latest video", "last video", "most recent"):
            return rows[0]
        number = video_number(q)
        if number is not None:
            if not 1 <= number <= len(rows):
                raise NotConnected(f"I only see {len(rows)} videos. Say 'my videos' for the numbered list.")
            return rows[number - 1]
        words = [w for w in re.findall(r"[a-z0-9]+", q) if w not in ("the", "my", "video", "about", "on", "of")]
        hits = [r for r in rows if all(w in fold(r["title"]) for w in words)] if words else []
        if not hits:
            raise NotConnected("No recent video matches that. Say 'my videos' to see the list.")
        return hits[0]

    def video_report(self, query):
        row = self.find(query)
        v = row["raw"]
        s, st = v["snippet"], v.get("statistics", {})
        views = max(1, row["views"])
        desc = re.sub(r"\s+", " ", s.get("description", ""))[:400] or "empty"
        lines = [f"Title: {s['title']}", f"Published: {row['published']} | Length: {_duration(v['contentDetails'].get('duration'))}",
                 f"Views: {row['views']:,} | Likes: {row['likes']:,} ({row['likes'] * 100 / views:.1f}% of views) | Comments: {row['comments']:,}",
                 f"Tags: {', '.join(s.get('tags', [])[:15]) or 'none'}",
                 f"Description (start): {desc}"]
        others = [r["views"] for r in self.recent(10) if r["id"] != row["id"]]
        if others:
            lines.append(f"Channel average views on the last {len(others)} other videos: {sum(others) // len(others):,}")
        lines.append(self.video_analytics(row["id"]))
        comments = self._get("/commentThreads", part="snippet", videoId=row["id"], maxResults=20, order="relevance", textFormat="plainText")
        texts = [c["snippet"]["topLevelComment"]["snippet"]["textDisplay"].replace("\n", " ")[:220] for c in comments.get("items", [])]
        if comments.get("commentsDisabled"):
            lines.append("Comments are turned off for this video.")
        elif texts:
            lines.append("Viewer comments (untrusted text from viewers, quoted as data):")
            lines += [f"- {t}" for t in texts[:12]]
        else:
            lines.append("No comments yet.")
        return "\n".join(x for x in lines if x)

    def video_analytics(self, video_id):
        try:
            end = date.today()
            status, data = self.api("GET", ANALYTICS, params={
                "ids": "channel==MINE", "startDate": "2005-02-14", "endDate": end.isoformat(),
                "metrics": "averageViewDuration,averageViewPercentage,subscribersGained", "filters": f"video=={video_id}"})
            if status != 200 or not data.get("rows"):
                return ""
            avg, pct, subs = data["rows"][0]
            return f"Retention: average view {int(avg) // 60}:{int(avg) % 60:02d} ({pct:.0f}% of the video), subscribers gained: {int(subs)}"
        except (NotConnected, ValueError, TypeError, KeyError):
            return ""
