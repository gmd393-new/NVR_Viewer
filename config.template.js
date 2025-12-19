window.NVR_CONFIG = {
  nvrIp: "CHANGE_ME",
  port: 1935,
  proxyOrigin: "", // optional override (defaults to window.location.origin while using the proxy)
  cameras: [
    { name: "Front Drive", channel: 0, streamName: "channel0_main.bcs" },
    { name: "Garage Entrance", channel: 1, streamName: "channel1_main.bcs" },
    { name: "Front Door", channel: 2, streamName: "channel2_main.bcs" },
    { name: "Circle Drive", channel: 4, streamName: "channel4_ext.bcs" }
  ]
};
