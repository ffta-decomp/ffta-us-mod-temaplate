# FFTA US Recruit Naming

This patch lets you name an ordinary recruit with the original English
keyboard in the North American release of Final Fantasy Tactics Advance.
The editor opens with the candidate's original name and portrait. Press
**START** to confirm the edited name or **SELECT** to keep the original name.
The name is assigned when you accept the recruit and appears in the party
card and unit details.

## Patch the game

1. Back up your original ROM and battery save.
2. Download the IPS patch from [Releases](https://github.com/ffta-decomp/ffta-us-mod-temaplate/releases).
3. Apply it to a clean 16 MiB North American ROM with game code `AFXE` and
   the SHA-256 below. Use a separate filename for the patched ROM.
4. Use **Flash 1 Mbit (128 KiB)**. In mGBA, v1.0.1 expands the save
   automatically at boot with default settings. If your emulator still
   uses 64 KiB, set its cartridge override to Flash 1 Mbit.

```text
43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19
```

## Expand an existing save

Close the emulator or fully unload the game before copying battery saves.
Use a copy of your save with the patched ROM. mGBA preserves the original
64 KiB and fills the added bank with erased bytes. An existing 128 KiB
save from v1.0.0 works without conversion.

For VBA-M or a setup that needs manual migration, expand the save before
importing it. VBA-M can select 64 KiB again when it loads a raw 64 KiB
battery file.

```sh
python3 tools/save_file.py expand original.sav recruit-naming.sav
```

The tool copies the original 65,536 bytes verbatim and appends 65,536
erased bytes. Normal game progress stays in the first bank. Recruit name
records live in the second bank starting at file offset `0x10000`. The tool
also accepts and copies an already-expanded 128 KiB save. Its output is
always a new file.

## Compatibility and rollback

- The patch targets the exact clean US ROM above. Use it on its own. Other
  game revisions, translations, and patch combinations are unsupported.
- Automatic expansion was tested on mGBA. Other emulators may require
  a manual setting or an expanded save. If the game detects only 64 KiB
  Flash after the probe, ordinary recruitment keeps its original behavior.
  Use battery saves when switching builds, since emulator save states
  are tied to their ROM build.
- To roll back, launch the original ROM with the original save backup and
  the stock **Flash 512 Kbit (64 KiB)** setting. To keep progress made while
  playing the patched ROM, extract the current lower bank instead.

```sh
python3 tools/save_file.py rollback recruit-naming.sav stock.sav
```

The rollback file contains the current native game progress and uses each
recruit's original name. Keep the 128 KiB backup to retain its custom names.

## Build from source

Install Python 3.10 or later, Clang with the `arm-none-eabi` target, and GNU
Arm Embedded binutils (`arm-none-eabi-ld`, `arm-none-eabi-nm`, and
`arm-none-eabi-objcopy`). From the repository root, run the following command
with your own clean North American ROM and a new IPS path outside the checkout.

```sh
./build.sh --retail /path/to/ffta-us.gba --output /path/to/ffta-us-recruit-naming.ips
```

The script checks the ROM's SHA-256, compiles the C source, and verifies the
generated IPS by applying it in memory. The IPS is the only output file. The
build report and SHA-256 checksums go to standard output. Use `./build.sh --help`
for toolchain overrides. On systems without a POSIX shell, run
`python3 tools/build_patch.py` with the same arguments.

Run the tests independently with the following command.

```sh
python3 -m unittest discover -s tests
```

See [the technical review](REVIEW.md) for the ROM and memory layout. The
repository and releases distribute source and a patch. Supply your own ROM.
