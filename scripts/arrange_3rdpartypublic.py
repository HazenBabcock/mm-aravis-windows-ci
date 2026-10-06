#!/usr/bin/env python3
"""Arrange a vcpkg build of Aravis the way Micro-Manager's Windows build
expects to find it in 3rdpartypublic.

The libraries are static, built against the dynamic C runtime, so the Aravis
adapter links them into its own DLL and installs no other DLLs. The result,
under --out:

    Aravis/aravis-<version>-bin/
        include/aravis-0.8/   Aravis headers
        include/glib-2.0/     GLib, GObject and GIO headers, with glibconfig.h
        x64/                  the static libraries the adapter links
        licenses/             the license of each package those come from
        BUILD-INFO.txt        how this directory was produced, and the
                              libraries to list in the adapter's project

The libraries come from pkgconf's static link line for aravis-0.8, so x64
holds exactly what linking Aravis needs. The same line names the Windows
system libraries the adapter must also link.

Licenses come from vcpkg, except where license-overrides/ in this repository
has a file for the package, because vcpkg installed something other than
the license text.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

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


def static_link_libraries(pkgconf, tree):
    """Return the .lib names in pkgconf's static link line for aravis-0.8."""
    pkgconfig = os.pathsep.join(str(tree / d / "pkgconfig") for d in ("lib", "share"))
    env = dict(os.environ, PKG_CONFIG_PATH=pkgconfig, PKG_CONFIG_LIBDIR=pkgconfig)
    result = subprocess.run(
        [str(pkgconf), "--static", "--libs", "--msvc-syntax", "aravis-0.8"],
        env=env, capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"pkgconf failed: {result.stderr.strip()}")
    print(f"pkgconf --static --libs --msvc-syntax aravis-0.8:\n  {result.stdout.strip()}")
    libraries = []
    for token in result.stdout.split():
        if token.lower().startswith("/libpath:"):
            continue
        if not token.lower().endswith(".lib"):
            fail(f"unexpected item in the link line: {token}")
        if token not in libraries:
            libraries.append(token)
    return libraries


def copy_tree(source, destination):
    if not source.is_dir():
        fail(f"{source} does not exist")
    shutil.copytree(source, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--installed", type=Path, required=True,
                        help="vcpkg's installed directory")
    parser.add_argument("--triplet", required=True)
    parser.add_argument("--pkgconf", type=Path, required=True,
                        help="the pkgconf executable vcpkg built")
    parser.add_argument("--aravis-version", required=True,
                        help="the Aravis version vcpkg is expected to have built")
    parser.add_argument("--vcpkg-ref", required=True)
    parser.add_argument("--vcpkg-commit", required=True)
    parser.add_argument("--repo-url", default="https://github.com/HazenBabcock/mm-aravis-windows-ci")
    parser.add_argument("--repo-commit", required=True,
                        help="the commit of this repository the build ran from")
    parser.add_argument("--build-url", default="")
    parser.add_argument("--runner-image", default="")
    parser.add_argument("--out", type=Path, required=True,
                        help="the directory standing in for 3rdpartypublic")
    parser.add_argument("--link-list", type=Path,
                        help="also write the libraries to link here, one per line")
    args = parser.parse_args()

    tree = args.installed / args.triplet
    ports = read_installed_ports(args.installed, args.triplet)
    owners = read_file_owners(args.installed, args.triplet)

    built = ports.get("aravis", "").split("#")[0]
    if built != args.aravis_version:
        fail(f"vcpkg built Aravis {built or '(none)'}, expected {args.aravis_version}")

    out = args.out / "Aravis" / f"aravis-{args.aravis_version}-bin"
    if out.exists():
        fail(f"{out} already exists")
    x64 = out / "x64"
    x64.mkdir(parents=True)

    # Headers. glib.h includes glibconfig.h, which GLib installs under lib/;
    # putting it beside glib.h means one include directory serves for GLib.
    copy_tree(tree / "include" / "aravis-0.8", out / "include" / "aravis-0.8")
    copy_tree(tree / "include" / "glib-2.0", out / "include" / "glib-2.0")
    glibconfig = out / "include" / "glib-2.0" / "glibconfig.h"
    if not glibconfig.exists():
        found = list(tree.glob("lib/glib-2.0/include/glibconfig.h"))
        if len(found) != 1:
            fail(f"expected one glibconfig.h under {tree / 'lib'}, found {len(found)}")
        shutil.copy2(found[0], glibconfig)

    # Headers from a DLL build would declare every function dllimport or
    # dllexport, which a static link cannot satisfy cleanly.
    if "#define GLIB_STATIC_COMPILATION" not in glibconfig.read_text(encoding="utf-8"):
        fail("glibconfig.h does not define GLIB_STATIC_COMPILATION; GLib was not built static")
    if "__declspec" in (out / "include" / "aravis-0.8" / "arvapi.h").read_text(encoding="utf-8"):
        fail("arvapi.h uses __declspec; Aravis was not built static")

    # Static libraries. Anything on the link line that vcpkg did not build is
    # a Windows system library, which the adapter links from the Windows SDK.
    libraries = static_link_libraries(args.pkgconf, tree)
    library_ports = {}
    system_libraries = []
    for name in libraries:
        library = tree / "lib" / name
        if not library.exists():
            system_libraries.append(name)
            continue
        shutil.copy2(library, x64)
        port = owners.get(f"{args.triplet}/lib/{name}".lower())
        if port is None:
            fail(f"no vcpkg port lists {name}")
        library_ports[name] = port

    # Licenses, one per package that contributes a library.
    licenses = out / "licenses"
    licenses.mkdir()
    overridden = []
    for port in sorted(set(library_ports.values())):
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

    # Provenance, and what the adapter's project must link. The MSVC linker
    # does not depend on library order, so list vcpkg's libraries first.
    link_order = list(library_ports) + system_libraries
    size = sum(p.stat().st_size for p in x64.iterdir())
    width = max(len(name) for name in library_ports)
    lines = [
        f"Aravis {args.aravis_version} for 64-bit Windows: static libraries built with vcpkg and MSVC.",
        "",
        f"Built from:   {args.repo_url} at commit {args.repo_commit}",
        f"vcpkg:        {args.vcpkg_ref} ({args.vcpkg_commit})",
        f"Triplet:      {args.triplet} (static libraries, dynamic C runtime /MD, release build)",
    ]
    if args.runner_image:
        lines.append(f"Runner image: {args.runner_image}")
    if args.build_url:
        lines.append(f"Build log:    {args.build_url}")
    lines += ["", f"Static libraries in x64 ({size / 1e6:.1f} MB), and the vcpkg package each comes from:"]
    lines += [f"  {name:<{width}}  {port} {ports[port]}" for name, port in library_ports.items()]
    lines += ["", "Windows system libraries they need, from the Windows SDK:"]
    lines += [f"  {name}" for name in system_libraries]
    lines += ["", "To link Aravis, add x64 to the library directories and list these "
              "as additional dependencies:", "  " + ";".join(link_order)]
    if overridden:
        lines += ["", "Licenses taken from license-overrides/ in "
                  f"{args.repo_url}, because vcpkg installs something other than "
                  "the license text:"]
        lines += [f"  {port}" for port in overridden]
    (out / "BUILD-INFO.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.link_list:
        args.link_list.write_text("\n".join(link_order) + "\n", encoding="utf-8")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
