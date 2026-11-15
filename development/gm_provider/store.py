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
import os
import subprocess
from git_errors import GitFailure, diagnostic, OPERATIONS


class Conflict(ValueError):
    """The document changed since it was read."""


class GitRefConflict(GitFailure, Conflict):
    """A verified Git ref rejection, distinct from a verified competing lease."""


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


class GitStore:
    """The same documents as files in a git branch that every GM session and client clone shares.

    One environment is one directory in the branch:  <scope>/campaign/  (an isolated campaign copy)
    and  <scope>/store/  (queue rows, the lease, routing, published public pages). A write is a
    commit pushed without force; git refusing a non-fast-forward push IS the compare-and-set. Because
    the queue and the ledger travel in the same commits, the queue can never be ahead of, or
    independent from, the ledger it describes: there is one history and it is the campaign's.

    `checkpoint` pushes whatever the gateway has durably accepted under the scope (fixed tables, dice
    logs and receipts, the ledger batch) so a different session that takes over later starts from it.
    Needs only git access to the branch: no server, no database, no model credential.
    """
    def __init__(self, scope, remote="origin", branch=None, min_sync_s=2.0, author="Genesis gateway <gateway@genesis.invalid>", git_timeout=30):
        import subprocess
        import time
        self._run, self._time = subprocess.run, time
        self.git_timeout = git_timeout
        self.scope = __import__("pathlib").Path(scope).resolve()
        self.directory = self.scope / "store"
        self.repo = __import__("pathlib").Path(self._git_at(self.scope, "rev-parse", "--show-toplevel").strip())
        self.remote = remote
        self.branch = branch or self._git("rev-parse", "--abbrev-ref", "HEAD").strip()
        self.min_sync_s, self.last_sync = min_sync_s, 0.0
        name, _, mail = author.partition(" <")
        self.identity = ["-c", f"user.name={name}", "-c", f"user.email={mail.rstrip('>')}", "-c", "commit.gpgsign=false"]
        self.guard = threading.RLock()

    def _git_at(self, cwd, *args, check=True):
        operation = next((a for a in args if a in OPERATIONS), "git")
        environment = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never", LC_ALL="C")
        try:
            result = self._run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                               timeout=self.git_timeout, env=environment)
        except subprocess.TimeoutExpired as error:
            raise GitFailure(diagnostic(operation, None, error.stderr, error.stdout, timed_out=True)) from None
        except OSError:
            raise GitFailure(diagnostic(operation, None, execution=True)) from None
        if check and result.returncode != 0:
            details = diagnostic(operation, result.returncode, result.stderr, result.stdout)
            raise (GitRefConflict if details["classification"] == "stale_ref" else GitFailure)(details) from None
        return result.stdout if check else result

    def _git(self, *args, check=True):
        return self._git_at(self.repo, *args, check=check)

    def sync(self, force=False):
        """Bring the clone up to the shared branch. Local uncommitted work is kept when it does not overlap."""
        with self.guard:
            if not force and self._time.monotonic() - self.last_sync < self.min_sync_s:
                return
            self._git("fetch", "--quiet", self.remote, self.branch)
            self.last_sync = self._time.monotonic()
            if self._git("rev-list", "--count", f"HEAD..{self.remote}/{self.branch}").strip() != "0":
                merged = self._git("merge", "--ff-only", "--quiet", f"{self.remote}/{self.branch}", check=False)
                if merged.returncode != 0:
                    details = diagnostic("merge", merged.returncode, merged.stderr, merged.stdout)
                    raise (GitRefConflict if details["classification"] == "stale_ref" else GitFailure)(details)
            # An indeterminate push may have reached the server. Never stack more
            # writes on an unconfirmed local commit, including in a new process.
            if self._git("rev-list", "--count", f"{self.remote}/{self.branch}..HEAD").strip() != "0":
                raise GitFailure({"operation":"sync", "exit_code":None, "classification":"sync_required",
                                  "stderr":"local commits are not confirmed on the shared branch; reconcile before writing",
                                  "stdout":"", "timed_out":False, "remote_outcome":"unknown"})

    def _path(self, key):
        return self.directory / (key + ".json")

    def read(self, key):
        with self.guard:
            self.sync()
            path = self._path(key)
            if not path.exists():
                return 0, None
            document = json.loads(path.read_text(encoding="utf-8"))
            return document["version"], document["data"]

    def _push(self, message):
        self._git("add", "-A", "--", str(self.scope))
        changes = self._git("diff", "--cached", "--quiet", "--", str(self.scope), check=False)
        if changes.returncode == 0:
            return True
        if changes.returncode != 1:
            raise GitFailure(diagnostic("diff", changes.returncode, changes.stderr, changes.stdout))
        self._git(*self.identity, "commit", "--quiet", "-m", message, "--", str(self.scope))
        try:
            pushed = self._git("push", "--quiet", self.remote, f"HEAD:{self.branch}", check=False)
            if pushed.returncode != 0:
                details = diagnostic("push", pushed.returncode, pushed.stderr, pushed.stdout)
                raise (GitRefConflict if details["classification"] == "stale_ref" else GitFailure)(details)
        except GitFailure as error:
            error.details["local_commit_reverted"] = False
            if error.details["remote_outcome"] == "rejected":
                try:
                    self._git("reset", "--quiet", "--soft", "HEAD~1")
                    self._git("reset", "--quiet", "--", str(self.scope))
                    error.details["local_commit_reverted"] = True
                except GitFailure as cleanup:
                    error.details["cleanup_failure"] = cleanup.details
            self.last_sync = 0.0
            raise
        return True

    def put(self, key, data, expected):
        with self.guard:
            self.sync(force=True)
            path = self._path(key)
            current = json.loads(path.read_text(encoding="utf-8"))["version"] if path.exists() else 0
            if current != expected:
                raise Conflict(f"{key} changed (expected version {expected}, found {current})")
            path.parent.mkdir(parents=True, exist_ok=True)
            previous = path.read_bytes() if path.exists() else None
            path.write_text(json.dumps({"version": expected+1, "data": data}, ensure_ascii=False, indent=1), encoding="utf-8")
            try:
                self._push(f"{self.scope.name}: {key} v{expected+1}")
            except GitFailure as error:
                if error.details.get("local_commit_reverted"):
                    if previous is None:
                        path.unlink()
                    else:
                        path.write_bytes(previous)
                raise
            return expected+1

    def checkpoint(self, what):
        with self.guard:
            self.sync(force=True)
            self._push(f"{self.scope.name}: accepted {what}")

    def keys(self, prefix):
        with self.guard:
            self.sync()
            if not self.directory.exists():
                return []
            found = [str(p.relative_to(self.directory))[:-5].replace("\\", "/") for p in self.directory.rglob("*.json")]
            return sorted(k for k in found if k.startswith(prefix))

    def close(self):
        pass
