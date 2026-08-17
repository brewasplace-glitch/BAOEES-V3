from __future__ import annotations
import json, mimetypes, os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

HOST='127.0.0.1'
PORT=int(os.environ.get('PHOENIX_MEDIA_PLAYER_PORT','8770'))
REPO=Path(os.environ.get('PHOENIX_REPO',r'C:\\PROJECT-PHOENIX')).resolve()
PLAYER_ROOT=(REPO/'phoenix'/'media_player'/'web').resolve()
ALLOWED_ROOTS=[(REPO/'projects'/'runtime').resolve(),(REPO/'outputs').resolve(),PLAYER_ROOT]

def safe_resolve(rel):
    rel=unquote(rel or '').replace('\\\\','/').lstrip('/')
    candidate=(REPO/rel).resolve()
    for root in ALLOWED_ROOTS:
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            pass
    raise PermissionError('path outside allowed Phoenix media roots')

def copyfileobj(src,dst,length=1024*1024):
    while True:
        chunk=src.read(length)
        if not chunk: break
        dst.write(chunk)

class Handler(SimpleHTTPRequestHandler):
    server_version='PhoenixOpenSourceMediaPlayer/1.0'
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin','http://127.0.0.1:8765')
        self.send_header('Access-Control-Allow-Methods','GET, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
    def do_OPTIONS(self):
        self.send_response(204);self._cors();self.end_headers()
    def do_HEAD(self):
        u=urlparse(self.path)
        if u.path!='/media':
            self.send_error(404);return
        rel=(parse_qs(u.query).get('path') or [''])[0]
        try:p=safe_resolve(rel)
        except PermissionError:self.send_error(403);return
        if not p.is_file():self.send_error(404);return
        self.send_response(200)
        self.send_header('Content-Type',mimetypes.guess_type(str(p))[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(p.stat().st_size))
        self._cors();self.end_headers()
    def do_GET(self):
        u=urlparse(self.path)
        if u.path=='/health':
            body=json.dumps({'ok':True,'engine':'PHOENIX_OPEN_SOURCE_MEDIA_PLAYER','port':PORT}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)));self._cors();self.end_headers();self.wfile.write(body);return
        if u.path=='/media':
            rel=(parse_qs(u.query).get('path') or [''])[0]
            try:p=safe_resolve(rel)
            except PermissionError:self.send_error(403);return
            if not p.is_file():self.send_error(404);return
            self.send_response(200)
            self.send_header('Content-Type',mimetypes.guess_type(str(p))[0] or 'application/octet-stream')
            self.send_header('Content-Length',str(p.stat().st_size))
            self.send_header('Cache-Control','no-store');self._cors();self.end_headers()
            with p.open('rb') as f:copyfileobj(f,self.wfile)
            return
        if u.path in ('/','/player','/player/'):
            self._send_file(PLAYER_ROOT/'index.html');return
        if u.path.startswith('/player/'):
            p=(PLAYER_ROOT/u.path[len('/player/'):]).resolve()
            try:p.relative_to(PLAYER_ROOT)
            except ValueError:self.send_error(403);return
            self._send_file(p);return
        self.send_error(404)
    def _send_file(self,p):
        if not p.is_file():self.send_error(404);return
        data=p.read_bytes()
        self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(str(p))[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store')
        self._cors();self.end_headers();self.wfile.write(data)
    def log_message(self,fmt,*args):
        print('[PHOENIX-MEDIA]',fmt%args)

if __name__=='__main__':
    PLAYER_ROOT.mkdir(parents=True,exist_ok=True)
    print(f'PHOENIX OPEN-SOURCE MEDIA PLAYER listening on http://{HOST}:{PORT}')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
