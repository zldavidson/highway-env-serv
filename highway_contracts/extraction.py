"""Uncached PDF extraction; callers own hash/version caching and persistence."""

from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

from pypdf import PdfReader, PdfWriter


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    method: str
    quality_flags: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    original_path: Path
    derivative_path: Path | None
    engine_version: str
    pages: list[ExtractedPage] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)


def _version(package):
    try:
        return version(package)
    except PackageNotFoundError:
        return 'unavailable'


def _has_images(resources, seen=None):
    """Inspect image and nested Form resources without decoding image data."""
    seen = set() if seen is None else seen
    if not resources:
        return False
    resources = resources.get_object()
    if id(resources) in seen:
        return False
    seen.add(id(resources))
    objects = resources.get('/XObject', {})
    objects = objects.get_object() if hasattr(objects, 'get_object') else objects
    for reference in objects.values():
        obj = reference.get_object()
        if obj.get('/Subtype') == '/Image':
            return True
        if obj.get('/Subtype') == '/Form' and _has_images(obj.get('/Resources'), seen):
            return True
    return False


def extract_pdf(original_path: Path, *, output_dir: Path, ocr: str = 'auto') -> ExtractionResult:
    """Extract original pages, optionally OCR suspect pages using local OCRmyPDF.

    ``required`` demands available OCR for suspect pages, not rasterization of
    legible text pages. Failures are returned as error diagnostics. Image-bearing
    pages are conservative review candidates, including mixed text/image pages;
    this is not a guarantee that all scanned/vector/inline-image text is detected.
    """
    if ocr not in {'auto', 'off', 'required'}:
        raise ValueError('ocr must be auto, off, or required')
    original_path = Path(original_path).resolve()
    output_dir = Path(output_dir).resolve()
    command = shutil.which('ocrmypdf')
    available = bool(command and shutil.which('tesseract'))
    result = ExtractionResult(
        original_path, None,
        f'extraction/1;pypdf/{_version("pypdf")};ocrmypdf/{_version("ocrmypdf")};'
        f'ocr={ocr};available={available}',
    )

    def diagnostic(code, message, page=None, severity='warning'):
        result.diagnostics.append(dict(code=code, message=message,
                                       page_number=page, severity=severity))

    try:
        reader = PdfReader(original_path)
        if reader.is_encrypted and not reader.decrypt(''):
            diagnostic('encrypted_pdf', 'A password is required to extract this PDF.', severity='error')
            return result
        count = len(reader.pages)
    except Exception as exc:
        diagnostic('pdf_read_failed', str(exc), severity='error')
        return result

    replacements = {}
    # Temporary derivatives are isolated; original_path is never written.
    with tempfile.TemporaryDirectory(prefix='highway-extraction-') as temporary:
        work = Path(temporary)
        for number in range(1, count + 1):
            extracted = ExtractedPage(number, '', 'failed')
            result.pages.append(extracted)
            try:
                page = reader.pages[number - 1]
                extracted.text = page.extract_text() or ''
                extracted.method = 'text'
                images = _has_images(page.get('/Resources'))
                low_text = len(extracted.text.strip()) < 30
                if low_text:
                    extracted.quality_flags.append('low_text')
                if images:
                    extracted.quality_flags.append('image_content_review')
                if page.get('/Rotate', 0) % 360:
                    extracted.quality_flags.append('rotated_page')
            except Exception as exc:
                extracted.quality_flags.append('page_extraction_failed')
                diagnostic('page_extraction_failed', str(exc), number, 'error')
                continue
            if not (low_text or images):
                continue
            if ocr == 'off':
                extracted.quality_flags.append('ocr_disabled')
                continue
            if not available:
                extracted.quality_flags.append('ocr_unavailable')
                diagnostic('ocr_unavailable',
                           'Install local OCRmyPDF, Tesseract and its required native dependencies; '
                           'then rerun extraction for this page.', number,
                           'error' if ocr == 'required' else 'warning')
                continue
            try:
                source = work / f'{number}-input.pdf'
                target = work / f'{number}-ocr.pdf'
                writer = PdfWriter()
                writer.add_page(page)
                with source.open('wb') as stream:
                    writer.write(stream)
                subprocess.run([command, '--force-ocr', '--rotate-pages', '--deskew',
                                '--output-type', 'pdf', str(source), str(target)],
                               check=True, capture_output=True, timeout=300)
                corrected = PdfReader(target)
                if len(corrected.pages) != 1:
                    raise ValueError('OCR changed the page count')
                text = corrected.pages[0].extract_text() or ''
                if not text.strip():
                    raise ValueError('OCR produced no searchable text; inspect the original page')
                replacements[number] = corrected.pages[0]
                extracted.text = text
                extracted.method = 'ocr'
                extracted.quality_flags = ['ocr_review']
                if len(text.strip()) < 30:
                    extracted.quality_flags.append('low_text')
            except Exception as exc:
                extracted.quality_flags.append('ocr_failed')
                diagnostic('ocr_failed', f'Local OCR failed: {exc}. Check OCR dependencies and inspect the page.',
                           number, 'error')
        if replacements:
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                target = output_dir / f'{original_path.stem}.ocr-{uuid.uuid4().hex}.pdf'
                writer = PdfWriter()
                for number, page in enumerate(reader.pages, 1):
                    writer.add_page(replacements.get(number, page))
                with target.open('xb') as stream:
                    writer.write(stream)
                result.derivative_path = target
            except Exception as exc:
                diagnostic('derivative_write_failed', str(exc), severity='error')
                if 'target' in locals() and target.exists():
                    target.unlink()
    return result
