"""Versioned document store used by the gateway for the queue, lease and public pages.

The store carries only what the Datapad database already carries (action rows, the campaign
lease, published public pages, provider routing). It is never a second campaign record: the
ledger in git stays the only canonical truth. Implementations must give compare-and-set
writes; `SqliteStore` is the staging/self-hosted one. The live Datapad database is reachable
only through Claude's ArtifactData tool, so no adapter for it exists outside a Claude session
(see development/PROVIDER_INTERCHANGE.md, release gate G1).
"""
import json
import sqlite3
import threading


class Conflict(ValueError):
    """The document changed since it was read."""


class SqliteStore:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.guard = threading.Lock()
        self.db.execute("CREATE TABLE IF NOT EXISTS documents (key TEXT PRIMARY KEY, version INTEGER, data TEXT)")

    def read(self, key):
        with self.guard:
            row = self.db.execute("SELECT version,data FROM documents WHERE key=?", (key,)).fetchone()
        return (row[0], json.loads(row[1])) if row else (0, None)

    def put(self, key, data, expected):
        with self.guard:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                row = self.db.execute("SELECT version FROM documents WHERE key=?", (key,)).fetchone()
                if (row[0] if row else 0) != expected:
                    raise Conflict(f"{key} changed (expected version {expected})")
                self.db.execute("INSERT INTO documents VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET "
                                "version=excluded.version,data=excluded.data", (key, expected+1, json.dumps(data)))
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
        return expected+1

    def keys(self, prefix):
        with self.guard:
            return [r[0] for r in self.db.execute("SELECT key FROM documents WHERE key LIKE ? ORDER BY key", (prefix+"%",))]

    def close(self):
        self.db.close()
