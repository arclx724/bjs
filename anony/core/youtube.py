# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import os
import re
import yt_dlp
import asyncio
import aiohttp
from pathlib import Path
from py_yt import Playlist, VideosSearch
from anony import logger
from anony.helpers import Track, utils

class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.api_url = "https://shrutibots.site"

    async def save_cookies(self, urls: list[str]) -> None:
        pass

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        _search = VideosSearch(query, limit=1, with_live=False)
        results = await _search.next()
        if results and results["result"]:
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track | None]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception:
            pass
        return tracks

    async def download(self, video_id: str, video: bool = False) -> str | None:
        DOWNLOAD_DIR = "downloads"
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        ext = "mp4" if video else "mp3"
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")

        # Agar pehle se download hai aur file size sahi hai, toh instant return karo
        if os.path.exists(file_path) and os.path.getsize(file_path) > 100000:
            return file_path

        logger.info(f"Fast Downloading {video_id} via ShrutiBots API...")
        try:
            async with aiohttp.ClientSession() as session:
                params = {"url": video_id, "type": "video" if video else "audio"}
                async with session.get(f"{self.api_url}/download", params=params, timeout=30) as response:
                    if response.status != 200:
                        return None
                    data = await response.json()
                    token = data.get("download_token")
                    if not token:
                        return None
                    
                    stream_url = f"{self.api_url}/stream/{video_id}?type={'video' if video else 'audio'}"
                    async with session.get(stream_url, headers={"X-Download-Token": token}, timeout=120) as file_response:
                        if file_response.status != 200:
                            return None
                        with open(file_path, "wb") as f:
                            async for chunk in file_response.content.iter_chunked(16384):
                                f.write(chunk)
                        return file_path
        except Exception as e:
            logger.error(f"API Download Error: {e}")
        return None
        
