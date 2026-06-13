"""
The YouTube Lyrics Metadata provider for Music Assistant.
Retrieves song transcripts/lyrics from YouTube/YouTube Music and formats them as LRC.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from music_assistant_models.config_entries import ConfigEntry
from music_assistant_models.enums import ConfigEntryType, ProviderFeature
from music_assistant_models.media_items import MediaItemMetadata, Track
from music_assistant.models.metadata_provider import MetadataProvider

from youtube_transcript_api import YouTubeTranscriptApi
import ytmusicapi

if TYPE_CHECKING:
    from music_assistant_models.config_entries import ConfigValueType, ProviderConfig
    from music_assistant_models.provider import ProviderManifest
    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType

SUPPORTED_FEATURES = {
    ProviderFeature.TRACK_METADATA,
    ProviderFeature.LYRICS,
}

CONF_ENABLE_SEARCH = "enable_search"
CONF_LANGUAGES = "languages"
CONF_ALLOW_GENERATED = "allow_generated"
CONF_TRANSLATE_TO = "translate_to"


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    return YouTubeLyricsProvider(mass, manifest, config, SUPPORTED_FEATURES)


async def get_config_entries(
    mass: MusicAssistant,
    instance_id: str | None = None,
    action: str | None = None,
    values: dict[str, ConfigValueType] | None = None,
) -> tuple[ConfigEntry, ...]:
    """Return Config entries to setup this provider."""
    # ruff: noqa: ARG001
    return (
        ConfigEntry(
            key=CONF_ENABLE_SEARCH,
            type=ConfigEntryType.BOOLEAN,
            label="Search YouTube for video ID",
            description="If enabled, search YouTube Music when a track does not have a YouTube/YTMusic provider mapping.",
            default_value=False,
            required=True,
        ),
        ConfigEntry(
            key=CONF_LANGUAGES,
            type=ConfigEntryType.STRING,
            label="Preferred Languages",
            description="Comma-separated language codes in priority order (e.g., 'en,es,de').",
            default_value="en",
            required=True,
        ),
        ConfigEntry(
            key=CONF_ALLOW_GENERATED,
            type=ConfigEntryType.BOOLEAN,
            label="Allow Auto-Generated Transcripts",
            description="Allow retrieving auto-generated transcripts if manual ones are not available.",
            default_value=True,
            required=True,
        ),
        ConfigEntry(
            key=CONF_TRANSLATE_TO,
            type=ConfigEntryType.STRING,
            label="Translate To Language Code",
            description="Optional target language code to translate the transcript to (e.g. 'es', 'fr'). Leave blank to disable translation.",
            default_value="",
            required=False,
        ),
    )


class YouTubeLyricsProvider(MetadataProvider):
    """YouTube Lyrics provider for handling track transcripts."""

    async def handle_async_init(self) -> None:
        """Handle async initialization of the provider."""
        self._ytm = None

    def _get_ytm(self) -> ytmusicapi.YTMusic:
        """Get or initialize ytmusicapi client."""
        if self._ytm is None:
            self._ytm = ytmusicapi.YTMusic()
        return self._ytm

    async def get_track_metadata(self, track: Track) -> MediaItemMetadata | None:
        """Retrieve lyrics for a track."""
        if track.metadata and (track.metadata.lyrics or track.metadata.lrc_lyrics):
            self.logger.debug(
                "Lyrics already exist for %s, skipping YouTube Lyrics lookup.",
                track.name,
            )
            return None

        # Resolve Video ID from provider mappings
        video_id = None
        if hasattr(track, "provider_mappings"):
            for pm in track.provider_mappings:
                if pm.provider_domain in ("ytmusic", "youtube"):
                    video_id = pm.item_id
                    break

        # If not found, check if searching is enabled
        enable_search = self.config.get_value(CONF_ENABLE_SEARCH, False)
        if not video_id and enable_search:
            if not track.artists or not track.name:
                self.logger.debug("Skipping search lookup: missing artist or track name.")
                return None
            artist_name = track.artists[0].name
            query = f"{track.name} {artist_name}"
            video_id = await self._search_youtube_video_id(query)

        if not video_id:
            self.logger.debug("No YouTube Video ID resolved for track %s", track.name)
            return None

        # Fetch transcript
        lrc_content = await self._fetch_transcript_as_lrc(video_id)
        if lrc_content:
            metadata = MediaItemMetadata()
            metadata.lrc_lyrics = lrc_content
            self.logger.info("Successfully fetched YouTube transcript lyrics for %s", track.name)
            return metadata

        return None

    async def _search_youtube_video_id(self, query: str) -> str | None:
        """Search YouTube Music for a video ID."""
        def _search():
            try:
                self.logger.debug("Searching YouTube Music for query: %s", query)
                results = self._get_ytm().search(query=query, filter="songs", limit=3)
                if results and len(results) > 0:
                    return results[0].get("videoId")
            except Exception as e:
                self.logger.warning("Error searching YouTube Music: %s", e)
            return None

        return await asyncio.to_thread(_search)

    async def _fetch_transcript_as_lrc(self, video_id: str) -> str | None:
        """Retrieve and format transcript as LRC from a YouTube Video ID."""
        # Get configuration settings
        languages_str = self.config.get_value(CONF_LANGUAGES, "en")
        languages = [lang.strip() for lang in languages_str.split(",") if lang.strip()]
        allow_generated = self.config.get_value(CONF_ALLOW_GENERATED, True)
        translate_to = self.config.get_value(CONF_TRANSLATE_TO, "")

        def _fetch():
            try:
                ytt_api = YouTubeTranscriptApi()
                transcript_list = ytt_api.list(video_id)

                # Filter transcripts based on configuration
                transcript_obj = None
                
                # First try to find manual transcripts in preferred languages
                try:
                    transcript_obj = transcript_list.find_manually_created_transcript(languages)
                except Exception:
                    pass

                # If not found and auto-generated is allowed, look for auto-generated in preferred languages
                if not transcript_obj and allow_generated:
                    try:
                        transcript_obj = transcript_list.find_generated_transcript(languages)
                    except Exception:
                        pass

                # Fallback to finding any transcript in preferred languages if strict check wasn't enough
                if not transcript_obj:
                    try:
                        transcript_obj = transcript_list.find_transcript(languages)
                    except Exception:
                        pass

                if not transcript_obj:
                    self.logger.debug("No matching transcript found for Video ID %s", video_id)
                    return None

                # Handle translation if configured
                if translate_to and transcript_obj.language_code != translate_to:
                    if transcript_obj.is_translatable:
                        translation_codes = [lang.language_code for lang in transcript_obj.translation_languages]
                        if translate_to in translation_codes:
                            self.logger.debug("Translating transcript to %s", translate_to)
                            transcript_obj = transcript_obj.translate(translate_to)
                        else:
                            self.logger.warning("Translation to %s not available for Video ID %s", translate_to, video_id)
                    else:
                        self.logger.warning("Transcript for Video ID %s is not translatable", video_id)

                # Retrieve the raw chunks
                transcript_data = transcript_obj.fetch()
                
                # Format to LRC
                lrc_lines = []
                for item in transcript_data:
                    start_sec = getattr(item, "start", 0)
                    text = getattr(item, "text", "").replace("\n", " ")
                    timestamp = self._seconds_to_lrc_timestamp(start_sec)
                    lrc_lines.append(f"{timestamp} {text}")

                return "\n".join(lrc_lines)

            except Exception as e:
                self.logger.warning("Failed to fetch transcript for Video ID %s: %s", video_id, e)
                return None

        return await asyncio.to_thread(_fetch)

    @staticmethod
    def _seconds_to_lrc_timestamp(seconds: float) -> str:
        """Convert float seconds to LRC timestamp [mm:ss.xx]."""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"[{minutes:02d}:{secs:05.2f}]"
