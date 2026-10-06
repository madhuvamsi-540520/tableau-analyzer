"""Upload validation and hardened .twbx extraction.

Trust nothing: every uploaded file is validated by *content* (not just its
extension) before it is stored or parsed.  A ``.twbx`` is a ZIP package, so it
is opened with explicit zip-bomb (entry-count / per-entry / total-size caps)
and zip-slip (path-traversal) guards before the embedded ``.twb`` is read.

Phase A performs a bounded prefix sniff for the workbook root; full XML
well-formedness is validated by the parser layer (Phase B) using ``defusedxml``.
"""
from __future__ import annotations

import io
import posixpath
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from . import config


class UploadError(Exception):
    """Raised when an upload fails validation (surfaced to the client as a 400)."""


@dataclass
class Packaging:
    """What the upload contained. For a .twb this is trivial; for a .twbx it
    records the embedded workbook plus any bundled flat files / extracts."""

    kind: str                                   # "twb" | "twbx"
    inner_twb_name: str | None = None
    flat_files: list[dict] = field(default_factory=list)   # [{"name", "size"}]
    extracts: list[dict] = field(default_factory=list)     # [{"name", "size"}]
    has_extract: bool = False


def _looks_like_twb(data: bytes) -> bool:
    """Cheap content sniff: a Tableau workbook is XML with a ``<workbook>`` root
    appearing near the top of the file."""
    head = data.lstrip(b"\xef\xbb\xbf").lstrip()          # tolerate BOM / whitespace
    window = data[:65536].lower()
    return (head.startswith(b"<?xml") or head.startswith(b"<workbook")) and b"<workbook" in window


def _validate_size(data: bytes, kind: str) -> None:
    limit = config.MAX_TWBX_BYTES if kind == "twbx" else config.MAX_TWB_BYTES
    if len(data) > limit:
        raise UploadError(
            f"File is too large ({len(data) // (1024 * 1024)} MB; limit {limit // (1024 * 1024)} MB)."
        )


def _is_safe_entry(name: str) -> bool:
    """Reject absolute paths and ``..`` traversal in a zip entry name (zip-slip)."""
    if not name or name.endswith("/"):
        return True  # directory markers are harmless and skipped later
    unified = name.replace("\\", "/")
    if unified.startswith("/") or PurePosixPath(unified).is_absolute():
        return False
    norm = posixpath.normpath(unified)
    return not (norm.startswith("..") or ".." in PurePosixPath(norm).parts)


def _extract_twbx(data: bytes) -> tuple[bytes, Packaging]:
    """Validate a .twbx ZIP and return (inner .twb bytes, packaging info)."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UploadError("Not a valid .twbx package (corrupt or not a ZIP archive).") from exc

    infos = zf.infolist()
    if len(infos) > config.MAX_ZIP_ENTRIES:
        raise UploadError(
            f"Package has too many entries ({len(infos)}; limit {config.MAX_ZIP_ENTRIES})."
        )

    total = 0
    for info in infos:
        if not _is_safe_entry(info.filename):
            raise UploadError(f"Unsafe path in package: {info.filename!r}.")
        if info.file_size > config.MAX_ENTRY_BYTES:
            raise UploadError(f"Entry too large in package: {info.filename!r}.")
        total += info.file_size
        if total > config.MAX_UNZIP_TOTAL_BYTES:
            raise UploadError("Package expands beyond the allowed uncompressed size (possible zip bomb).")

    packaging = Packaging(kind="twbx")
    inner_twb: bytes | None = None

    for info in infos:
        if info.filename.endswith("/"):
            continue
        path = PurePosixPath(info.filename)
        ext = path.suffix.lower()
        base = path.name
        if ext == ".twb" and inner_twb is None:
            with zf.open(info) as fh:
                inner_twb = fh.read(config.MAX_ENTRY_BYTES + 1)
            if len(inner_twb) > config.MAX_ENTRY_BYTES:
                raise UploadError("Embedded workbook is too large.")
            packaging.inner_twb_name = base
        elif ext in config.FLAT_FILE_EXTENSIONS:
            packaging.flat_files.append({"name": base, "size": info.file_size})
        elif ext in config.EXTRACT_EXTENSIONS:
            packaging.extracts.append({"name": base, "size": info.file_size})

    if inner_twb is None:
        raise UploadError("No .twb workbook found inside the .twbx package.")
    if not _looks_like_twb(inner_twb):
        raise UploadError("The workbook inside the .twbx is not a valid Tableau .twb.")

    packaging.has_extract = bool(packaging.extracts)
    return inner_twb, packaging


def validate_and_prepare(filename: str, data: bytes) -> tuple[bytes, Packaging]:
    """Validate an uploaded file and return (workbook_xml_bytes, packaging).

    ``workbook_xml_bytes`` is the ``.twb`` XML to parse: the file itself for a
    ``.twb`` upload, or the extracted embedded workbook for a ``.twbx``.
    """
    ext = PurePosixPath(filename).suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise UploadError(f"Unsupported file type '{ext or filename}'. Upload a .twb or .twbx file.")

    if ext == ".twb":
        _validate_size(data, "twb")
        if not _looks_like_twb(data):
            raise UploadError("This does not look like a Tableau .twb (missing a <workbook> root element).")
        return data, Packaging(kind="twb")

    _validate_size(data, "twbx")
    return _extract_twbx(data)
