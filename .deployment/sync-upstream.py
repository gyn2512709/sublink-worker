"""Mirror upstream source while retaining this installation's deployment policy."""
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = 'https://github.com/7Sageer/sublink-worker.git'
PROTECTED_DIRS = {'.github', '.deployment', 'personal'}
PROTECTED_FILES = {'wrangler.toml', 'wrangler.json', 'wrangler.jsonc', '.gitmodules'}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def protected(name):
    path = PurePosixPath(name)
    return path.parts[0] in PROTECTED_DIRS or name in PROTECTED_FILES


def destination(name):
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ('..', '.git') for p in path.parts):
        raise ValueError('Unsafe upstream path')
    target = ROOT.joinpath(*path.parts)
    if not target.resolve().is_relative_to(ROOT):
        raise ValueError('Path escaped the checkout')
    if any(p.is_symlink() for p in [target, *target.parents] if p != ROOT.parent):
        raise ValueError('Symbolic links are not supported')
    return target


def main():
    subprocess.run(['git', '-C', str(ROOT), 'fetch', '--depth=1', UPSTREAM, 'main'], check=True)
    sha = git('rev-parse', 'FETCH_HEAD').decode().strip()
    marker = ROOT / '.deployment/upstream.json'
    prior = json.loads(marker.read_text()) if marker.exists() else {}
    changed = prior.get('sha') != sha
    if changed:
        archive = tarfile.open(fileobj=io.BytesIO(git('archive', '--format=tar', sha)), mode='r:')
        members = [m for m in archive.getmembers() if not m.isdir() and not protected(m.name)]
        if any(not m.isfile() for m in members):
            raise ValueError('Upstream contains non-regular files')
        incoming = {m.name for m in members}
        if not {'src/worker.jsx', 'package.json', 'package-lock.json'} <= incoming:
            raise ValueError('Upstream layout changed; refusing an incompatible deployment')
        tracked = git('ls-files', '-z').decode().split('\0')
        # Only remove tracked source files, never local secrets or deployment state.
        for name in tracked:
            if name and not protected(name) and name not in incoming:
                destination(name).unlink(missing_ok=True)
        for member in members:
            target = destination(member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
            if os.name != 'nt':
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
        marker.write_text(json.dumps({'repository': UPSTREAM, 'branch': 'main', 'sha': sha}, indent=2) + '\n')
    # A weekly metadata commit prevents inactivity from disabling the public-repo schedule.
    week = datetime.now(timezone.utc).strftime('%G-W%V')
    (ROOT / '.deployment/sync-state.json').write_text(json.dumps({'checkedWeek': week}) + '\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write(f'changed={str(changed).lower()}\nsha={sha}\n')
    print(json.dumps({'upstreamChanged': changed, 'sha': sha}))


if __name__ == '__main__':
    main()
