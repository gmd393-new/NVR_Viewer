#!/usr/bin/env python3
"""Serve the static viewer and expose /flv that relays RTMP streams as HTTP-FLV."""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass
from typing import Dict, Iterable

from flask import (
    Flask,
    Response,
    abort,
    current_app,
    request,
    send_from_directory,
    stream_with_context,
)


@dataclass
class ProxySettings:
    static_dir: str
    listen_host: str
    listen_port: int
    nvr_host: str
    default_rtmp_port: int
    nvr_protocol: str
    nvr_user: str | None
    nvr_password: str | None
    ffmpeg_bin: str
    nvr_user_env: str | None
    nvr_password_env: str | None


def create_app(settings: ProxySettings) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["PROXY_SETTINGS"] = settings

    @app.route("/flv", methods=["OPTIONS"])
    def flv_options() -> Response:
        resp = Response(status=204)
        resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        resp.headers["Access-Control-Allow-Origin"] = f"http://{settings.listen_host}:{settings.listen_port}"
        return resp

    @app.route("/flv", methods=["GET"])
    def flv_proxy() -> Response:
        raw_query = request.query_string.decode("utf-8", "replace")
        current_app.logger.info("Incoming %s?%s", request.path, raw_query)
        params = {key: value for key, value in request.args.items()}
        current_app.logger.info("Parsed params: %s", params)
        try:
            rtmp_url = _build_rtmp_url(params, settings)
        except ValueError as exc:  # invalid/missing params
            abort(400, description=str(exc))

        current_app.logger.info("RTMP upstream: %s", rtmp_url)
        return _stream_rtmp_over_http(rtmp_url, settings)

    @app.route("/")
    def index() -> Response:
        return send_from_directory(settings.static_dir, "index.html")

    @app.route("/<path:path>")
    def static_files(path: str) -> Response:
        return send_from_directory(settings.static_dir, path)

    return app


def _build_rtmp_url(params: Dict[str, str], settings: ProxySettings) -> str:
    stream_value = params.get("stream")
    if not stream_value:
        raise ValueError("Missing required 'stream' query parameter")

    port_value = params.get("port") or settings.default_rtmp_port
    try:
        rtmp_port = int(port_value)
    except ValueError as exc:
        raise ValueError("Invalid 'port' value") from exc

    app_segment = params.get("app", "bcs").strip("/") or "bcs"

    path_part, _, existing_query = stream_value.partition("?")
    existing_params = dict(urllib.parse.parse_qsl(existing_query, keep_blank_values=True)) if existing_query else {}

    extras: Dict[str, str] = {}
    for key, value in params.items():
        if key in {"port", "app", "stream"}:
            continue
        extras[key] = value

    if settings.nvr_user and "user" not in (extras.keys() | existing_params.keys()):
        extras["user"] = settings.nvr_user
    if settings.nvr_password and "password" not in (extras.keys() | existing_params.keys()):
        extras["password"] = settings.nvr_password

    for key, value in extras.items():
        existing_params.setdefault(key, value)

    query_string = urllib.parse.urlencode(existing_params)
    playpath = path_part.lstrip("/")
    if query_string:
        playpath = f"{playpath}?{query_string}"

    protocol = settings.nvr_protocol
    return f"{protocol}://{settings.nvr_host}:{rtmp_port}/{app_segment}/{playpath}"


def _stream_rtmp_over_http(rtmp_url: str, settings: ProxySettings) -> Response:
    ffmpeg_path = shutil.which(settings.ffmpeg_bin) or settings.ffmpeg_bin
    if not shutil.which(ffmpeg_path):
        abort(500, description="ffmpeg binary not found. Install ffmpeg or set --ffmpeg-bin")

    cmd = [
        ffmpeg_path,
        "-nostdin",
        "-loglevel",
        "error",
        "-rw_timeout",
        "5000000",
        "-i",
        rtmp_url,
        "-c",
        "copy",
        "-f",
        "flv",
        "pipe:1",
    ]
    current_app.logger.info("ffmpeg command: %s", " ".join(cmd))

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
    except FileNotFoundError as exc:
        abort(500, description=f"Unable to execute ffmpeg: {exc}")

    if proc.stdout is None or proc.stderr is None:
        proc.kill()
        abort(500, description="Failed to start ffmpeg subprocess")

    def generate() -> Iterable[bytes]:
        try:
            while True:
                chunk = proc.stdout.read(64 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            if proc.poll() is None:
                proc.kill()
            stderr_output = proc.stderr.read().decode("utf-8", "replace").strip()
            if stderr_output:
                current_app.logger.error("ffmpeg stderr: %s", stderr_output)

    response = Response(stream_with_context(generate()), mimetype="video/x-flv")
    response.headers["Cache-Control"] = "no-store"
    return response


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the viewer and proxy RTMP streams as HTTP-FLV")
    parser.add_argument("--listen-host", default="127.0.0.1", help="Interface to bind (default: 127.0.0.1)")
    parser.add_argument("--listen-port", type=int, default=8000, help="Local port for HTTP server")
    parser.add_argument("--directory", default=os.path.dirname(__file__), help="Directory containing the static viewer files")
    parser.add_argument("--nvr-host", required=True, help="IP or hostname of the Reolink NVR")
    parser.add_argument("--rtmp-port", type=int, default=1935, help="Default RTMP port if 'port' is not supplied in requests")
    parser.add_argument("--nvr-protocol", choices=("rtmp", "rtmps"), default="rtmp", help="RTMP protocol to use upstream")
    parser.add_argument("--nvr-user-env", default="NVR_USER", help="Env var with the default username (optional)")
    parser.add_argument("--nvr-password-env", default="NVR_PASSWORD", help="Env var with the default password (optional)")
    parser.add_argument("--ffmpeg-bin", default="ffmpeg", help="ffmpeg binary to execute (default: ffmpeg)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    static_dir = os.path.abspath(args.directory)
    if not os.path.isdir(static_dir):
        print(f"Static directory does not exist: {static_dir}", file=sys.stderr)
        sys.exit(1)

    settings = ProxySettings(
        static_dir=static_dir,
        listen_host=args.listen_host,
        listen_port=args.listen_port,
        nvr_host=args.nvr_host,
        default_rtmp_port=args.rtmp_port,
        nvr_protocol=args.nvr_protocol,
        nvr_user=os.environ.get(args.nvr_user_env) if args.nvr_user_env else None,
        nvr_password=os.environ.get(args.nvr_password_env) if args.nvr_password_env else None,
        ffmpeg_bin=args.ffmpeg_bin,
        nvr_user_env=args.nvr_user_env,
        nvr_password_env=args.nvr_password_env,
    )

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = create_app(settings)
    app.logger.setLevel(logging.INFO)
    if not settings.nvr_user:
        app.logger.warning(
            "No default NVR username detected. Provide ?user=... in requests or set %s",
            settings.nvr_user_env or "NVR_USER",
        )
    if not settings.nvr_password:
        app.logger.warning(
            "No default NVR password detected. Provide ?password=... in requests or set %s",
            settings.nvr_password_env or "NVR_PASSWORD",
        )
    app.logger.info(
        "Serving viewer on http://%s:%s (proxying RTMP via %s://%s:%s)",
        settings.listen_host,
        settings.listen_port,
        settings.nvr_protocol,
        settings.nvr_host,
        settings.default_rtmp_port,
    )
    app.run(host=settings.listen_host, port=settings.listen_port, threaded=True)


if __name__ == "__main__":
    main()
