"""Verify the exact published asset/source bytes before any regression test."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'assets/manifest.json').read_text())
for relative, expected in manifest['sha256'].items():
    path = root / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('Asset/source integrity mismatch: ' + relative)
print('Published asset/source hashes verified:', len(manifest['sha256']))
