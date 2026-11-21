#!/usr/bin/env python3
"""Build a same-size IPS patch for the authenticated North American cartridge."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from ips import apply_patch, encode_patch

ROOT = Path(__file__).resolve().parents[1]
RETAIL_SHA = '43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19'
BASE = 0x08000000
BODY = 0xE02000
BRIDGE = 0x36D370
FLASH_TABLE = 0xF30000
# Only callers that save live progress or load the selected file. The title
# preview and temporary copies keep their original direct calls.
SAVE_CALLS = (0x649F6, 0x64A82, 0x64B6E, 0xBD268, 0x13997A)
LOAD_CALLS = (0x13AA28, 0x13AAC2)
LINK_SCRIPT = f'''
SECTIONS {{
    .bridge {BASE + BRIDGE:#x} : {{ *(.bridge) }}
    .text {BASE + BODY:#x} : {{ *(.text*) *(.rodata*) }}
    .data : {{ *(.data*) }}
    .bss : {{ *(.bss*) *(COMMON) }}
    /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }}
}}
ASSERT(SIZEOF(.data) == 0 && SIZEOF(.bss) == 0, "Unexpected RAM section")
ASSERT(SIZEOF(.text) <= 0x2000 && SIZEOF(.bridge) <= 0x100, "ROM reservation exceeded")
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def thumb_bl(offset, target):
    delta = (target & ~1) - (BASE + offset + 4)
    if delta & 1 or not -0x400000 <= delta < 0x400000:
        raise ValueError('Thumb call destination out of range')
    return struct.pack('<HH', 0xf000 | ((delta >> 12) & 0x7ff),
                       0xf800 | ((delta >> 1) & 0x7ff))


def english_tokens(text):
    alphabet = {character: 0x80B0 + index for index, character in
                enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')}
    alphabet.update({' ': 0x4073, '?': 0x80EA, '.': 0x80E4})
    return b''.join(alphabet[character].to_bytes(2, 'big') for character in text)


def build_header(rom):
    names = struct.unpack_from('<725I', rom, 0x5680DC)
    page = struct.unpack_from('<I', rom, 0x36D67C)[0] - BASE
    first, end = struct.unpack_from('<HH', rom, page + 21 * 2)
    original = rom[page + first + 2:page + end]
    choice = original[original.index(b'\x40\x6e\x40\x53'):]
    messages = {
        'recruit_question_prefix': english_tokens('Welcome ') + b'\x00',
        'recruit_question_suffix': english_tokens(' to clan?') + choice,
        'recruit_joined_suffix': english_tokens(' joined the clan.') + b'\x40\x77\x40\x63\x00',
    }
    rows = [f'#define NAMES_FIRST {min(names):#x}u', f'#define NAMES_END {max(names) + 1:#x}u']
    for name, data in messages.items():
        items = ', '.join(f'{value:#04x}' for value in data)
        rows.append(f'static const u8 {name}[] = {{ {items} }};')
    return '\n'.join(rows) + '\n'


def assemble(rom, clang, prefix):
    with tempfile.TemporaryDirectory(prefix='ffta-recruit-') as tmp:
        work = Path(tmp)
        (work / 'build_bindings.h').write_text(build_header(rom))
        (work / 'recruit.ld').write_text(LINK_SCRIPT)
        subprocess.run([clang, '--target=arm-none-eabi', '-mcpu=arm7tdmi', '-mthumb',
                        '-Os', '-std=c11', '-ffreestanding', '-fno-builtin',
                        '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
                        '-Wall', '-Wextra', '-Werror', '-I', tmp, '-c',
                        ROOT / 'src/recruit.c', '-o', work / 'recruit.o'], check=True)
        elf = work / 'recruit.elf'
        subprocess.run([prefix + 'ld', '-T', work / 'recruit.ld',
                        work / 'recruit.o', '-o', elf], check=True)
        symbols = {}
        for row in subprocess.check_output([prefix + 'nm', '-n', elf], text=True).splitlines():
            fields = row.split()
            if len(fields) == 3 and fields[1] in ('T', 't'):
                symbols[fields[2]] = int(fields[0], 16) | 1
        sections = {}
        for name in ('text', 'bridge'):
            target = work / f'{name}.bin'
            subprocess.run([prefix + 'objcopy', '-O', 'binary', '-j', '.' + name,
                            elf, target], check=True)
            sections[name] = target.read_bytes()
    return symbols, sections


def install(rom, symbols, sections):
    fragments = []

    def add(name, offset, data, expected=None):
        if not data or offset < 0 or offset + len(data) > len(rom):
            raise ValueError(f'Invalid ROM range for {name}')
        if expected is not None and rom[offset:offset + len(data)] != expected:
            raise ValueError(f'Unexpected ROM bytes at {offset:#x} for {name}')
        fragments.append((offset, name, data))

    def redirect(name, offset, target, original):
        add(name, offset, thumb_bl(offset, symbols[target]), thumb_bl(offset, BASE + original))

    for offset, section in ((BODY, 'text'), (BRIDGE, 'bridge')):
        data = sections[section]
        add(section, offset, data, b'\xff' * len(data))
    for offset in (0x70E10, 0x70F58):
        add('recruit scene callback', offset, struct.pack('<I', symbols['RecruitStep']),
            struct.pack('<I', 0x080802E5))
    redirect('dialog text', 0x1181A, 'DialogBridge', 0x18028)
    for offset in (0x743F6, 0x7563C):
        redirect('unit display name', offset, 'RenderNameBridge', 0xC7EA4)
    for offset in (0x807D0, 0x8097E):
        redirect('roster copy', offset, 'AcceptBridge', 0x1443FC)
    for offset, symbol in ((0x227E8, 'MenuHeap'), (0x4CA00, 'MissionHeap'),
                           (0x13C064, 'SaveHeap')):
        # Thumb LDR/BX enters the C replacement without changing the caller's LR.
        add(symbol, offset, struct.pack('<HHI', 0x4b00, 0x4718, symbols[symbol]))
    for offset in SAVE_CALLS:
        redirect('save companion block', offset, 'SaveBridge', 0x13B0D4)
    for offset in LOAD_CALLS:
        redirect('load companion block', offset, 'LoadBridge', 0x13B480)

    # Preserve the original Flash entries and the native 64 KiB sector layout.
    # Sanyo 1 Mbit shares the Panasonic command protocol used by the descriptor.
    original_table = rom[0x36CE38:0x36CE48]
    alias = bytearray(rom[0x36CF64:0x36CF64 + 44])
    struct.pack_into('<H', alias, 40, 0x1362)
    table = original_table[:12] + struct.pack('<I', BASE + FLASH_TABLE + 20) + original_table[12:] + alias
    add('Flash descriptor', FLASH_TABLE, table, b'\xff' * len(table))
    add('Flash lookup pointer', 0x141DC4, struct.pack('<I', BASE + FLASH_TABLE),
        struct.pack('<I', 0x0836CE38))
    add('Flash 1 Mbit marker', 0x36CE28, b'FLASH1M_V103' + bytes(4),
        b'FLASH512_V130' + bytes(3))

    patched = bytearray(rom)
    previous_end = 0
    ranges = []
    for offset, name, data in sorted(fragments):
        end = offset + len(data)
        if offset < previous_end:
            raise ValueError(f'Overlapping ROM fragments at {offset:#x}')
        patched[offset:end] = data
        ranges.append(dict(name=name, start=f'{offset:#08x}', end=f'{end:#08x}'))
        previous_end = end
    return bytes(patched), ranges


def build(rom, clang, prefix):
    if len(rom) != 0x1000000 or sha(rom) != RETAIL_SHA:
        raise ValueError('Expected the original 16 MiB North American ROM with game code AFXE')
    symbols, sections = assemble(rom, clang, prefix)
    patched, ranges = install(rom, symbols, sections)
    patch = encode_patch(rom, patched)
    if apply_patch(rom, patch) != patched:
        raise ValueError('IPS round trip failed')
    return patch, {
        'base_sha256': RETAIL_SHA,
        'patched_sha256': sha(patched),
        'patch_sha256': sha(patch),
        'rom_bytes': len(patched),
        'patched_bytes': sum(a != b for a, b in zip(rom, patched)),
        'recruit_body_bytes': len(sections['text']),
        'near_bridge_bytes': len(sections['bridge']),
        'touched_ranges': ranges,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retail', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='Output IPS outside the source tree')
    parser.add_argument('--clang', default='clang')
    parser.add_argument('--tool-prefix', default='arm-none-eabi-')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT):
        parser.error('Generated patches must stay outside the source tree')
    try:
        patch, report = build(args.retail.read_bytes(), args.clang, args.tool_prefix)
        with args.output.open('xb') as dest:
            dest.write(patch)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
