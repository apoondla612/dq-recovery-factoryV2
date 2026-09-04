from __future__ import annotations
import hashlib, json, re, zipfile
from pathlib import Path
from urllib.parse import unquote_plus
from typing import Any

_HEX = re.compile(r"[0-9A-Fa-f]{2}")

def local_name(x: str) -> str:
    return x.split('}')[-1]

def attrs(e):
    return {local_name(k): v for k, v in e.attrib.items()}

def jwrite(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def jread(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def stable_hash_json(obj: Any) -> str:
    return sha256(json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))

def decode_native(raw: str) -> tuple[str, str | None]:
    i = 0
    while i < len(raw):
        if raw[i] == '%':
            if i + 2 >= len(raw) or not _HEX.fullmatch(raw[i + 1:i + 3]):
                return raw, f"malformed percent escape at {i}"
            i += 3
        else:
            i += 1
    return unquote_plus(raw), None

def register_export(export: Path, work: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    members = []
    root = work / 'members'
    root.mkdir(exist_ok=True)
    archive_sha = file_sha256(export)
    with zipfile.ZipFile(export) as z:
        for info in sorted(z.infolist(), key=lambda x: x.filename):
            if info.is_dir() or not info.filename.lower().endswith('.xml'):
                continue
            b = z.read(info.filename)
            parts = Path(info.filename).parts
            rel = Path(*parts[-2:]) if len(parts) >= 2 else Path(info.filename).name
            out = root / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b)
            members.append({
                'name': info.filename,
                'path': str(Path('members') / rel),
                'sha256': sha256(b),
                'bytes': len(b),
            })
    manifest = {
        'kind': 'pilot-source.manifest',
        'archive_name': export.name,
        'archive_sha256': archive_sha,
        'member_count': len(members),
        'members': members,
    }
    jwrite(work / 'pilot-source.manifest.json', manifest)
    return manifest

def load_manifest(path: Path) -> tuple[Path, dict[str, Any]]:
    manifest = jread(path)
    if manifest.get('kind') != 'pilot-source.manifest':
        raise ValueError('not a pilot-source.manifest')
    return path.parent, manifest
