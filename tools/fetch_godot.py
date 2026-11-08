"""Fetch the pinned official Linux engine; verify identical bytes on every route."""
import argparse
import hashlib
import subprocess
from pathlib import Path

SHA256 = 'cadd3204e728a35d3f13adb7fd0d7902636b79f6b95c40c265eb73b6c35329e4'
URLS = [
    'https://api.github.com/repos/godotengine/godot-builds/releases/assets/519677358',
    'https://github.com/godotengine/godot-builds/releases/download/4.7.2-stable/Godot_v4.7.2-stable_linux.x86_64.zip',
    'https://github.com/godotengine/godot/releases/download/4.7.2-stable/Godot_v4.7.2-stable_linux.x86_64.zip',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    output = parser.parse_args().output
    temporary = output.with_name(output.name + '.part')
    try:
        for url in URLS:
            result = subprocess.run([
                'curl', '--fail', '--location', '--retry', '1', '--retry-all-errors',
                '--retry-delay', '5', '--connect-timeout', '20', '--max-time', '60',
                '--header', 'Accept: application/octet-stream',
                '--output', str(temporary), url,
            ])
            if result.returncode:
                continue
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != SHA256:
                print('Downloaded response failed the pinned SHA-256; trying another official route.', flush=True)
                continue
            temporary.replace(output)
            print('Verified Godot 4.7.2 archive:', SHA256)
            return
        raise SystemExit('All official download routes failed; no unverified engine accepted.')
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
