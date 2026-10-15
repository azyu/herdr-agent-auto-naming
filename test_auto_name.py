import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

with patch("subprocess.run"), patch.dict(os.environ, {"HERDR_PLUGIN_EVENT_JSON": "{}"}):
    import auto_name


class ThemeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "themes").mkdir()
        config = patch.object(auto_name, "CONFIG_DIR", str(self.root))
        config.start()
        self.addCleanup(config.stop)

    def write(self, path, value):
        (self.root / path).write_text(json.dumps(value), encoding="utf-8")

    def test_default_and_custom_themes(self):
        self.assertEqual(auto_name.load_themes(), auto_name.THEMES)
        custom = {"left": ["sleepy"], "right": ["otter"]}
        self.write("themes/mine.json", custom)
        for names, expected in [
            (["mine"], [(custom["left"], custom["right"])]),
            (["default", "mine"], auto_name.THEMES + [(custom["left"], custom["right"])]),
        ]:
            with self.subTest(names=names):
                self.write("config.json", {"themes": names})
                self.assertEqual(auto_name.load_themes(), expected)

    def test_unset_config_directory_does_not_read_working_directory(self):
        with patch.object(auto_name, "CONFIG_DIR", ""), patch("builtins.open") as opening:
            self.assertEqual(auto_name.load_themes(), auto_name.THEMES)
            opening.assert_not_called()

    def test_invalid_config_falls_back(self):
        for value in [None, {}, {"themes": None}, {"themes": "default"},
                      {"themes": [1]}, {"themes": ["../outside"]}]:
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()) as log:
                self.write("config.json", value)
                self.assertEqual(auto_name.load_themes(), auto_name.THEMES)
                self.assertIn("config.json:", log.getvalue())
        (self.root / "config.json").write_text("{", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as log:
            self.assertEqual(auto_name.load_themes(), auto_name.THEMES)
            self.assertIn("config.json:", log.getvalue())

    def test_invalid_theme_is_skipped(self):
        self.write("config.json", {"themes": ["bad", "mine"]})
        self.write("themes/mine.json", {"left": ["sleepy"], "right": ["otter"]})
        for value in [None, {}, {"left": None, "right": ["otter"]},
                      {"left": "sleepy", "right": ["otter"]},
                      {"left": [1], "right": ["otter"]}]:
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()) as log:
                self.write("themes/bad.json", value)
                self.assertEqual(auto_name.load_themes(), [(["sleepy"], ["otter"])])
                self.assertIn("theme bad:", log.getvalue())
        self.write("config.json", {"themes": ["missing"]})
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(auto_name.load_themes(), auto_name.THEMES)

    def test_mint_excludes_used_and_invalid_names(self):
        self.write("config.json", {"themes": ["mine"]})
        self.write("themes/mine.json", {
            "left": ["angry", "sleepy", "cozy", "INVALID", "x" * 32],
            "right": ["otter"],
        })
        with patch.object(auto_name, "herdr", side_effect=[
            ({"agents": [{"name": "angry-otter"}]}, ""),
            ({"panes": [{"label": "cozy-otter"}]}, ""),
            ({}, ""),
        ]) as herdr, patch.object(auto_name, "claim", return_value=True) as claim:
            self.assertEqual(auto_name.mint("pane"), "sleepy-otter")
            claim.assert_called_once_with("pane", "sleepy-otter")
            self.assertEqual(herdr.call_args.args, ("pane", "rename", "pane", "sleepy-otter"))

    def test_existing_name_and_label_are_preserved(self):
        with patch.object(auto_name, "occupant", return_value={"name": "old-otter"}), \
             patch.object(auto_name, "herdr", return_value=({"pane": {"label": "Reviewer"}}, "")), \
             patch.object(auto_name, "mint") as mint:
            auto_name.name_pane("pane")
            mint.assert_not_called()


if __name__ == "__main__":
    unittest.main()
