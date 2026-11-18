"""Optional Windows-only isolated PostgreSQL bootstrap. Docker Compose is preferred.
Downloads official EDB binaries into ignored storage, binds localhost:5433,
and never opens or modifies an existing PostgreSQL data directory.
"""
import argparse
import os
import subprocess
import zipfile
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
STORE=ROOT/'storage/postgres'
URL='https://get.enterprisedb.com/postgresql/postgresql-16.4-1-windows-x64-binaries.zip'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','stop']);args=parser.parse_args()
    if os.name!='nt':raise SystemExit('Use Docker Compose on Linux/macOS.')
    binpath=STORE/'pgsql/bin';data=STORE/'data';STORE.mkdir(parents=True,exist_ok=True)
    if args.action=='stop':
        subprocess.run([str(binpath/'pg_ctl.exe'),'-D',str(data),'stop','-m','fast'],check=True);return
    if not (binpath/'initdb.exe').exists():
        archive=STORE/'binaries.zip'
        print('Downloading official PostgreSQL 16.4 binary archive for local synthetic verification...',flush=True)
        with httpx.stream('GET',URL,follow_redirects=True,timeout=90) as response:
            response.raise_for_status()
            with archive.open('wb') as output:
                for block in response.iter_bytes(1024*1024):output.write(block)
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                if item.filename.startswith(('pgsql/bin/','pgsql/lib/','pgsql/share/')):
                    target=(STORE/item.filename).resolve()
                    if not target.is_relative_to(STORE.resolve()):raise RuntimeError('Unsafe archive entry')
                    bundle.extract(item,STORE)
        archive.unlink()
    if not (data/'PG_VERSION').exists():
        # Trust is limited to loopback and synthetic demo data. Use SCRAM for real deployments.
        subprocess.run([str(binpath/'initdb.exe'),'-D',str(data),'-U','resume','-A','trust','--encoding=UTF8','--locale=C'],check=True)
    status=subprocess.run([str(binpath/'pg_ctl.exe'),'-D',str(data),'status'],capture_output=True)
    if status.returncode!=0:
        subprocess.run([str(binpath/'pg_ctl.exe'),'-D',str(data),'-l',str(STORE/'server.log'),'-o','-h 127.0.0.1 -p 5433','-w','start'],check=True)
    with __import__('psycopg').connect('host=127.0.0.1 port=5433 user=resume dbname=postgres',autocommit=True) as db:
        if not db.execute("SELECT 1 FROM pg_database WHERE datname = 'resume_matcher'").fetchone():db.execute('CREATE DATABASE resume_matcher')
    print('Isolated local PostgreSQL ready on 127.0.0.1:5433 (synthetic local demo only).')


if __name__=='__main__':main()
