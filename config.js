window.NVR_CONFIG = {
  nvrIp: "192.168.1.126",
  port: 1935,
  protocol: "http", // http or https depending on how you expose your NVR
  username: "",
  password: "",
  streamProfile: "main", // "main" for highest quality, "sub" for low-bandwidth
  useWorker: false, // set to true only if your browser supports Web Worker + MSE combo
  useProxy: true, // flip to true if you're running server.py and want browser requests to stay on localhost
  proxyOrigin: "", // optional override (defaults to window.location.origin when useProxy is true)
  cameras: [
    { name: "Front Drive", channel: 0 , streamName: "channel0_main.bcs"},
    { name: "Garage Entrance", channel: 1 , streamName: "channel1_main.bcs"},
    { name: "Front Door", channel: 2 , streamName: "channel2_main.bcs"},
    { name: "Circle Drive", channel: 4, streamName: "channel4_ext.bcs" }
  ]
};
