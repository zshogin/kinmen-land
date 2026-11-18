import http.server
import socketserver
import urllib.request
import urllib.parse
import ssl
import sys
import os

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

class ProxyAndStaticHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/proxy':
            query = urllib.parse.parse_qs(parsed.query)
            target_url = query.get('url', [None])[0]
            if not target_url:
                self.send_error(400, "Missing url parameter")
                return
            try:
                req = urllib.request.Request(target_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                })
                with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
                    data = resp.read()
                    content_type = resp.headers.get('Content-Type', 'application/json')
                    self.send_response(resp.status)
                    self.send_header('Content-Type', content_type)
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                self.send_error(500, f"Proxy error: {str(e)}")
        else:
            super().do_GET()

if __name__ == '__main__':
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), ProxyAndStaticHTTPHandler) as httpd:
        print(f"Kinmen Land Cloud Prototype Server running at http://localhost:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Stopping server...")
