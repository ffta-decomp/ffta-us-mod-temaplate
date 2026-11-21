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
4. Configure your emulator to use **Flash 1 Mbit (128 KiB)** for the patched
   ROM. In mGBA, set the cartridge override before booting the game because
   the `AFXE` preset can select the stock 64 KiB device.

```text
43fc8204c6dceee58828aebc7af0c72eb807e99f35ad641c8bb0a4fa8b6edc19
```

## Expand an existing save

Close the emulator or fully unload the game before copying battery saves.
Use the original raw 64 KiB `.sav` as input, then import the new file for the
patched ROM.

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
- The tested setup is mGBA using Flash 1 Mbit with the Sanyo-compatible
  Flash ID. With a stock 64 KiB Flash device, ordinary recruitment keeps
  its original behavior. Emulator save states are tied to their ROM build
  and should be discarded when switching builds.
- To roll back, launch the original ROM with the original save backup and
  the stock **Flash 512 Kbit (64 KiB)** setting. To keep progress made while
  playing the patched ROM, extract the current lower bank instead.

```sh
python3 tools/save_file.py rollback recruit-naming.sav stock.sav
```

The rollback file contains the current native game progress and uses each
recruit's original name. Keep the 128 KiB backup to retain its custom names.

## Build from source

Use Python 3.10 or later, Clang with the ARM bare-metal target, and GNU
Arm Embedded binutils (`arm-none-eabi-ld`, `nm`, and `objcopy`).

```sh
python3 tools/build_patch.py --retail /path/to/ffta-us.gba --output /path/to/ffta-us-recruit-naming.ips
python3 -m unittest discover -s tests
```

See [the technical review](REVIEW.md) for the ROM and memory layout. The
repository and releases distribute source and a patch. Supply your own ROM.
