#!/usr/bin/env python3
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start a local CORS-enabled web server.')
    parser.add_argument('--port', type=int, default=8000, help='Port to serve on (default: 8000)')
    args = parser.parse_args()
    
    print(f"\n=========================================")
    print(f" Serving Neuroglancer Data on port {args.port}")
    print(f"=========================================")
    print(f"1. Open Chrome/Firefox")
    print(f"2. Go to: https://neuroglancer-demo.appspot.com/")
    print(f"3. Add a new layer with Source: precomputed://http://localhost:{args.port}/precomputed")
    print(f"\nPress Ctrl+C to stop the server.")
    
    try:
        HTTPServer(('localhost', args.port), CORSRequestHandler).serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
