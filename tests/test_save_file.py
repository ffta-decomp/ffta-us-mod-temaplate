from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from save_file import BANK_BYTES, convert


class SaveFileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        base = Path(self.directory.name)
        self.stock = base / 'stock.sav'
        self.expanded = base / 'expanded.sav'
        self.restored = base / 'restored.sav'
        self.original = bytes(range(256)) * (BANK_BYTES // 256)
        self.stock.write_bytes(self.original)

    def test_expansion_preserves_stock_bank(self):
        convert(self.stock, self.expanded, 'expand')
        self.assertEqual(self.expanded.read_bytes(), self.original + b'\xff' * BANK_BYTES)
        self.assertEqual(self.stock.read_bytes(), self.original)

    def test_rollback_keeps_the_current_stock_bank(self):
        progress = b'\x12' * BANK_BYTES
        self.expanded.write_bytes(progress + b'\x34' * BANK_BYTES)
        convert(self.expanded, self.restored, 'rollback')
        self.assertEqual(self.restored.read_bytes(), progress)
        self.assertEqual(self.expanded.read_bytes()[BANK_BYTES:], b'\x34' * BANK_BYTES)

    def test_can_copy_an_existing_expanded_save(self):
        content = self.original + b'\x77' * BANK_BYTES
        self.expanded.write_bytes(content)
        convert(self.expanded, self.restored, 'expand')
        self.assertEqual(self.restored.read_bytes(), content)

    def test_existing_destination_is_never_overwritten(self):
        self.expanded.write_bytes(b'retain')
        with self.assertRaises(FileExistsError):
            convert(self.stock, self.expanded, 'expand')
        self.assertEqual(self.expanded.read_bytes(), b'retain')

    def test_wrong_size_and_state_files_are_rejected(self):
        self.stock.write_bytes(b'not a battery save')
        with self.assertRaises(ValueError):
            convert(self.stock, self.expanded, 'expand')
        with self.assertRaises(ValueError):
            convert(self.stock, self.expanded, 'rollback')
        self.assertFalse(self.expanded.exists())
