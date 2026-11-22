"""One operation at a time per worktree, across threads and OS processes."""
import fcntl
import json
import os
from pathlib import Path
import threading
import uuid


class WorktreeGuard:
    def __init__(self, path, expected_generation=None, *, initialize=True):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.local = threading.RLock()
        self.depth = threading.local()
        with self:
            marker = self.marker = self.path.with_suffix('.generation.json')
            if initialize and not marker.exists():
                data = json.dumps({'generation': str(uuid.uuid4())}).encode()
                fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data); stream.flush(); os.fsync(stream.fileno())
                directory = os.open(marker.parent, os.O_RDONLY)
                try: os.fsync(directory)
                finally: os.close(directory)
            self.generation, _ = self._read_generation()
        self.expected_generation = expected_generation

    def _read_generation(self):
        try:
            generation = json.loads(self.marker.read_text())['generation']
            if not isinstance(generation, str) or not generation:
                return None, 'marker_unreadable'
            return generation, None
        except FileNotFoundError:
            return None, 'marker_missing'
        except (OSError, ValueError, KeyError, TypeError):
            return None, 'marker_unreadable'
    @property
    def recovery_reason(self):
        """Check under the operation lock. A running worker cannot outlive its marker."""
        current, reason = self._read_generation()
        if reason:
            return reason
        if current != self.generation:
            return 'marker_changed'
        if not self.expected_generation:
            return 'generation_unpinned'
        if current != self.expected_generation:
            return 'generation_mismatch'
        return None

    @property
    def recovery_required(self):
        return self.recovery_reason is not None

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


def for_gateway(gateway, expected_generation=None, *, initialize=True):
    store = gateway.store
    if hasattr(store, 'repo'):
        path = Path(store._git('rev-parse', '--git-path', 'genesis-operation.lock').strip())
        if not path.is_absolute(): path = store.repo / path
    else:  # Isolated test stores only; production build always requires GitStore.
        path = gateway.campaign.parent / 'test-operation.lock'
    return WorktreeGuard(path, expected_generation, initialize=initialize)
