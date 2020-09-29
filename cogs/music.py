import asyncio
import urllib.parse, urllib.request, re

import discord
import youtube_dl
import os

from discord.ext import commands

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    @commands.command()
    async def add_song(self, track):
        """Adds the track to the playlist instance and plays it, if it is the first song"""

        # If the track is a video title, get the corresponding video link first
        if not ("watch?v=" in track):
            link = self.convert_to_youtube_link('"' + track + '"')
            if link is None:
                link = self.convert_to_youtube_link(track)
                if link is None:
                    return
        else:
            link = track
        self.playlist.add(link)
        if len(self.playlist.playque) == 1:
            await self.play_youtube(link)

    def convert_to_youtube_link(self, title):
        """Searches youtube for the video title and returns the first results video link"""

        filter(lambda x: x in set(printable), title)

        # Parse the search result page for the first results link
        query = urllib.parse.quote(title)
        url = "https://www.youtube.com/results?search_query=" + query
        response = urllib.request.urlopen(url)
        html = response.read()
        soup = BeautifulSoup(html, "html.parser")
        results = soup.findAll(attrs={'class': 'yt-uix-tile-link'})
        checked_videos = 0;
        while len(results) > checked_videos:
            if not "user" in results[checked_videos]['href']:
                return 'https://www.youtube.com' + results[checked_videos]['href']
            checked_videos += 1
        return None

    async def load(self, youtube_link):
        """Downloads and plays the audio of the youtube link passed"""

        youtube_link = youtube_link.split("&list=")[0]

        try:
            downloader = youtube_dl.YoutubeDL({'format': 'bestaudio', 'title': True})
            extracted_info = downloader.extract_info(youtube_link, download=False)
        # "format" is not available for livestreams - redownload the page with no options
        except:
            try:
                downloader = youtube_dl.YoutubeDL({})
                extracted_info = downloader.extract_info(youtube_link, download=False)
            except:
                self.next_song(None)



bot = commands.Bot(command_prefix=commands.when_mentioned_or("!!"),
                   description='Relatively simple music bot example')

def setup(client):
    client.add_cog(Music(client))
