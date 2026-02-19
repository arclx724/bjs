# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import re
import aiohttp
import asyncio
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
        logger.info(f"Extracting Superfast Direct Stream URL for {video_id}...")
        
        # Multiple public APIs taaki bot kabhi down na ho
        apis = [
            "https://pipedapi.kavin.rocks",
            "https://pipedapi.smnz.de",
            "https://pipedapi.adminforge.de"
        ]
        
        async with aiohttp.ClientSession() as session:
            for api in apis:
                try:
                    async with session.get(f"{api}/streams/{video_id}", timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            if video:
                                streams = data.get("videoStreams", [])
                                stream = next((s for s in streams if not s.get("videoOnly")), None)
                                if stream: 
                                    return stream["url"]
                            else:
                                streams = data.get("audioStreams", [])
                                if streams:
                                    logger.info("Direct Stream Link fetched successfully! Instantly playing...")
                                    return streams[0]["url"]
                except Exception as e:
                    logger.warning(f"Failed to fetch from {api}: {e}")
                    continue
        
        logger.error("All Direct Stream APIs failed.")
        return None
        
