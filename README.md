# Reolink NVR Viewer

A lightweight viewer plus Python proxy that renders up to four Reolink NVR channels using [`flv.js`](https://github.com/bilibili/flv.js). The browser UI lives in `index.html`, while the bundled Flask server (`server.py`) proxies HTTP-FLV traffic from your NVR through ffmpeg so modern browsers can play the streams without fighting CORS or RTMP limitations. Run both pieces on a trusted LAN host and browse to the proxy to watch your feeds.
## Security Warning ⚠️🚨

- ⚠️🚫 **LAN/VPN only:** Keep the proxy and viewer on a trusted network so HTTP-FLV traffic never touches the public internet.
- 🔐📛 **Protect credentials:** Store `NVR_USER` / `NVR_PASSWORD` in your shell environment and avoid hardcoding sensitive values in `config.js` or version control.


## Requirements

- Python 3.12+
- [`ffmpeg`](https://ffmpeg.org/download.html) accessible on your `PATH`
- Python proxy deps from `requirements.txt` (run `python -m pip install -r requirements.txt` to install Flask 3.1.2 plus the pinned Werkzeug, Click, Jinja2, MarkupSafe, Blinker, and ItsDangerous versions the proxy relies on)

## Configure

1. Copy the template and update the placeholders:

   ```bash
   cp config.template.js config.js
   ```

   Then edit `config.js`:
   - `nvrIp`: IP or hostname of your Reolink NVR (used only for constructing stream names).
   - `port`: The RTMP forwarding port (default is `1935`).
   - `username` / `password`: Optional only if you ever bypass the proxy; normally you should export `NVR_USER` / `NVR_PASSWORD` before running `server.py` so the proxy injects credentials for every request.
   - `proxyOrigin`: Leave blank to use the detected `window.location.origin`. Set it only if you host the proxy somewhere other than `http://127.0.0.1:8000`.
   - `cameras`: List of channels you want to see. Only the first four entries are rendered, intended for a 2×2 tile view.

Each camera entry should include at least a `channel` number (0-based) and optional `name`, `hasAudio`, `streamName`, and `streamIndex`. Omit `streamName` to fall back to `channel{channel}_main.bcs`. The viewer automatically sets the FLV `stream` flag to `1` when the name ends with `_sub`; set `streamIndex` to `"0"` or `"1"` explicitly if you need to override that heuristic. Example:

```js
{
  name: "Front Door",
  channel: 0,
  hasAudio: false,
  streamName: "channel201_sub.bcs",
  streamIndex: "1"
}
```

The browser always calls `/flv` on the proxy origin (defaults to `http://127.0.0.1:8000`). The `stream` parameter itself contains the playpath *and* the `channel`/`stream` flags, so the proxy can faithfully reconstruct the RTMP URL even though the browser never touches the NVR directly:

```
http://<proxy-origin>/flv?port=1935&app=bcs&stream=<streamName>.bcs%3Fchannel=<channel>%26stream=<0|1>
```

## Use

1. **Build a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   ```

2. **Configure the viewer** – Copy `config.template.js` to `config.js`, edit it as described above, and keep it out of version control (already handled by `.gitignore`). Leave `proxyOrigin` blank unless you bind the proxy somewhere other than `http://127.0.0.1:8000`.
3. **Provide credentials via env vars** – for example:

   ```bash
   export NVR_USER=admin
   export NVR_PASSWORD='letmein'
   ```

   Override the env var names with `--nvr-user-env` / `--nvr-password-env` if needed.
4. **Execute the Python proxy** – this binds to localhost and pipes RTMP from the NVR through ffmpeg to `/flv`:

   ```bash
   python server.py --nvr-host 192.168.1.126 --rtmp-port 1935 --nvr-protocol rtmp
   ```

5. **Connect through the browser** – browse to `http://127.0.0.1:8000/`. The viewer and `/flv` calls will now share the same origin. If streams fail, check the Python console for the reconstructed RTMP URL and ffmpeg command to confirm addresses, ports, and credentials.

### Manual verification

You can validate the proxy without opening the viewer:

```bash
curl -o test.flv "http://127.0.0.1:8000/flv?port=1935&app=bcs&stream=channel2_main.bcs&channel=2&stream=0&user=admin&password=letmein"
ffprobe -v info -i "http://127.0.0.1:8000/flv?port=1935&app=bcs&stream=channel2_main.bcs&channel=2&stream=0&user=admin&password=letmein"
```

Swap in the channel, stream name, and credentials that match the RTMP URL you have already validated (e.g., via `ffprobe rtmp://...`). Once these commands work, the browser tiles will work as well.

## Notes

- Browsers must support Media Source Extensions (Chrome, Edge, Firefox). Safari currently cannot play HTTP-FLV.
- flv.js runs inline (no Web Worker) to avoid the compatibility issues that some Chromium builds have with worker-based MSE pipelines.
- If you serve this through HTTPS but your NVR is HTTP-only, your browser will block the mixed-content request. In that case, either host this page over HTTP within your LAN or put the NVR behind an HTTPS-capable proxy.
- The bundled proxy shells out to `ffmpeg` to remux RTMP into HTTP-FLV, so you must have an `ffmpeg` binary available on your `PATH`.

## Security Warning ⚠️🚨

- ⚠️🚫 **LAN/VPN only:** Keep the proxy and viewer on a trusted network so HTTP-FLV traffic never touches the public internet.
- 🔐📛 **Protect credentials:** Store `NVR_USER` / `NVR_PASSWORD` in your shell environment and avoid hardcoding sensitive values in `config.js` or version control.
