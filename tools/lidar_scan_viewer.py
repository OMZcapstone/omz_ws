#!/usr/bin/env python3
import json
import math
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import rclpy
from sensor_msgs.msg import LaserScan


latest_scan = {
    "frame_id": "",
    "angle_min": 0.0,
    "angle_increment": 0.0,
    "range_min": 0.0,
    "range_max": 0.0,
    "ranges": [],
}
clients = []
lock = threading.Lock()


HTML = b"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>RPLIDAR C1 /scan</title>
  <style>
    html, body { margin: 0; height: 100%; background: #111; color: #ddd; font-family: system-ui, sans-serif; }
    #bar { position: fixed; left: 0; right: 0; top: 0; height: 42px; display: flex; align-items: center; gap: 18px; padding: 0 16px; background: #181818; border-bottom: 1px solid #333; box-sizing: border-box; }
    #canvas { width: 100vw; height: 100vh; display: block; }
    .ok { color: #72e38b; }
    .muted { color: #999; }
  </style>
</head>
<body>
  <canvas id="canvas"></canvas>
  <div id="bar">
    <strong>RPLIDAR C1 /scan</strong>
    <span id="status" class="muted">waiting...</span>
    <span id="meta" class="muted"></span>
  </div>
  <script>
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const statusEl = document.getElementById('status');
    const metaEl = document.getElementById('meta');
    let scan = null;
    let last = 0;

    function resize() {
      canvas.width = Math.floor(window.innerWidth * devicePixelRatio);
      canvas.height = Math.floor(window.innerHeight * devicePixelRatio);
    }
    window.addEventListener('resize', resize);
    resize();

    function draw() {
      requestAnimationFrame(draw);
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2 + 28 * devicePixelRatio;
      ctx.fillStyle = '#111';
      ctx.fillRect(0, 0, w, h);

      const r = Math.min(w, h) * 0.42;
      ctx.strokeStyle = '#2d2d2d';
      ctx.lineWidth = devicePixelRatio;
      for (let i = 1; i <= 4; i++) {
        ctx.beginPath();
        ctx.arc(cx, cy, r * i / 4, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.strokeStyle = '#333';
      ctx.beginPath();
      ctx.moveTo(cx - r, cy);
      ctx.lineTo(cx + r, cy);
      ctx.moveTo(cx, cy - r);
      ctx.lineTo(cx, cy + r);
      ctx.stroke();

      if (!scan) return;
      const maxRange = Math.min(scan.range_max || 16, 8);
      ctx.fillStyle = '#48d7ff';
      for (let i = 0; i < scan.ranges.length; i++) {
        const dist = scan.ranges[i];
        if (!Number.isFinite(dist) || dist < scan.range_min || dist > scan.range_max) continue;
        const a = scan.angle_min + i * scan.angle_increment;
        const rr = Math.min(dist, maxRange) / maxRange * r;
        const x = cx + Math.cos(a) * rr;
        const y = cy + Math.sin(a) * rr;
        ctx.fillRect(x - 1.5 * devicePixelRatio, y - 1.5 * devicePixelRatio, 3 * devicePixelRatio, 3 * devicePixelRatio);
      }

      ctx.fillStyle = '#ffcc66';
      ctx.beginPath();
      ctx.arc(cx, cy, 5 * devicePixelRatio, 0, Math.PI * 2);
      ctx.fill();
    }
    draw();

    const events = new EventSource('/events');
    events.onmessage = (event) => {
      scan = JSON.parse(event.data);
      const now = performance.now();
      const hz = last ? (1000 / (now - last)).toFixed(1) : '-';
      last = now;
      statusEl.textContent = 'live';
      statusEl.className = 'ok';
      metaEl.textContent = `${scan.frame_id} | ${scan.ranges.length} samples | ${hz} Hz`;
    };
  </script>
</body>
</html>
"""


class ScanNode:
    def __init__(self):
        self.node = rclpy.create_node("lidar_scan_web_viewer")
        self.sub = self.node.create_subscription(LaserScan, "/scan", self.scan_cb, 10)

    def scan_cb(self, msg):
        step = max(1, len(msg.ranges) // 720)
        data = {
            "frame_id": msg.header.frame_id,
            "angle_min": msg.angle_min,
            "angle_increment": msg.angle_increment * step,
            "range_min": msg.range_min,
            "range_max": msg.range_max,
            "ranges": [
                r if math.isfinite(r) else None
                for r in msg.ranges[::step]
            ],
        }
        payload = json.dumps(data).encode()
        with lock:
            dead = []
            for client in clients:
                try:
                    client.put_nowait(payload)
                except queue.Full:
                    dead.append(client)
            for client in dead:
                clients.remove(client)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(HTML)))
            self.end_headers()
            self.wfile.write(HTML)
            return
        if self.path == "/events":
            q = queue.Queue(maxsize=4)
            with lock:
                clients.append(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            try:
                while True:
                    payload = q.get(timeout=15)
                    self.wfile.write(b"data: " + payload.replace(b"NaN", b"null") + b"\n\n")
                    self.wfile.flush()
            except Exception:
                with lock:
                    if q in clients:
                        clients.remove(q)
            return
        self.send_error(404)

    def log_message(self, fmt, *args):
        return


def main():
    rclpy.init()
    scan_node = ScanNode()
    ros_thread = threading.Thread(target=rclpy.spin, args=(scan_node.node,), daemon=True)
    ros_thread.start()
    server = ThreadingHTTPServer(("0.0.0.0", 8765), Handler)
    print("Open http://localhost:8765", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
