import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import test_shared_store as shared_fixture
from test_gateway import HOLSTER
from test_mcp_adapter import access
import uuid

RUNNER = Path(__file__).resolve().parent / "deploy/oracle/run.py"
SPEC = importlib.util.spec_from_file_location("oracle_runner", RUNNER)
oracle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(oracle)
RESOURCE = "https://genesis-test.duckdns.org/mcp"


def write_env(generation=None):
    return {
        "GENESIS_MCP_RESOURCE": RESOURCE,
        "GENESIS_MCP_ENABLE_WRITES": "1",
        "GENESIS_STORAGE_GENERATION": generation or str(uuid.uuid4()),
        "GENESIS_GITHUB_TOKEN": "test-only-git-token",
        "GENESIS_GM_TOKENS": '{"gpt-session":"test-only-gm-token"}',
    }


class OracleRunner(unittest.TestCase):
    def test_default_readonly_and_loopback(self):
        env = {"GENESIS_MCP_RESOURCE": RESOURCE}
        with patch.object(oracle.Path, "is_mount", return_value=True):
            self.assertFalse(oracle.configure(env))
        self.assertEqual(env["GENESIS_MCP_ENABLE_WRITES"], "0")
        self.assertEqual(env["GENESIS_MCP_HOST"], "127.0.0.1")

    def test_missing_mount_and_bad_resources_refused(self):
        with patch.object(oracle.Path, "is_mount", return_value=False), self.assertRaises(ValueError):
            oracle.configure(write_env())
        with patch.object(oracle.Path, "is_mount", return_value=True):
            for url in ("http://a.duckdns.org/mcp", "https://other.example/mcp",
                        "https://u:secret@a.duckdns.org/mcp"):
                with self.subTest(url=url), self.assertRaises(ValueError):
                    oracle.configure({"GENESIS_MCP_RESOURCE": url})

    def test_write_mode_requires_explicit_configuration(self):
        with patch.object(oracle.Path, "is_mount", return_value=True):
            env = write_env()
            self.assertTrue(oracle.configure(env))
            self.assertEqual(env["GIT_CONFIG_VALUE_0"], "")
            for key in ("GENESIS_STORAGE_GENERATION", "GENESIS_GITHUB_TOKEN", "GENESIS_GM_TOKENS"):
                env = write_env()
                del env[key]
                with self.subTest(key=key), self.assertRaises(ValueError):
                    oracle.configure(env)
            for invalid in ("bad-env", "[]", "{}", '{"claude-session":"x"}',
                            '{"gpt-session":"same","gemini-session":"same"}'):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    oracle.configure({**write_env(), "GENESIS_GM_TOKENS": invalid})

    def test_codex_gm_token_is_optional_distinct_and_unknown_providers_still_refused(self):
        with patch.object(oracle.Path, "is_mount", return_value=True):
            # Staging with only GPT remains fully backwards compatible.
            self.assertTrue(oracle.configure(write_env()))
            # A third provider is allowed only by explicit host-side token setup.
            configured={**write_env(), "GENESIS_GM_TOKENS":
                '{"gpt-session":"test-gpt-token","codex-session":"test-codex-token"}'}
            self.assertTrue(oracle.configure(configured))
            for bad in (
                '{"gpt-session":"test-gpt-token","codex-session":"test-gpt-token"}',
                '{"gpt-session":"test-gpt-token","unexpected-session":"test-unknown-token"}',
            ):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    oracle.configure({**write_env(), "GENESIS_GM_TOKENS": bad})

    def test_generation_continuity_and_dry_run_against_real_git(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            remote, repo = root / "remote.git", root / "authority"
            env = dict(os.environ)
            oracle.git(["init", "--bare", str(remote)], root, env)
            oracle.git(["init", str(repo)], root, env)
            oracle.git(["-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "--allow-empty", "-m", "fixture"], repo, env)
            oracle.git(["remote", "add", "origin", str(remote)], repo, env)
            path = repo / ".git/genesis-operation.lock"
            marker = path.with_suffix(".generation.json")
            self.assertEqual(oracle.verify_storage(repo, write_env()), "marker_missing")
            self.assertFalse(marker.exists())
            guard = oracle.WorktreeGuard(path)
            env["GENESIS_STORAGE_GENERATION"] = guard.generation
            self.assertIsNone(oracle.verify_write_startup(repo, env))
            result = subprocess.check_output(["git", "for-each-ref"], cwd=remote, text=True)
            self.assertEqual(result, "")
            marker.unlink()
            with patch.object(oracle, "git") as git:
                self.assertEqual(oracle.verify_write_startup(repo, env), "marker_missing")
                git.assert_not_called()
            self.assertTrue(oracle.WorktreeGuard(path).recovery_required)
            self.assertEqual(oracle.verify_storage(repo, env), "generation_mismatch")

    def test_push_refusal_is_not_swallowed(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            guard = oracle.WorktreeGuard(repo / ".git/genesis-operation.lock")
            oracle.git(["init", str(repo)], repo, os.environ)
            oracle.git(["-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "--allow-empty", "-m", "fixture"], repo, os.environ)
            oracle.git(["remote", "add", "origin", str(repo / "missing-remote")], repo, os.environ)
            with self.assertRaises(oracle.GitFailure):
                oracle.verify_write_startup(repo, write_env(guard.generation))


class RuntimeAuthority(unittest.TestCase):
    setUp = shared_fixture.Shared.setUp
    tearDown = shared_fixture.Shared.tearDown
    clone = shared_fixture.Shared.clone

    def test_restart_preserves_authority_even_with_new_remote_commit(self):
        gateway = self.player
        row = oracle.CAMPAIGN_ID + "-0001"
        import staging
        gateway.submit(staging.declare(gateway, row, text=HOLSTER, provider="gpt-session"))
        repo = gateway.store.repo
        branch = oracle.BRANCH
        remote = self.root / "oracle-origin.git"
        shared_fixture.git(self.root, "init", "--bare", str(remote))
        gateway.store._git("remote", "remove", "origin")
        gateway.store._git("branch", "-m", branch)
        gateway.store._git("remote", "add", "origin", str(remote))
        scope = repo / "staging" / oracle.CAMPAIGN_ID
        gateway.store._git("mv", "staging/env", str(scope))
        manifest = scope / "environment.json"
        environment = json.loads(manifest.read_text())
        environment["campaign_id"] = oracle.CAMPAIGN_ID
        manifest.write_text(json.dumps(environment))
        action = scope / "store/actions" / (row + ".json")
        data = json.loads(action.read_text())
        data["data"]["campaign_id"] = oracle.CAMPAIGN_ID
        action.write_text(json.dumps(data))
        gateway.store._git("add", "staging")
        gateway.store._git(*gateway.store.identity, "commit", "-qm", "Oracle fixture")
        gateway.store._git("push", "-q", "origin", branch)
        guard = oracle.WorktreeGuard(repo / ".git/genesis-operation.lock")
        other = self.root / "remote-update"
        shared_fixture.git(self.root, "clone", "-qb", branch, str(remote), str(other))
        shared_fixture.git(other, "-c", "user.name=t", "-c", "user.email=t@t.invalid",
                           "commit", "--allow-empty", "-qm", "remote-only update")
        shared_fixture.git(other, "push", "-q", "origin", "HEAD:" + branch)

        def snapshot():
            paths = [*scope.rglob("*"), *(repo / ".git").iterdir()]
            return (gateway.store._git("rev-parse", "HEAD"),
                    gateway.store._git("for-each-ref"),
                    {path: path.read_bytes() for path in paths if path.is_file()})

        env = write_env(guard.generation)
        env.update(GENESIS_MCP_CLIENT_PROVIDERS='{"fixture":"gpt-session","fixture-gemini":"gemini-session"}',
                   GENESIS_MCP_ISSUER="https://issuer.example.invalid/",
                   GENESIS_MCP_SUBJECT="owner-fixture")
        before = snapshot()
        with patch.object(oracle, "DATA_ROOT", self.root), \
                patch.object(oracle, "BRANCH", branch), \
                patch.object(oracle, "REPOSITORY", str(remote)), \
                patch.object(oracle.Path, "is_mount", return_value=True), \
                patch.object(oracle.os, "umask"), \
                patch.dict(oracle.os.environ, env), \
                patch("mcp_adapter.create_server") as server:
            repo.rename(self.root / "authority")
            try:
                self.assertEqual(oracle.main([]), 0)
                self.assertEqual(oracle.main([]), 0)
                self.assertEqual(server.return_value.run.call_count, 2)
                self.assertEqual(oracle.main(["--check"]), 0)
                self.assertEqual(server.return_value.run.call_count, 2)
                tools = server.call_args.args[0]
                token = access()
                token.subject = env["GENESIS_MCP_SUBJECT"]
                with patch("mcp_adapter.get_access_token", return_value=token):
                    refreshed = tools.read("refresh")
                pending = refreshed["recovery"]["in_flight"]
                self.assertEqual((pending["action_id"], pending["status"], pending["provider"]),
                                 (row, "submitted", "gpt-session"))
                self.assertFalse(refreshed["recovery"]["lease"]["held"])
                mounted = self.root / "authority"
                dirty = mounted / "unexpected.txt"
                dirty.touch()
                try:
                    self.assertEqual(oracle.main(["--check"]), 2)
                finally:
                    dirty.unlink()
                self.assertEqual(oracle.existing_authority(mounted, write_env())[1],
                                 "generation_mismatch")
            finally:
                (self.root / "authority").rename(repo)
        self.assertEqual(snapshot(), before)

    def test_missing_authority_is_not_initialized(self):
        repo = self.root / "missing"
        with self.assertRaises(ValueError):
            oracle.existing_authority(repo, write_env())
        self.assertFalse(repo.exists())


if __name__ == "__main__":
    unittest.main()
