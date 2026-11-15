"""One operation at a time per worktree, across threads and OS processes."""
import fcntl
import json
import os
from pathlib import Path
import threading
import uuid


class WorktreeGuard:
    def __init__(self, path, expected_generation=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.local = threading.RLock()
        self.depth = threading.local()
        with self:
            marker = self.path.with_suffix('.generation.json')
            if not marker.exists():
                data = json.dumps({'generation': str(uuid.uuid4())}).encode()
                fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data); stream.flush(); os.fsync(stream.fileno())
                directory = os.open(marker.parent, os.O_RDONLY)
                try: os.fsync(directory)
                finally: os.close(directory)
            self.generation = json.loads(marker.read_text())['generation']
        self.recovery_required = self.generation != expected_generation

    def __enter__(self):
        self.local.acquire()
        try:
            if not getattr(self.depth, 'count', 0):
                self.depth.fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
                fcntl.flock(self.depth.fd, fcntl.LOCK_EX)
            self.depth.count = getattr(self.depth, 'count', 0) + 1
            return self
        except BaseException:
            self.local.release()
            raise

    def __exit__(self, *args):
        try:
            self.depth.count -= 1
            if not self.depth.count:
                fcntl.flock(self.depth.fd, fcntl.LOCK_UN)
                os.close(self.depth.fd)
        finally:
            self.local.release()


def for_gateway(gateway, expected_generation=None):
    store = gateway.store
    if hasattr(store, 'repo'):
        path = Path(store._git('rev-parse', '--git-path', 'genesis-operation.lock').strip())
        if not path.is_absolute(): path = store.repo / path
    else:  # Isolated test stores only; production build always requires GitStore.
        path = gateway.campaign.parent / 'test-operation.lock'
    return WorktreeGuard(path, expected_generation)
