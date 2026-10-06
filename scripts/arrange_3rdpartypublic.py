#!/usr/bin/env python3
"""Arrange a vcpkg build of Aravis the way Micro-Manager's Windows build
expects to find it in 3rdpartypublic.

The result, under --out:

    aravis/aravis-<version>-bin/
        include/aravis-0.8/   Aravis headers
        include/glib-2.0/     GLib, GObject and GIO headers, with glibconfig.h
        x64/                  import libraries, and every DLL Aravis needs
        licenses/             the license of each package a DLL comes from
        BUILD-INFO.txt        how this directory was produced

The DLLs are found by following the import tables from the Aravis DLL, so
x64 holds exactly what Aravis loads and nothing else vcpkg happened to
install.

Licenses come from vcpkg, except where license-overrides/ in this repository
has a file for the package, because vcpkg installed something other than
the license text.
"""

import argparse
import shutil
import sys
from pathlib import Path

import pefile

# The libraries the adapter links against directly; it calls GLib and GObject
# functions itself as well as Aravis ones.
LINK_LIBRARIES = ["aravis-0.8", "gio-2.0", "gobject-2.0", "glib-2.0"]

LICENSE_OVERRIDES = Path(__file__).resolve().parent.parent / "license-overrides"

# Every real license in this build is over 1000 bytes. A file shorter than
# this is most likely a pointer to a license, not the license itself, which
# is what vcpkg installs for PCRE2.
MIN_LICENSE_BYTES = 500


def fail(message):
    sys.exit(f"error: {message}")


def read_installed_ports(installed, triplet):
    """Return {port: version} for the ports vcpkg installed for triplet."""
    ports = {}
    text = (installed / "vcpkg" / "status").read_text(encoding="utf-8")
    for paragraph in text.split("\n\n"):
        fields = {}
        for line in paragraph.splitlines():
            key, sep, value = line.partition(":")
            if sep and not line.startswith(" "):
                fields[key.strip()] = value.strip()
        if ("Feature" in fields
                or fields.get("Architecture") != triplet
                or not fields.get("Status", "").endswith(" installed")):
            continue
        version = fields["Version"]
        if fields.get("Port-Version", "0") != "0":
            version += "#" + fields["Port-Version"]
        ports[fields["Package"]] = version
    return ports


def read_file_owners(installed, triplet):
    """Return {lower-case path below installed: port} from vcpkg's file lists."""
    owners = {}
    for listing in (installed / "vcpkg" / "info").glob(f"*_{triplet}.list"):
        port = listing.name.split("_", 1)[0]
        for line in listing.read_text(encoding="utf-8").splitlines():
            owners[line.strip().lower()] = port
    return owners


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


def dll_closure(bin_dir, root):
    """Follow imports from root, returning (bundled DLL paths, external names).

    A DLL counts as bundled when vcpkg built it, i.e. it is in bin_dir.
    Everything else must come from Windows or the Visual C++ runtime.
    """
    available = {p.name.lower(): p for p in bin_dir.glob("*.dll")}
    bundled = {root.name.lower(): root}
    external = set()
    pending = [root]
    while pending:
        for name in imported_dlls(pending.pop()):
            key = name.lower()
            if key in bundled:
                continue
            if key in available:
                bundled[key] = available[key]
                pending.append(available[key])
            else:
                external.add(name)
    return sorted(bundled.values(), key=lambda p: p.name.lower()), sorted(external, key=str.lower)


