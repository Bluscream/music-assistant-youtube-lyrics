# Music Assistant YouTube Lyrics Metadata Provider

A custom metadata provider plugin for [Music Assistant](https://github.com/music-assistant/server) that retrieves track transcripts/lyrics from YouTube and YouTube Music, converting them into time-synced LRC formats `[mm:ss.xx] Lyric text`.

## Features

- **Synced Lyrics:** Formats YouTube transcripts into standard `LRC` format so that Music Assistant can render them as synced/karaoke-style lyrics.
- **YouTube Music Resolve Search:** Option to search YouTube Music to fetch video IDs if the track does not come with a native YouTube/YTMusic provider mapping.
- **Translatable Lyrics:** Option to automatically translate transcripts to your preferred language code if supported.
- **Customizable Preferences:** Prioritize manual vs. auto-generated transcripts, select fallback languages, and enable/disable search.

## Installation

To deploy the provider plugin to your Music Assistant instance, copy the `youtube_lyrics` directory to your Music Assistant providers path, or run your deployment flow to place it under `/app/venv/lib/python3.14/site-packages/music_assistant/providers/youtube_lyrics/`.

## Configuration Settings

Once installed and activated in **Music Assistant -> Settings -> Integration / Plugins -> Add YouTube Lyrics**:

1. **Search YouTube for video ID:** Enable/disable searching YouTube Music when playing tracks from other sources (like Spotify or local files).
2. **Preferred Languages:** Comma-separated list of language codes to seek (e.g. `en,es,de`).
3. **Allow Auto-Generated Transcripts:** Toggle to retrieve auto-generated transcripts if manual ones are not found.
4. **Translate To Language Code:** Enter an optional target language (like `es`) to request machine translation.

## License

MIT License. See [LICENSE](LICENSE) for details.
