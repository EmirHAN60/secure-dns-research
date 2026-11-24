"""Offline artifact integrity checks using temporary, non-research fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("package_checks", ROOT / "scripts/validate_package.py")
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)


class PackageIntegrity(unittest.TestCase):
    def test_public_manifest_excludes_private_guide_and_local_dependencies(self):
        with tempfile.TemporaryDirectory(prefix="dns-manifest-test-") as folder:
            root = Path(folder)
            for name in ("README.md", "SON_ADIMLAR_TR.md", ".git/config", "node_modules/example/index.js", "__pycache__/a.pyc", "data/new-run/partial.jsonl"):
                p = root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text("test")
            self.assertEqual([p.relative_to(root).as_posix() for p in V.public_files(root)], ["README.md"])
            self.assertEqual(V.manifest(root, write=True), 1)

    def test_manifest_detects_changed_or_new_public_files(self):
        with tempfile.TemporaryDirectory(prefix="dns-manifest-test-") as folder:
            root = Path(folder); p = root / "README.md"; p.write_text("version one")
            V.manifest(root, write=True)
            p.write_text("changed")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                V.manifest(root)
            V.manifest(root, write=True)
            (root / "extra.txt").write_text("new public artifact")
            with self.assertRaisesRegex(ValueError, "coverage"):
                V.manifest(root)

    def test_protected_inputs_cannot_be_silently_replaced(self):
        with tempfile.TemporaryDirectory(prefix="dns-protected-test-") as folder:
            root = Path(folder); (root / "data").mkdir(); (root / "docs/evidence").mkdir(parents=True)
            raw = root / "data/raw.jsonl"; raw.write_bytes(b"original")
            ledger = {"files": {"data/raw.jsonl": hashlib.sha256(b"original").hexdigest()}}
            (root / "docs/evidence/original-data-sha256.json").write_text(json.dumps(ledger))
            self.assertEqual(V.original_data_checks(root), 1)
            raw.write_bytes(b"replacement")
            with self.assertRaisesRegex(ValueError, "changed"):
                V.original_data_checks(root)

    def test_broken_local_links_fail_without_network_access(self):
        with tempfile.TemporaryDirectory(prefix="dns-links-test-") as folder:
            root = Path(folder)
            (root / "README.md").write_text("[external](https://example.invalid/)\n[missing](docs/absent.md)")
            with self.assertRaisesRegex(ValueError, "Broken local link"):
                V.check_links(root)
            (root / "docs").mkdir(); (root / "docs/absent.md").write_text("now exists")
            self.assertEqual(V.check_links(root), 1)

    def test_local_markdown_fragment_must_resolve_to_heading(self):
        with tempfile.TemporaryDirectory(prefix="dns-links-test-") as folder:
            root = Path(folder)
            readme = root / "README.md"
            readme.write_text("[Check](#method-and-data)\n\n## Method and data\n", encoding="utf-8")
            self.assertEqual(V.check_links(root), 1)
            readme.write_text("[Check](#method-and-data)\n\n## Methods\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing Markdown heading"):
                V.check_links(root)


if __name__ == "__main__":
    unittest.main()
