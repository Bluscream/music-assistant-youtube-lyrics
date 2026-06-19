# Music Assistant YouTube Lyrics Metadata Provider

A custom metadata provider plugin for [Music Assistant](https://github.com/music-assistant/server) that retrieves track transcripts/lyrics from YouTube and YouTube Music, converting them into time-synced LRC formats `[mm:ss.xx] Lyric text`.

## Features

- **Synced Lyrics:** Formats YouTube transcripts into standard `LRC` format so that Music Assistant can render them as synced/karaoke-style lyrics.
- **YouTube Music Resolve Search:** Option to search YouTube Music to fetch video IDs if the track does not come with a native YouTube/YTMusic provider mapping.
- **Translatable Lyrics:** Option to automatically translate transcripts to your preferred language code if supported.
- **Customizable Preferences:** Prioritize manual vs. auto-generated transcripts, select fallback languages, and enable/disable search.

## Installation

To deploy the provider plugin to your Music Assistant instance, copy the `youtube_lyrics` directory to your Music Assistant providers path, or run your deployment flow to place it under `/app/venv/lib/python3.14/site-packages/music_assistant/providers/youtube_lyrics/`.

### Persistent Installation (Docker / Unraid)

To prevent custom providers from being wiped when the Music Assistant Docker container is updated or restarted, you can use a startup hook script:

1. Create a `custom_providers` directory in your persistent appdata volume (e.g., `/mnt/user/appdata/music-assistant/custom_providers/`).
2. Place the provider folder (`youtube_lyrics`) inside that directory:
   `/mnt/user/appdata/music-assistant/custom_providers/youtube_lyrics`
3. Create an entrypoint hook script at `/mnt/user/appdata/music-assistant/entrypoint_hook.sh` with the following content:

```bash
#!/bin/sh

# Find site-packages directory
PROVIDERS_DIR=$(find /app/venv/lib/ -name "providers" -path "*/music_assistant/providers" | head -n 1)

if [ -n "${PROVIDERS_DIR}" ]; then
    # Copy custom providers from /data/custom_providers/
    if [ -d "/data/custom_providers" ]; then
        for provider in /data/custom_providers/*; do
            if [ -d "$provider" ]; then
                name=$(basename "$provider")
                rm -rf "${PROVIDERS_DIR}/${name}"
                cp -R "$provider" "${PROVIDERS_DIR}/${name}"
            fi
        done
    fi

    # Install dependencies if simplyrics is present
    if [ -d "${PROVIDERS_DIR}/simplyrics" ]; then
        /app/venv/bin/uv pip install ytmusicapi
    fi
fi

# Run the original entrypoint logic
for path in /usr/lib/*/libjemalloc.so.2; do
    [ -f "$path" ] && export LD_PRELOAD="$path" MALLOC_CONF="background_thread:true,dirty_decay_ms:5000,muzzy_decay_ms:5000" && break
done
exec mass "$@"
```

4. Make the script executable:
   ```bash
   chmod +x /mnt/user/appdata/music-assistant/entrypoint_hook.sh
   ```
5. Map this hook script in your Docker/Unraid container volume config:
   - **Host Path**: `/mnt/user/appdata/music-assistant/entrypoint_hook.sh`
   - **Container Path**: `/usr/local/bin/entrypoint.sh`
   - **Mode**: `Read/Write` (or `Read Only`)


## Configuration Settings

Once installed and activated in **Music Assistant -> Settings -> Integration / Plugins -> Add YouTube Lyrics**:

1. **Search YouTube for video ID:** Enable/disable searching YouTube Music when playing tracks from other sources (like Spotify or local files).
2. **Preferred Languages:** Comma-separated list of language codes to seek (e.g. `en,es,de`).
3. **Allow Auto-Generated Transcripts:** Toggle to retrieve auto-generated transcripts if manual ones are not found.
4. **Translate To Language Code:** Enter an optional target language (like `es`) to request machine translation.

## License

MIT License. See [LICENSE](LICENSE) for details.
