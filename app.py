"""Servidor local del dashboard; ejecutar: python app.py --port 8501."""
import argparse
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8501);args=p.parse_args()
    directory=Path(__file__).resolve().parent/'dashboard'
    if not (directory/'index.html').exists():raise SystemExit('Primero ejecute: python -m src.reproducir')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(directory)))
    print(f'Dashboard: http://127.0.0.1:{args.port}/',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
