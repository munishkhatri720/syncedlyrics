import os
import time
import json
from typing import Optional, List
from .base import LRCProvider
from ..utils import get_best_match

class Musixmatch(LRCProvider):
    """Musixmatch provider class"""

    ROOT_URL = "https://apic-desktop.musixmatch.com/ws/1.1/"

    def __init__(self) -> None:
        super().__init__()
        self.token = None
        self.session.headers.update(
            {
                "authority": "apic-desktop.musixmatch.com",
                "cookie": "AWSELBCORS=0; AWSELB=0",
            }
        )

    def _get(self, action: str, query: List[tuple]):
        if action != "token.get" and self.token is None:
            self._get_token()
        query.append(("app_id", "web-desktop-app-v1.0"))
        if self.token is not None:
            query.append(("usertoken", self.token))
        t = str(int(time.time() * 1000))
        query.append(("t", t))
        url = self.ROOT_URL + action
        response = self.session.get(url, params=query)
        return response

    def _get_token(self):
        current_time = int(time.time())
        cached_token = os.environ.get("MUSIXMATCH_TOKEN")
        expiration_time = int(os.environ.get("MUSIXMATCH_TOKEN_EXPIRATION", 0))
        
        if cached_token and expiration_time > current_time:
            self.token = cached_token
            return

        d = self._get("token.get", [("user_language", "en")]).json()
        if d["message"]["header"]["status_code"] == 401:
            time.sleep(10)
            return self._get_token()

        new_token = d["message"]["body"]["user_token"]
        expiration_time = current_time + 600  # 10 minutes expiration

        # Cache the new token using environment variables
        os.environ["MUSIXMATCH_TOKEN"] = new_token
        os.environ["MUSIXMATCH_TOKEN_EXPIRATION"] = str(expiration_time)

    def get_lrc_by_id(self, track_id: str) -> Optional[str]:
        r = self._get(
            "track.subtitle.get", [("track_id", track_id), ("subtitle_format", "lrc")]
        )
        if not r.ok:
            return
        body = r.json()["message"]["body"]
        if not body:
            return
        return body["subtitle"]["subtitle_body"]

    def get_lrc(self, search_term: str) -> Optional[str]:
        r = self._get(
            "track.search",
            [
                ("q", search_term),
                ("page_size", "5"),
                ("page", "1"),
                ("s_track_rating", "desc"),
                ("quorum_factor", "1.0"),
            ],
        )
        body = r.json()["message"]["body"]
        tracks = body["track_list"]
        cmp_key = lambda t: f"{t['track']['track_name']} {t['track']['artist_name']}"
        track = get_best_match(tracks, search_term, cmp_key)
        if not track:
            return
        return self.get_lrc_by_id(track["track"]["track_id"])
