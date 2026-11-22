import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
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


if __name__ == "__main__":
    unittest.main()
