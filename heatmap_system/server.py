import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as urlparse
import os
from heatmap_service import HeatmapService

class SimpleRequestHandler(BaseHTTPRequestHandler):
    service = HeatmapService()

    def do_GET(self):
        parsed_url = urlparse.urlparse(self.path)
        query = urlparse.parse_qs(parsed_url.query)

        if parsed_url.path == "/heatmap":
            page_id = query.get("page_id", ["unknown"])[0]
            bandwidth = float(query.get("bandwidth", [10])[0])
            grid = float(query.get("grid", [15])[0])

            result_path = self.service.generate_heatmap(page_id, bandwidth, grid)
            if result_path and os.path.exists(result_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                with open(result_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Heatmap not found or no data.")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed_url = urlparse.urlparse(self.path)
        query = urlparse.parse_qs(parsed_url.query)

        if parsed_url.path == "/upload_data":
            page_id = query.get("page_id", ["unknown"])[0]
            content_length = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode("utf-8"))
                points = data.get("points", [])
                self.service.store_raw_data(page_id, points)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Data uploaded successfully.")
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"Error parsing data: {e}".encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

def run_server(host="127.0.0.1", port=8080):
    httpd = HTTPServer((host, port), SimpleRequestHandler)
    print(f"Server started at http://{host}:{port}")
    httpd.serve_forever()
