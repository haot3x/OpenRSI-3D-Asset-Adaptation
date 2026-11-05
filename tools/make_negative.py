"""Remove all animation from a copy; retain the original binary geometry chunk."""
import json
from pathlib import Path
import struct

root = Path(__file__).resolve().parents[1]
raw = (root / 'assets/adapted/asset.glb').read_bytes()
length, kind = struct.unpack_from('<II', raw, 12)
assert kind == 0x4e4f534a
data = json.loads(raw[20:20 + length])
assert data.pop('animations', None)
encoded = json.dumps(data, separators=(',', ':')).encode()
encoded += b' ' * (-len(encoded) % 4)
body = struct.pack('<II', len(encoded), kind) + encoded + raw[20 + length:]
(root / 'assets/negative-static.glb').write_bytes(struct.pack('<4sII', b'glTF', 2, 12 + len(body)) + body)
