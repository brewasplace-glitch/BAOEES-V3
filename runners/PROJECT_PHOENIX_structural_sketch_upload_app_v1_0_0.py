"""Local-only Phoenix sketch upload application."""
from __future__ import annotations
import argparse, cgi, html, json, os, secrets, sys, tempfile, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from phoenix.structural.regional_profiles import RegionalStructuralProfileRegistry
from phoenix.structural.sketch_input_recognition import SketchInputRecognitionEngine, render_preview_svg
REG=RegionalStructuralProfileRegistry(ROOT/'configs/structural/regional_structural_profiles_v1_0_0.json')
TOKEN=secrets.token_urlsafe(24); UPLOAD_ROOT=ROOT/'outputs/runtime/structural_sketch_input_v1_0_0/uploads'; UPLOAD_ROOT.mkdir(parents=True,exist_ok=True)
PAGE="""<!doctype html><html><head><meta charset="utf-8"><title>Phoenix sketch input</title><style>body{font-family:Arial;max-width:980px;margin:30px auto}label{display:block;margin-top:12px}input,select,textarea{width:100%;padding:9px}.card{border:1px solid #ccd3df;padding:18px;border-radius:12px;margin:15px 0}button{padding:12px 20px;margin-top:15px}</style></head><body><h1>Phoenix structural sketch upload</h1><div class="card"><form method="post" enctype="multipart/form-data" action="/recognize"><input type="hidden" name="token" value="TOKEN"><label>Jurisdiction</label><select name="jurisdiction">OPTIONS</select><label>Sketch (PNG/JPG/BMP/TIFF/PDF, max 25 MB)</label><input type="file" name="sketch" required><label>Optional OCR text / manual transcription</label><textarea name="ocr_text" rows="8" placeholder="L=5.0 m; q=12 kN/m; P1=25 kN @ 2.0 m; 300x500 mm; C30/37; B500B; cover=40 mm; support A pin; support B roller"></textarea><button type="submit">Recognize sketch</button></form></div><p>Recognition never silently starts a structural calculation. Confirm/correct all values first. Final use requires local engineer approval.</p></body></html>"""
OPTIONS=''.join(f'<option value="{html.escape(p["jurisdiction_code"])}">{html.escape(p["jurisdiction"])}</option>' for p in REG.describe())
PAGE=PAGE.replace('TOKEN',TOKEN).replace('OPTIONS',OPTIONS)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path!='/': self.send_error(404); return
        data=PAGE.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        if self.path!='/recognize': self.send_error(404); return
        form=cgi.FieldStorage(fp=self.rfile,headers=self.headers,environ={'REQUEST_METHOD':'POST','CONTENT_TYPE':self.headers.get('Content-Type','')})
        if form.getfirst('token')!=TOKEN: self.send_error(403); return
        item=form['sketch']; filename=Path(item.filename or 'upload.bin').name; target=UPLOAD_ROOT/(secrets.token_hex(6)+'_'+filename)
        with target.open('wb') as fh: fh.write(item.file.read(25*1024*1024+1))
        try:
            result=SketchInputRecognitionEngine(ROOT).recognize(target,form.getfirst('jurisdiction','SUR'),form.getfirst('ocr_text',''),None)
            candidate=html.escape(json.dumps(result['candidate'],ensure_ascii=False,indent=2)); svg=render_preview_svg(result)
            body=f'<html><body style="font-family:Arial;max-width:1100px;margin:25px auto"><h1>Recognition result</h1><p><b>Status:</b> confirmation required</p>{svg}<h2>Candidate JSON</h2><pre>{candidate}</pre><p>Copy these values into a confirmation JSON or use the Phoenix workflow. No calculation has been released.</p><p><a href="/">Back</a></p></body></html>'
            data=body.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
        except Exception as exc:
            self.send_error(400,str(exc))
    def log_message(self,fmt,*args): pass

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--host',default='127.0.0.1'); ap.add_argument('--port',type=int,default=8771); args=ap.parse_args()
    if args.host!='127.0.0.1': raise SystemExit('External bind rejected')
    server=ThreadingHTTPServer((args.host,args.port),Handler); threading.Timer(0.5,lambda:webbrowser.open(f'http://{args.host}:{server.server_port}/')).start(); print(f'Phoenix sketch upload app: http://{args.host}:{server.server_port}/'); server.serve_forever()
if __name__=='__main__': main()
