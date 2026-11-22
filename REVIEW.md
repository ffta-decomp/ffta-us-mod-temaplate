# Release review

## ROM changes

The input and output ROMs are both 16 MiB. The v1.0.1 IPS is 4,118 bytes and
changes 3,935 ROM bytes. The input SHA-256 is checked before building.
Clang compiles the C implementation. GNU Arm Embedded binutils link
and extract the payload.

| ROM file offset | Purpose | Bytes |
| --- | --- | ---: |
| `0xE02000` | Recruit code and read-only tables | 3,548 |
| `0x36D370` | Nearby call bridges and startup Flash probe | 248 |
| `0xF30000` | Flash descriptor table with the Sanyo 1 Mbit entry | 64 |

The three payloads occupy erased space checked by the builder. The remaining
edits redirect the recruit scene, display, roster copy, bounded heap
initialization, and live save or selected-load calls. The original save and
load routines, title previews, and temporary-copy calls retain their original
code. The build checks every redirected BL and rejects overlapping fragments.
The patch is intended for a clean ROM.

## Memory and storage

| Region | Use |
| --- | --- |
| EWRAM `0x0203ED20–0x0203FFFF` | 4,832 bytes reserved at the top of the native menu, mission, and save heaps. The runtime structure uses 4,808 bytes. Its editor state shares storage with a 4,096-byte Flash staging buffer. |
| Native menu heap | One temporary allocation of 106,496 bytes (104 KiB), plus the native allocator header. It holds a 48 KiB VRAM backup and a 56 KiB heap for the stock keyboard. |
| Flash bank 0 | The original 64 KiB native save format and sector handling. |
| Flash bank 1 | Recruit names starting at file offset `0x10000`. A 592-byte name block is stored in one 4 KiB sector corresponding to the native save's first physical sector. |
| Cartridge SRAM | Zero bytes. The patch uses banked Flash. |

The editor checks that the recruit scene is inside its live, native
`0xC600`-byte arena before allocating scratch space. The graphics backup
and keyboard heap are subregions of a separate allocation owned by the same
native allocator. The plugin releases that allocation after the editor
closes. If allocation fails, recruitment proceeds with the original name.

A name block carries the native save sequence and checksum plus a separate
name-record CRC. A missing or stale block leaves the corresponding recruit's
original name visible. The program returns to Flash bank 0 after accessing the
name bank.

At the startup Flash ID call (`0x141DAC`), the patch probes Bank 1 only
when the detected Flash presents ID `0x1B32`. It returns to Bank 0 and
reads the ID again before the native driver selects its descriptor.
mGBA upgrades its emulated Flash on that Bank 1 command. The probe sends only bank-select
and ID commands and uses the existing memory layout. Both the
`AFXE` game code and aligned `FLASH1M_V103` marker are retained.

## Validation

- Rebuilt the IPS twice and compared the results byte for byte.
- Verified mGBA 0.10.5 default detection with an empty battery file, a 64 KiB save,
  and a 128 KiB save from v1.0.0. Expansion preserves all existing bytes
  and fills the newly added bank with `0xFF`.
- Entered the recruit scene from a US battery save in mGBA with a candidate
  produced by the game's generator and a scene arena allocated by the native
  allocator. Used game controls to name the recruit, confirm, save, and read
  back the party card and unit details after a fresh boot.
- Verified that rejecting recruitment leaves the roster slot empty and that
  skipping the editor joins the candidate under the original name.
- Traced the native allocator creating the editor block at
  `0x020223FC–0x0203C3FB` and freeing it on close. Forced low available memory
  and verified that the original recruit screen still opened.
- Extracted the lower bank and booted it on the unpatched US ROM with 64 KiB
  Flash. The recruited unit and native progress loaded with the original name.
- Ran seven host tests covering the IPS and battery-file tools.

Validation covers controlled recruitment and battery saves in mGBA. Other
emulators, physical cartridges, and combinations with other patches are
outside the tested configurations.
