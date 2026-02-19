# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import os
import re
import asyncio
import aiohttp
import yt_dlp
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

    async def clear_old_files(self, directory: str, keep_limit: int = 10):
        # 🔥 AWS Storage Saver 🔥
        try:
            files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            if len(files) > keep_limit:
                files.sort(key=os.path.getctime)
                files_to_delete = len(files) - keep_limit
                for i in range(files_to_delete):
                    try:
                        os.remove(files[i])
                        logger.info(f"Auto-Cleaned old file: {files[i]} to save AWS space.")
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Auto-Clean Error: {e}")

    async def download(self, video_id: str, video: bool = False) -> str | None:
        DOWNLOAD_DIR = "downloads"
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        # Storage full hone se bachao
        await self.clear_old_files(DOWNLOAD_DIR, keep_limit=10)

        ext = "mp4" if video else "mp3"
        file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")

        if os.path.exists(file_path) and os.path.getsize(file_path) > 100000:
            return file_path

        # PLAN A: ShrutiBots API (Fastest)
        logger.info(f"Fast Downloading {video_id} via ShrutiBots API...")
        api_success = False
        try:
            async with aiohttp.ClientSession() as session:
                params = {"url": video_id, "type": "video" if video else "audio"}
                async with session.get(f"{self.api_url}/download", params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        token = data.get("download_token")
                        if token:
                            stream_url = f"{self.api_url}/stream/{video_id}?type={'video' if video else 'audio'}"
                            async with session.get(stream_url, headers={"X-Download-Token": token}, timeout=120) as file_response:
                                if file_response.status == 200:
                                    with open(file_path, "wb") as f:
                                        async for chunk in file_response.content.iter_chunked(16384):
                                            f.write(chunk)
                                    api_success = True
        except Exception as e:
            logger.warning(f"ShrutiBots API Down/Failed: {e}")
        
        if api_success and os.path.exists(file_path) and os.path.getsize(file_path) > 100000:
            return file_path

        # PLAN B: Ultra-Bypass yt-dlp Fallback (No bot detection!)
        logger.info(f"API failed. Using Fallback yt-dlp to download {video_id}...")
        
        def _fallback_download():
            ydl_opts = {
                "format": "bestaudio/best" if not video else "best[height<=?720]",
                "outtmpl": file_path,
                "quiet": True,
                "geo_bypass": True,
                "nocheckcertificate": True,
                # iPhone aur Smart TV ka bypass
                "extractor_args": {"youtube": ["client=IOS,TV", "player_client=IOS,TV"]},
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
                }
            }
            
            # 🔥 Cookie Injector 🔥 (Agar file bahar rakhi hai toh use karega)
            if os.path.exists("cookies.txt"):
                ydl_opts["cookiefile"] = "cookies.txt"

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([self.base + video_id])
                return True
            except Exception as e:
                logger.error(f"Fallback DL Error: {e}")
                return False

        success = await asyncio.to_thread(_fallback_download)
        if success and os.path.exists(file_path):
            return file_path

        return None
                          
