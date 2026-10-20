import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'bridge'))
import worker

class Configuration(unittest.TestCase):
    def test_explicit_path_has_priority(self):
        with patch.dict(os.environ, {'ELGIN_DEVICES_FILE': '/tmp/custom-devices.json'}):
            self.assertEqual(worker.devices_path(), Path('/tmp/custom-devices.json'))

    def test_xdg_without_legacy_file(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(worker, 'BASE', Path(tmp)/'app'), patch.dict(os.environ, {'XDG_CONFIG_HOME': tmp}, clear=True):
            self.assertEqual(worker.devices_path(), Path(tmp)/'elgin-smart-local/devices.json')

    def test_existing_legacy_configuration_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(worker, 'BASE', Path(tmp)), patch.dict(os.environ, {}, clear=True):
            path=Path(tmp)/'devices.json'
            path.write_text('[]')
            self.assertEqual(worker.devices_path(), path)
