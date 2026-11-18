from io import BytesIO
from pathlib import PurePosixPath
import zipfile
import fitz
from docx import Document


class DocumentError(ValueError):
    pass


def safe_filename(name: str) -> str:
    return PurePosixPath(name.replace('\\', '/')).name[:240] or 'document'


def extract_document(name: str, content: bytes, max_mb: int = 10) -> tuple[str, str]:
    if len(content) > max_mb * 1024 * 1024:
        raise DocumentError(f'File exceeds {max_mb} MB limit.')
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in {'.pdf', '.docx'}:
        raise DocumentError('Only PDF and DOCX files are supported.')
    try:
        if suffix == '.pdf':
            if not content.startswith(b'%PDF-'):
                raise DocumentError('File content does not match PDF format.')
            with fitz.open(stream=content, filetype='pdf') as doc:
                if doc.needs_pass:
                    raise DocumentError('Password-protected PDFs are not supported.')
                if len(doc) > 100:
                    raise DocumentError('Document exceeds 100 page limit.')
                text = '\n'.join(page.get_text(sort=True) for page in doc)
            mime = 'application/pdf'
        else:
            if not zipfile.is_zipfile(BytesIO(content)):
                raise DocumentError('File content does not match DOCX format.')
            with zipfile.ZipFile(BytesIO(content)) as z:
                if sum(x.file_size for x in z.infolist()) > 40 * 1024 * 1024:
                    raise DocumentError('Expanded document exceeds safety limit.')
                if 'word/document.xml' not in z.namelist():
                    raise DocumentError('Not a Word DOCX document.')
            doc = Document(BytesIO(content))
            text = '\n'.join([p.text for p in doc.paragraphs] + [' | '.join(c.text for c in row.cells) for t in doc.tables for row in t.rows])
            mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError('Document is corrupted or unreadable.') from exc
    if len(text.strip()) < 20:
        raise DocumentError('OCR required / text not extractable, or document is empty.')
    if len(text) > 200_000:
        raise DocumentError('Extracted text exceeds 200,000 character limit.')
    return text.strip(), mime
