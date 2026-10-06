# mm-aravis-windows-ci

Continuous integration that builds the [Micro-Manager](https://micro-manager.org)
Aravis camera adapter for Windows and checks that it works in a Micro-Manager
installation.

[Aravis](https://github.com/AravisProject/aravis) is an open-source library for
GenICam cameras (GigE Vision and USB3 Vision). Micro-Manager's adapter for it
currently builds on Linux only. This repository works out what a Windows build
needs, so that the adapter can be added to the Windows nightly builds.

## What the workflow does

1. Builds Aravis and its dependencies (GLib, libxml2, zlib, libusb) with
   [vcpkg](https://vcpkg.io) and MSVC, from a pinned vcpkg release.
2. Arranges the headers, import libraries and DLLs in the directory layout
   that Micro-Manager's Windows build expects to find in `3rdpartypublic`, and
   saves that directory as a build artifact named
   `3rdpartypublic-aravis-<version>`. It contains `aravis\aravis-<version>-bin`,
   with the license of every package a DLL comes from and a `BUILD-INFO.txt`
   recording how it was built.
3. Compiles a small test program against the arranged files alone and runs it
   with only those DLLs on the search path. The program grabs a frame from
   Aravis's built-in fake camera, so it needs no hardware.

Still to come:

4. Build the adapter with MSBuild from the `aravis-windows` branch of
   [HazenBabcock/mmCoreAndDevices](https://github.com/HazenBabcock/mmCoreAndDevices/tree/aravis-windows).
5. Install a current Micro-Manager nightly build, add the adapter and its
   DLLs, and check that the adapter loads.

## Files

- `.github/workflows/build.yml`: the workflow.
- `scripts/arrange_3rdpartypublic.py`: builds the `3rdpartypublic` layout from
  vcpkg's output, following the DLL imports from the Aravis DLL to decide
  which DLLs to include.
- `tests/smoke.cpp`: the test program.
- `triplets/x64-windows-release.cmake`: a vcpkg triplet for release-only DLLs.

## Status

Work in progress. The upstream discussion is
[micro-manager/mmCoreAndDevices#465](https://github.com/micro-manager/mmCoreAndDevices/issues/465).

## License

BSD 3-clause; see [LICENSE](LICENSE). This covers the files in this
repository. The Aravis files the workflow produces keep their own licenses,
which it copies into the artifact.
