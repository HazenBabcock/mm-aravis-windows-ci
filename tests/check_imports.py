"""Check that Windows binaries load only DLLs that come with Windows.

    python check_imports.py FILE [FILE ...] [--system-dir DIR]

Lists every DLL each FILE imports and fails if any of them is neither in the
Windows system directory (by default %SystemRoot%\\System32) nor an API set
(api-ms-win-*, ext-ms-*). The Visual C++ runtime DLLs count as system DLLs
here because the redistributable installs them into System32, and
Micro-Manager's installer runs that redistributable.
"""

import argparse
import os
import sys
from pathlib import Path

import pefile


def imported_dlls(path):
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(directories=[
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
    ])
    names = []
    for table in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT"):
        for entry in getattr(pe, table, []):
            names.append(entry.dll.decode("ascii"))
    pe.close()
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--system-dir", type=Path,
                        default=Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32")
    args = parser.parse_args()

    system = {p.name.lower() for p in args.system_dir.iterdir()}
    failed = False
    for path in args.files:
        print(f"{path.name} ({path.stat().st_size:,} bytes) imports:")
        for name in sorted(imported_dlls(path), key=str.lower):
            key = name.lower()
            if key.startswith(("api-ms-win-", "ext-ms-")) or key in system:
                print(f"  {name}")
            else:
                print(f"  {name}  <- not part of Windows")
                failed = True
    if failed:
        sys.stdout.flush()
        print("Some imports are not part of Windows.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
