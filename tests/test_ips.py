from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ips import apply_patch, encode_patch


class IpsTests(unittest.TestCase):
    def test_round_trip_and_split_large_records(self):
        before = bytes(72000)
        after = b'\x00\x01' + bytes(16) + b'\x55' * 68000 + bytes(3982)
        self.assertEqual(apply_patch(before, encode_patch(before, after)), after)

    def test_rejects_out_of_bounds_record(self):
        with self.assertRaises(ValueError):
            apply_patch(bytes(10), b'PATCH\x00\x00\x0a\x00\x01aEOF')