def copy_tree(source, destination):
    if not source.is_dir():
        fail(f"{source} does not exist")
    shutil.copytree(source, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--installed", type=Path, required=True,
                        help="vcpkg's installed directory")
    parser.add_argument("--triplet", required=True)
    parser.add_argument("--aravis-version", required=True,
                        help="the Aravis version vcpkg is expected to have built")
    parser.add_argument("--vcpkg-ref", required=True)
    parser.add_argument("--vcpkg-commit", required=True)
    parser.add_argument("--build-url", default="")
    parser.add_argument("--runner-image", default="")
    parser.add_argument("--out", type=Path, required=True,
                        help="the directory standing in for 3rdpartypublic")
    args = parser.parse_args()

    tree = args.installed / args.triplet
    ports = read_installed_ports(args.installed, args.triplet)
    owners = read_file_owners(args.installed, args.triplet)

    built = ports.get("aravis", "").split("#")[0]
    if built != args.aravis_version:
        fail(f"vcpkg built Aravis {built or '(none)'}, expected {args.aravis_version}")

    out = args.out / "aravis" / f"aravis-{args.aravis_version}-bin"
    if out.exists():
        fail(f"{out} already exists")
    x64 = out / "x64"
    x64.mkdir(parents=True)

    # Headers. glib.h includes glibconfig.h, which GLib installs under lib/;
    # putting it beside glib.h means one include directory serves for GLib.
    copy_tree(tree / "include" / "aravis-0.8", out / "include" / "aravis-0.8")
    copy_tree(tree / "include" / "glib-2.0", out / "include" / "glib-2.0")
    if not (out / "include" / "glib-2.0" / "glibconfig.h").exists():
        found = list(tree.glob("lib/glib-2.0/include/glibconfig.h"))
        if len(found) != 1:
            fail(f"expected one glibconfig.h under {tree / 'lib'}, found {len(found)}")
        shutil.copy2(found[0], out / "include" / "glib-2.0")

    # Import libraries.
    for name in LINK_LIBRARIES:
        library = tree / "lib" / f"{name}.lib"
        if not library.exists():
            fail(f"{library} does not exist")
        shutil.copy2(library, x64)

    # DLLs.
    roots = list((tree / "bin").glob("aravis-0.8*.dll"))
    if len(roots) != 1:
        fail(f"expected one Aravis DLL in {tree / 'bin'}, found {[p.name for p in roots]}")
    dlls, external = dll_closure(tree / "bin", roots[0])
    dll_ports = {}
    for dll in dlls:
        shutil.copy2(dll, x64)
        port = owners.get(f"{args.triplet}/bin/{dll.name}".lower())
        if port is None:
            fail(f"no vcpkg port lists {dll.name}")
        dll_ports[dll.name] = port

    # Licenses, one per package that contributes a DLL.
    licenses = out / "licenses"
    licenses.mkdir()
    overridden = []
    for port in sorted(set(dll_ports.values())):
        source = LICENSE_OVERRIDES / f"{port}.txt"
        if source.exists():
            overridden.append(port)
        else:
            source = tree / "share" / port / "copyright"
        if not source.exists():
            fail(f"{source} does not exist")
        if source.stat().st_size < MIN_LICENSE_BYTES:
            fail(f"the license vcpkg installed for {port} is only "
                 f"{source.stat().st_size} bytes, so it is probably a pointer to "
                 f"the license rather than the license itself; put the real "
                 f"text in {LICENSE_OVERRIDES / (port + '.txt')}")
        shutil.copy2(source, licenses / f"{port}.txt")

    # Provenance.
    width = max(len(name) for name in dll_ports)
    lines = [
        f"Aravis {args.aravis_version} for 64-bit Windows, built with vcpkg and MSVC.",
        "",
        f"vcpkg:        {args.vcpkg_ref} ({args.vcpkg_commit})",
        f"Triplet:      {args.triplet} (DLLs, dynamic C runtime, release build)",
    ]
    if args.runner_image:
        lines.append(f"Runner image: {args.runner_image}")
    if args.build_url:
        lines.append(f"Built by:     {args.build_url}")
    lines += ["", "DLLs in x64, and the vcpkg package each comes from:"]
    lines += [f"  {name:<{width}}  {port} {ports[port]}" for name, port in sorted(dll_ports.items())]
    lines += ["", "Import libraries in x64:"]
    lines += [f"  {name}.lib" for name in LINK_LIBRARIES]
    lines += ["", "DLLs these load from Windows or the Visual C++ runtime:"]
    lines += [f"  {name}" for name in external]
    if overridden:
        lines += ["", "Licenses taken from license-overrides/ in "
                  "https://github.com/HazenBabcock/mm-aravis-windows-ci, because "
                  "vcpkg installs something other than the license text:"]
        lines += [f"  {port}" for port in overridden]
    (out / "BUILD-INFO.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
