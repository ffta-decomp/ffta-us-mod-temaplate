#!/usr/bin/env python3
"""Copy a battery save between the stock and recruit naming Flash layouts."""
import argparse
from pathlib import Path

BANK_BYTES = 64 * 1024


def convert(source, destination, action):
    payload = source.read_bytes()
    if action == 'expand':
        if len(payload) == BANK_BYTES:
            payload += b'\xff' * BANK_BYTES
        elif len(payload) != 2 * BANK_BYTES:
            raise ValueError('Expected a raw 64 or 128 KiB battery save')
    elif action == 'rollback':
        if len(payload) != 2 * BANK_BYTES:
            raise ValueError('Expected a raw 128 KiB battery save')
        payload = payload[:BANK_BYTES]
    else:
        raise ValueError('Unknown save action')
    with destination.open('xb') as result:
        result.write(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('expand', 'rollback'))
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    try:
        convert(args.source, args.destination, args.action)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
