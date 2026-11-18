"""Recover missing Windows PostgreSQL utilities via HTTP range requests.
Uses a read-only existing installation as a binary source, never its data.
Only needed on machines whose PostgreSQL install lacks initdb and pg_ctl.
"""
import io
import shutil
import zipfile
from pathlib import Path
import httpx

from local_postgres import URL, STORE


class RemoteArchive(io.RawIOBase):
    def __init__(self,url):
        self.client=httpx.Client(follow_redirects=True,timeout=45)
        self.url=url
        result=self.client.head(url);result.raise_for_status()
        self.size=int(result.headers['content-length']);self.position=0

    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.position

    def seek(self,offset,whence=0):
        self.position=offset if whence==0 else self.position+offset if whence==1 else self.size+offset
        return self.position

    def read(self,size=-1):
        if size<0:size=self.size-self.position
        if not size:return b''
        end=min(self.position+size,self.size)-1
        r=self.client.get(self.url,headers={'Range':f'bytes={self.position}-{end}'})
        if r.status_code!=206:raise RuntimeError('Server did not honor byte range; full bootstrap is required.')
        value=r.content;self.position+=len(value);return value


def main():
    installed=Path('C:/Program Files/PostgreSQL/16')
    if not (installed/'bin/postgres.exe').exists():raise SystemExit('No compatible existing binary source; use the full bootstrap.')
    destination=STORE/'pgsql'
    destination.mkdir(parents=True,exist_ok=True)
    for folder in ['bin','lib','share']:
        shutil.copytree(installed/folder,destination/folder,dirs_exist_ok=True)
    archive=RemoteArchive(URL)
    with zipfile.ZipFile(archive) as bundle:
        for name in ['initdb.exe','pg_ctl.exe','pg_isready.exe']:
            target=destination/'bin'/name
            target.write_bytes(bundle.read('pgsql/bin/'+name))
            print('Recovered',name,flush=True)
    archive.client.close()
    print('Portable utilities ready. Start with scripts/local_postgres.py start.')


if __name__=='__main__':main()
