(function () {
  const DEFAULT_CONFIG = {
    nvrIp: "192.168.1.100",
    port: 1935,
    protocol: "http",
    username: "admin",
    password: "",
    streamProfile: "main",
    useWorker: false,
    cameras: []
  };

  const AUTO_REFRESH_MS = 30 * 60 * 1000; // reload page every 30 minutes to recover stale streams

  const cfg = Object.assign({}, DEFAULT_CONFIG, window.NVR_CONFIG || {});
  const statusEl = document.getElementById("status");
  const grid = document.getElementById("camera-grid");
  const players = [];

  function updateStatus(message, isError = false) {
    statusEl.textContent = message || "";
    statusEl.classList.toggle("status__error", Boolean(isError));
  }

  function buildStreamUrl(camera) {
    if (!cfg.nvrIp) {
      throw new Error("Missing NVR IP address. Update config.js");
    }

    const protocol = cfg.protocol || "http";
    const streamProfile = (camera.streamProfile || cfg.streamProfile || "main").toLowerCase();
    const channelIndex = typeof camera.channel === "number" ? camera.channel : camera.id;

    if (typeof channelIndex !== "number") {
      throw new Error(`Camera ${camera.name || ""} is missing a channel number.`);
    }

    const profileSuffix = streamProfile === "ext" ? "ext" : streamProfile;
    const streamName = camera.streamName || `channel${channelIndex}_${profileSuffix}.bcs`;
    const streamIndex = streamProfile === "sub" ? "1" : "0";

    const playpathQuery = new URLSearchParams({
      channel: channelIndex.toString(),
      stream: streamIndex
    });

    const params = new URLSearchParams({
      port: cfg.port?.toString() || "1935",
      app: "bcs",
      stream: `${streamName}?${playpathQuery.toString()}`
    });

    if (!cfg.useProxy) {
      if (cfg.username) params.set("user", cfg.username);
      if (cfg.password) params.set("password", cfg.password);
    }

    const baseOrigin = cfg.useProxy
      ? cfg.proxyOrigin || window.location.origin
      : `${protocol}://${cfg.nvrIp}`;

    return `${baseOrigin}/flv?${params.toString()}`;
  }

  function createCameraTile(camera) {
    const tile = document.createElement("article");
    tile.className = "camera";

    const title = document.createElement("h2");
    title.className = "camera__title";
    title.textContent = camera.name || `Channel ${camera.channel}`;
    tile.appendChild(title);

    const video = document.createElement("video");
    video.setAttribute("playsinline", "");
    video.muted = true; // allows autoplay
    video.autoplay = true;
    video.controls = true;
    tile.appendChild(video);

    let player = null;

    function destroyPlayer() {
      if (player) {
        try {
          player.pause();
          player.unload();
          player.detachMediaElement();
          player.destroy();
        } catch (err) {
          console.warn("Failed to destroy player", err);
        }
        player = null;
      }
      video.removeAttribute("src");
    }

    function startPlayer() {
      destroyPlayer();
      if (!window.flvjs || !flvjs.isSupported()) {
        updateStatus("flv.js is not supported in this browser. Try the latest Chromium, Edge, or Firefox.", true);
        return;
      }

      let streamUrl;
      try {
        streamUrl = buildStreamUrl(camera);
      } catch (err) {
        updateStatus(err.message, true);
        return;
      }

      player = flvjs.createPlayer(
        {
          type: "flv",
          isLive: true,
          hasAudio: camera.hasAudio ?? true,
          url: streamUrl
        },
        {
          enableWorker: cfg.useWorker !== false,
          enableStashBuffer: false
        }
      );

      player.attachMediaElement(video);
      player.load();
      player.play().catch((err) => {
        console.error("Playback error", err);
        updateStatus(`Camera ${camera.name || camera.channel}: ${err.message}`, true);
      });
    }

    startPlayer();

    players.push({ destroy: destroyPlayer });
    return tile;
  }

  function init() {
    if (!cfg.cameras || cfg.cameras.length === 0) {
      updateStatus("Add at least one camera to config.js", true);
      return;
    }

    cfg.cameras.slice(0, 4).forEach((camera) => {
      const tile = createCameraTile(camera);
      grid.appendChild(tile);
    });

    if (cfg.cameras.length > 4) {
      updateStatus("Only the first 4 cameras are shown. Update styles if you need more.");
    }
  }

  window.addEventListener("beforeunload", () => {
    players.forEach((player) => player.destroy());
  });

  init();
  setInterval(() => window.location.reload(), AUTO_REFRESH_MS);
})();
