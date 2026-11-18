"""Serve the compiled React application from the same origin as the REST API."""
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_frontend(app, directory: Path | None):
    if directory is None:
        return
    root = directory.resolve()
    index = root / 'index.html'
    if not index.is_file():
        raise RuntimeError('FRONTEND_DIST does not contain a compiled frontend index.html.')
    if (root / 'assets').is_dir():
        app.mount('/assets', StaticFiles(directory=root / 'assets'), name='frontend-assets')

    @app.get('/{path:path}', include_in_schema=False)
    def react_page(path: str):
        if path == 'api' or path.startswith('api/'):
            raise HTTPException(404, 'API endpoint not found')
        target = (root / path).resolve()
        if not target.is_relative_to(root):
            raise HTTPException(404, 'Not found')
        if target.is_file():
            return FileResponse(target)
        if Path(path).suffix:
            raise HTTPException(404, 'File not found')
        return FileResponse(index, headers={'Cache-Control': 'no-cache'})
