# Reolink NVR Viewer

A tiny static page that renders up to four Reolink NVR channels using the browser-based [`flv.js`](https://github.com/bilibili/flv.js) player. Everything runs locally in the browser—just open `index.html` in Chrome, Edge, or Firefox.

## Requirements

- Python 3.12+
- [`ffmpeg`](https://ffmpeg.org/download.html) accessible on your `PATH`
- [`Flask`](https://flask.palletsprojects.com/) for the proxy (`pip install flask`)

## Configure

1. Edit `config.js` and update the placeholders:
   - `nvrIp`: IP or hostname of your Reolink NVR.
   - `protocol`: `http` or `https` depending on how you expose the `/flv` endpoint (ignored when `useProxy` is `true`).
   - `port`: The RTMP forwarding port (default is `1935`).
   - `username` / `password`: The credentials you use for the Reolink web UI. Leave them blank if you provide credentials via the Python proxy env vars described below.
   - `streamProfile`: `main` (full quality), `ext` (Reolink “extra” profile when available), or `sub` (lower bitrate). You can override this per camera with `streamProfile` inside a camera entry.
   - `useWorker`: Leave `false` if you see errors coming from a `blob:` URL (some browsers / security settings prevent flv.js workers). Set to `true` only if streams play fine with workers enabled for better CPU usage.
   - `useProxy` / `proxyOrigin`: Set `useProxy: true` when you run the Python server; the viewer will then call `/flv` on the proxy origin (`proxyOrigin` overrides the detected `window.location.origin` if needed).
   - `cameras`: List of channels you want to see. Only the first four entries are rendered, intended for a 2×2 tile view.

Each camera entry should include at least a `channel` number (0-based) and optional `name`, `hasAudio`, `streamProfile`, and `streamName`. Use `streamName` if your Reolink assigns a playpath that does not match the default `channel{channel}_{profile}.bcs`. Example:

```js
{
  name: "Front Door",
  channel: 0,
  hasAudio: false,
  streamProfile: "sub",
  streamName: "channel201_sub.bcs"
}
```

The generated stream URL follows the pattern Reolink uses for HTTP-FLV/RTMP. The `stream` parameter itself contains the playpath *and* the `channel`/`stream` flags, so the proxy can faithfully reconstruct the RTMP URL:

```
http(s)://<origin>/flv?port=1935&app=bcs&stream=channel<channel>_<profile>.bcs%3Fchannel=<channel>%26stream=<0|1>&user=<username>&password=<password>
```

## Use

1. After editing `config.js`, simply open `index.html` in a supported browser, or run the local proxy outlined below.
2. Allow the page to auto-play video (stream tiles are muted to satisfy browser policies).
3. Each tile includes **Reconnect** and **Stop** buttons if a stream needs to be restarted.

## Local-only proxy server

Many browsers will block the direct `http://<nvr-ip>/flv` request because of CORS. Use the bundled Python helper if that happens:

1. Set `useProxy: true` in `config.js`. Leave `proxyOrigin` blank unless you bind the proxy somewhere other than `http://127.0.0.1:8000`.
2. Install the proxy dependency if you have not already:

   ```bash
   pip install flask
   ```

3. Provide your credentials via environment variables and start the proxy (this binds to localhost only):

   ```bash
   NVR_USER=admin NVR_PASSWORD='letmein' python3 server.py --nvr-host 192.168.1.126
   ```

   Adjust `--rtmp-port` and `--nvr-protocol` if your NVR uses non-default RTMP settings (`rtmp://<host>:1935`). Use `--ffmpeg-bin` to point at a custom ffmpeg binary. You can change the env var names with `--nvr-user-env` / `--nvr-password-env`.
4. Browse to `http://127.0.0.1:8000/` and the viewer plus `/flv` requests will share the same origin, bypassing the CORS restriction. Leave `nvrIp` in `config.js` set to your actual NVR for display/reference; the proxy CLI flags determine the true upstream.

If you see `404` or `5xx` statuses in the browser, check the Python server console—each proxied `/flv` request logs the incoming querystring, the parsed params, the exact RTMP URL, and the ffmpeg command so you can confirm the RTMP port, channel index, and credentials are correct.

### Manual verification

You can validate the proxy without opening the viewer:

```bash
curl -o test.flv "http://127.0.0.1:8000/flv?port=1935&app=bcs&stream=channel2_main.bcs&channel=2&stream=0&user=admin&password=letmein"
ffprobe -v info -i "http://127.0.0.1:8000/flv?port=1935&app=bcs&stream=channel2_main.bcs&channel=2&stream=0&user=admin&password=letmein"
```

Swap in the channel, stream profile, and credentials that match the RTMP URL you have already validated (e.g., via `ffprobe rtmp://...`). Once these commands work, the browser tiles will work as well.

## Notes

- Browsers must support Media Source Extensions (Chrome, Edge, Firefox). Safari currently cannot play HTTP-FLV.
- If you serve this through HTTPS but your NVR is HTTP-only, your browser will block the mixed-content request. In that case, either host this page over HTTP within your LAN or put the NVR behind an HTTPS-capable proxy.
- Credentials live in `config.js`. Consider keeping the file outside version control or injecting values at build time if you plan to share this repo.
