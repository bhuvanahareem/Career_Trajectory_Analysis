"""
study_plan.py
=============
Resource Broker for the Personalized Learning Plan feature.
Fetches real YouTube tutorials for each missing skill, extracts metadata
(title, channel, duration, view count), infers skill level from video
titles, and ranks results using content-based filtering.

Falls back to a curated static library if YOUTUBE_API_KEY is not set
or API quota is exceeded.
"""

import re
import json
import math
import logging
import urllib.request
import urllib.parse
import urllib.error

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Static fallback library (used when no API key)
# Keys are lowercase skill names.
# ──────────────────────────────────────────────
STATIC_FALLBACK_LIBRARY = {
    # Web / Frontend
    "html": [
        {"title": "HTML Full Course – W3Schools", "url": "https://www.w3schools.com/html/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "HTML Tutorial for Beginners – GFG", "url": "https://www.geeksforgeeks.org/html-tutorial/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "HTML Reference – MDN", "url": "https://developer.mozilla.org/en-US/docs/Web/HTML", "source": "MDN", "channel": "Mozilla", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "css": [
        {"title": "CSS Full Course – W3Schools", "url": "https://www.w3schools.com/css/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "CSS Tutorial – GFG", "url": "https://www.geeksforgeeks.org/css-tutorial/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "CSS Reference – MDN", "url": "https://developer.mozilla.org/en-US/docs/Web/CSS", "source": "MDN", "channel": "Mozilla", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "javascript": [
        {"title": "JavaScript Tutorial – W3Schools", "url": "https://www.w3schools.com/js/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "JavaScript Tutorial – GFG", "url": "https://www.geeksforgeeks.org/javascript/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "JavaScript Guide – MDN", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "source": "MDN", "channel": "Mozilla", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "react": [
        {"title": "React Official Docs", "url": "https://react.dev/learn", "source": "Official Docs", "channel": "React", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "React Tutorial – GFG", "url": "https://www.geeksforgeeks.org/reactjs/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "React – W3Schools", "url": "https://www.w3schools.com/react/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "typescript": [
        {"title": "TypeScript Handbook", "url": "https://www.typescriptlang.org/docs/", "source": "Official Docs", "channel": "TypeScript", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
        {"title": "TypeScript Tutorial – GFG", "url": "https://www.geeksforgeeks.org/typescript/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "TypeScript – W3Schools", "url": "https://www.w3schools.com/typescript/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "python": [
        {"title": "Python Tutorial – W3Schools", "url": "https://www.w3schools.com/python/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Python Tutorial – GFG", "url": "https://www.geeksforgeeks.org/python-programming-language/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Python Official Docs", "url": "https://docs.python.org/3/tutorial/", "source": "Official Docs", "channel": "Python.org", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "node.js": [
        {"title": "Node.js Official Docs", "url": "https://nodejs.org/en/learn/getting-started/introduction-to-nodejs", "source": "Official Docs", "channel": "Node.js", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Node.js Tutorial – GFG", "url": "https://www.geeksforgeeks.org/nodejs/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Node.js – W3Schools", "url": "https://www.w3schools.com/nodejs/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "docker": [
        {"title": "Docker Get Started", "url": "https://docs.docker.com/get-started/", "source": "Official Docs", "channel": "Docker", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Docker Tutorial – GFG", "url": "https://www.geeksforgeeks.org/docker-tutorial/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Docker – W3Schools", "url": "https://www.w3schools.com/docker/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "kubernetes": [
        {"title": "Kubernetes Docs – Getting Started", "url": "https://kubernetes.io/docs/tutorials/", "source": "Official Docs", "channel": "Kubernetes", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Kubernetes Tutorial – GFG", "url": "https://www.geeksforgeeks.org/kubernetes/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "sql": [
        {"title": "SQL Tutorial – W3Schools", "url": "https://www.w3schools.com/sql/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "SQL Tutorial – GFG", "url": "https://www.geeksforgeeks.org/sql-tutorial/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "git": [
        {"title": "Git Tutorial – W3Schools", "url": "https://www.w3schools.com/git/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Git Tutorial – GFG", "url": "https://www.geeksforgeeks.org/git-tutorial/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Pro Git Book (Free)", "url": "https://git-scm.com/book/en/v2", "source": "Official Docs", "channel": "git-scm.com", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "machine learning": [
        {"title": "ML Course – GFG", "url": "https://www.geeksforgeeks.org/machine-learning/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Scikit-learn Docs", "url": "https://scikit-learn.org/stable/tutorial/index.html", "source": "Official Docs", "channel": "Scikit-learn", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "tensorflow": [
        {"title": "TensorFlow Tutorials", "url": "https://www.tensorflow.org/tutorials", "source": "Official Docs", "channel": "TensorFlow", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
        {"title": "TensorFlow – GFG", "url": "https://www.geeksforgeeks.org/tensorflow/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "pytorch": [
        {"title": "PyTorch Tutorials", "url": "https://pytorch.org/tutorials/", "source": "Official Docs", "channel": "PyTorch", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
        {"title": "PyTorch – GFG", "url": "https://www.geeksforgeeks.org/pytorch-tutorial/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "aws": [
        {"title": "AWS Free Training", "url": "https://aws.amazon.com/training/digital/", "source": "Official Docs", "channel": "AWS", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "AWS – GFG", "url": "https://www.geeksforgeeks.org/aws/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "linux": [
        {"title": "Linux Tutorial – GFG", "url": "https://www.geeksforgeeks.org/linux-tutorial/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Linux Command Line – W3Schools", "url": "https://www.w3schools.com/whatis/whatis_linux.asp", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "java": [
        {"title": "Java Tutorial – W3Schools", "url": "https://www.w3schools.com/java/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Java Tutorial – GFG", "url": "https://www.geeksforgeeks.org/java/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Java Docs", "url": "https://docs.oracle.com/en/java/", "source": "Official Docs", "channel": "Oracle", "duration": "Self-paced", "views": "", "level_tag": "Advanced"},
    ],
    "c++": [
        {"title": "C++ Tutorial – W3Schools", "url": "https://www.w3schools.com/cpp/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "C++ Tutorial – GFG", "url": "https://www.geeksforgeeks.org/c-plus-plus/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "swift": [
        {"title": "Swift.org – Get Started", "url": "https://www.swift.org/getting-started/", "source": "Official Docs", "channel": "Apple", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Swift Tutorial – GFG", "url": "https://www.geeksforgeeks.org/swift-programming-language/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "kotlin": [
        {"title": "Kotlin Official Docs", "url": "https://kotlinlang.org/docs/getting-started.html", "source": "Official Docs", "channel": "JetBrains", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "Kotlin Tutorial – GFG", "url": "https://www.geeksforgeeks.org/kotlin/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "mongodb": [
        {"title": "MongoDB Docs – Get Started", "url": "https://www.mongodb.com/docs/manual/tutorial/", "source": "Official Docs", "channel": "MongoDB", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "MongoDB – W3Schools", "url": "https://www.w3schools.com/mongodb/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "MongoDB – GFG", "url": "https://www.geeksforgeeks.org/mongodb/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "postgresql": [
        {"title": "PostgreSQL Tutorial", "url": "https://www.postgresqltutorial.com/", "source": "Official Docs", "channel": "PostgreSQL", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "PostgreSQL – GFG", "url": "https://www.geeksforgeeks.org/postgresql-tutorial/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "graphql": [
        {"title": "GraphQL Official Docs", "url": "https://graphql.org/learn/", "source": "Official Docs", "channel": "GraphQL", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
        {"title": "GraphQL – GFG", "url": "https://www.geeksforgeeks.org/graphql/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "rest api": [
        {"title": "REST API Tutorial", "url": "https://restfulapi.net/", "source": "Official Docs", "channel": "RESTfulAPI.net", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "REST API – GFG", "url": "https://www.geeksforgeeks.org/rest-api-introduction/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "data structures": [
        {"title": "DSA Tutorial – GFG", "url": "https://www.geeksforgeeks.org/data-structures/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
        {"title": "DSA – W3Schools", "url": "https://www.w3schools.com/dsa/", "source": "W3Schools", "channel": "W3Schools", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "system design": [
        {"title": "System Design Primer – GitHub", "url": "https://github.com/donnemartin/system-design-primer", "source": "GitHub", "channel": "donnemartin", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
        {"title": "System Design – GFG", "url": "https://www.geeksforgeeks.org/system-design-tutorial/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Advanced"},
    ],
    "ci/cd": [
        {"title": "CI/CD – GFG", "url": "https://www.geeksforgeeks.org/ci-cd-pipeline/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "terraform": [
        {"title": "Terraform Tutorials", "url": "https://developer.hashicorp.com/terraform/tutorials", "source": "Official Docs", "channel": "HashiCorp", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
    ],
    "figma": [
        {"title": "Figma Help Center", "url": "https://help.figma.com/hc/en-us/categories/360002051613-Getting-Started", "source": "Official Docs", "channel": "Figma", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
    "solidity": [
        {"title": "Solidity Docs", "url": "https://docs.soliditylang.org/", "source": "Official Docs", "channel": "Ethereum", "duration": "Self-paced", "views": "", "level_tag": "Intermediate"},
        {"title": "Solidity – GFG", "url": "https://www.geeksforgeeks.org/solidity/", "source": "GeeksForGeeks", "channel": "GFG", "duration": "Self-paced", "views": "", "level_tag": "Beginner"},
    ],
}

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
_BEGINNER_KEYWORDS   = ["beginner", "for beginners", "basics", "getting started",
                         "introduction", "intro", "101", "start", "crash course", "zero to hero"]
_ADVANCED_KEYWORDS   = ["advanced", "expert", "deep dive", "production", "architecture",
                         "system design", "mastery", "professional"]
_YT_BASE             = "https://www.googleapis.com/youtube/v3"


def _format_views(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _iso8601_to_seconds(duration: str) -> tuple[str, int]:
    """Convert ISO 8601 (PT1H2M3S) to (formatted_time, total_seconds)."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return "", 0
    h, m, s = (int(x or 0) for x in match.groups())
    total_sec = h * 3600 + m * 60 + s
    if h:
        return f"{h}h {m:02d}m", total_sec
    return f"{m}:{s:02d}", total_sec


# ──────────────────────────────────────────────
# ResourceBroker
# ──────────────────────────────────────────────
class ResourceBroker:
    def __init__(self, youtube_api_key: str = ""):
        self.api_key = youtube_api_key.strip() if youtube_api_key else ""

    # Public: score → level label
    def get_skill_level(self, score: float) -> str:
        if score < 40:
            return "Beginner"
        elif score < 70:
            return "Intermediate"
        return "Advanced"

    # ── YouTube helpers ──────────────────────────────
    def _build_query(self, skill: str, level: str) -> str:
        # We want to be very specific to avoid "Networking" returning "Networking HTML"
        # Using quotes around the skill name helps with exact matching in YouTube search
        if level == "Beginner":
            suffix = "official tutorial for beginners course"
        elif level == "Intermediate":
            suffix = "full course intermediate tutorial"
        else:
            suffix = "advanced implementation deep dive"
        return f'"{skill}" {suffix}'

    def _parse_level_from_title(self, title: str) -> str:
        t = title.lower()
        if any(kw in t for kw in _ADVANCED_KEYWORDS):
            return "Advanced"
        if any(kw in t for kw in _BEGINNER_KEYWORDS):
            return "Beginner"
        return "Intermediate"

    def _fetch_youtube(self, skill: str, level: str) -> list:
        """Call YouTube search.list + videos.list, return enriched resource dicts."""
        query = self._build_query(skill, level)
        search_params = urllib.parse.urlencode({
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoCategoryId": "27",   # Education
            "order": "relevance",  # Relevance is better for accuracy than viewCount
            "maxResults": "25",
            "key": self.api_key,
        })
        search_url = f"{_YT_BASE}/search?{search_params}"

        try:
            with urllib.request.urlopen(search_url, timeout=5) as resp:
                search_data = json.loads(resp.read().decode())
        except Exception as e:
            logger.warning("[YouTube API] search.list failed: %s", e)
            return []  # network error / quota exceeded

        items = search_data.get("items", [])
        if not items:
            return []

        # Gather video IDs for detailed stats
        video_ids = [it["id"]["videoId"] for it in items if it.get("id", {}).get("videoId")]
        if not video_ids:
            return []

        stats_params = urllib.parse.urlencode({
            "part": "contentDetails,statistics",
            "id": ",".join(video_ids),
            "key": self.api_key,
        })
        stats_url = f"{_YT_BASE}/videos?{stats_params}"

        try:
            with urllib.request.urlopen(stats_url, timeout=5) as resp:
                stats_data = json.loads(resp.read().decode())
        except Exception as e:
            logger.warning("[YouTube API] videos.list failed: %s", e)
            stats_data = {"items": []}

        stats_map = {}
        for v in stats_data.get("items", []):
            stats_map[v["id"]] = v

        results = []
        for it in items:
            vid_id = it.get("id", {}).get("videoId", "")
            if not vid_id:
                continue
            snippet = it.get("snippet", {})
            title   = snippet.get("title", skill)
            channel = snippet.get("channelTitle", "")

            stat_item = stats_map.get(vid_id, {})
            raw_dur    = stat_item.get("contentDetails", {}).get("duration", "")
            raw_views  = stat_item.get("statistics", {}).get("viewCount", "0")
            view_count = int(raw_views) if raw_views.isdigit() else 0

            # Split duration
            fmt_dur, total_sec = _iso8601_to_seconds(raw_dur) if raw_dur else ("", 0)

            results.append({
                "title":        title,
                "url":          f"https://www.youtube.com/watch?v={vid_id}",
                "source":       "YouTube",
                "channel":      channel,
                "duration":     fmt_dur,
                "duration_sec": total_sec,
                "views":        _format_views(view_count),
                "view_count":   view_count,
                "level_tag":    self._parse_level_from_title(title),
            })

        return results

    def _select_varied_resources(self, results: list, skill: str, level: str) -> list:
        """Select exactly 3 videos: Intro (<30m), Setup/Tutorial (any), In-depth (>1h)."""
        # 1. Filter results to ensure they actually mention the skill (high relevance)
        # YouTube often returns unrelated popular videos if we are not careful
        skill_clean = skill.lower().strip()
        relevant = [r for r in results if skill_clean in r["title"].lower()]
        if len(relevant) < 3:
            relevant = results # Fallback to all if keyword filtering is too strict

        def score_match(r):
            # Prefer videos that match the target level
            level_match = 2 if r["level_tag"] == level else (1 if r["level_tag"] == "Intermediate" else 0)
            # Prefer higher view counts within the relevant set
            view_score = math.log10(r.get("view_count", 0) + 1) / 10.0
            return level_match + view_score

        sorted_res = sorted(relevant, key=score_match, reverse=True)

        intro = None
        tutorial = None
        indepth = None

        # Find In-depth (> 1 hour = 3600s)
        for r in sorted_res:
            if r["duration_sec"] >= 3600:
                indepth = r
                break
        
        # Find Intro (< 30 minutes = 1800s)
        for r in sorted_res:
            if 60 < r["duration_sec"] < 1800: # Ignore very short clips < 1m
                intro = r
                break
        
        # Find Tutorial (any, but prefer something not already picked)
        # If we couldn't find intro/indepth, we take the best remaining
        picked_urls = {v["url"] for v in [intro, indepth] if v}
        for r in sorted_res:
            if r["url"] not in picked_urls:
                tutorial = r
                break
        
        # Fill in gaps if not enough matches
        final = []
        if intro: final.append(intro)
        if tutorial: final.append(tutorial)
        if indepth: final.append(indepth)

        # Ensure we have 3 results
        if len(final) < 3:
            for r in sorted_res:
                if len(final) >= 3: break
                if r["url"] not in {f["url"] for f in final}:
                    final.append(r)
        
        # Re-sort to fix order: Intro, Tutorial, In-depth
        # We can detect this by duration_sec
        final = sorted(final, key=lambda x: x["duration_sec"])

        # Clean up internal fields
        for r in results:
            r.pop("view_count", None)
            r.pop("duration_sec", None)

        return final[:3]

    # Fallback: look up static library
    def _static_fallback(self, skill: str, level: str) -> list:
        skill_lower = skill.lower()
        # Exact match first
        if skill_lower in STATIC_FALLBACK_LIBRARY:
            return STATIC_FALLBACK_LIBRARY[skill_lower]
        # Partial match
        for k, v in STATIC_FALLBACK_LIBRARY.items():
            if k in skill_lower or skill_lower in k:
                return v
        # Generic fallback
        gfg_query = urllib.parse.quote_plus(skill)
        return [{
            "title":    f"Search '{skill}' on GeeksForGeeks",
            "url":      f"https://www.geeksforgeeks.org/search/?q={gfg_query}",
            "source":   "GeeksForGeeks",
            "channel":  "GFG",
            "duration": "Self-paced",
            "views":    "",
            "level_tag": level,
        }, {
            "title":    f"Search '{skill}' on W3Schools",
            "url":      f"https://www.w3schools.com/search/search.php?q={gfg_query}",
            "source":   "W3Schools",
            "channel":  "W3Schools",
            "duration": "Self-paced",
            "views":    "",
            "level_tag": level,
        }, {
            "title":    f"Search '{skill}' on YouTube",
            "url":      f"https://www.youtube.com/results?search_query={gfg_query}+tutorial",
            "source":   "YouTube",
            "channel":  "YouTube Search",
            "duration": "",
            "views":    "",
            "level_tag": level,
        }]

    # Main entry per skill
    def get_resources(self, skill: str, level: str) -> tuple:
        """Returns (resources: list, used_youtube: bool)."""
        if self.api_key:
            logger.info("[YouTube API] Attempting fetch for skill=%r level=%r", skill, level)
            try:
                raw = self._fetch_youtube(skill, level)
                if raw:
                    selected = self._select_varied_resources(raw, skill, level)
                    logger.info("[YouTube API] SUCCESS – got %d varied results for '%s'", len(selected), skill)
                    return selected, True
                else:
                    logger.warning("[YouTube API] Returned 0 results for '%s' – using fallback", skill)
            except Exception as e:
                logger.warning("[YouTube API] Exception for '%s': %s", skill, e)
        else:
            logger.warning("[YouTube API] No API key set – using static fallback")
        return self._static_fallback(skill, level)[:3], False

    # ── Weekly plan builder ─────────────────────────
    @staticmethod
    def _distribute_skills(skills: list) -> list[list]:
        """Return list-of-lists representing week buckets."""
        n = len(skills)
        if n == 0:
            return []
        if n == 1:
            num_weeks = 1
        elif n <= 4:
            num_weeks = 2
        elif n <= 8:
            num_weeks = 4
        elif n <= 15:
            num_weeks = 5
        else:
            num_weeks = 6

        buckets = [[] for _ in range(num_weeks)]
        for i, skill in enumerate(skills):
            buckets[i % num_weeks].append(skill)

        # Redistribute so no bucket exceeds 3 skills (overflow flows to next bucket)
        max_per_week = 3
        final = []
        for bucket in buckets:
            while len(bucket) > max_per_week:
                final.append(bucket[:max_per_week])
                bucket = bucket[max_per_week:]
            final.append(bucket)

        return [b for b in final if b]  # remove empty buckets

    # Public: build the full plan
    def build_study_plan(self, missing_skills: list, score: float) -> list:
        level   = self.get_skill_level(score)
        buckets = self._distribute_skills(missing_skills)
        weeks   = []
        for week_idx, skill_names in enumerate(buckets, start=1):
            skill_data = []
            for skill in skill_names:
                resources, used_youtube = self.get_resources(skill, level)
                skill_data.append({
                    "skill":       skill,
                    "resources":   resources,
                    # "youtube" = live API data  |  "fallback" = static library
                    "source_type": "youtube" if used_youtube else "fallback",
                })
            weeks.append({
                "week":   week_idx,
                "skills": skill_data,
            })
        return weeks
