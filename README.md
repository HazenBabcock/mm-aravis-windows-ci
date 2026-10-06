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
   [vcpkg](https://vcpkg.io) and MSVC.
2. Arranges the headers, import libraries and DLLs in the directory layout
   that Micro-Manager's Windows build expects to find in `3rdpartypublic`, and
   saves that directory as a build artifact.
3. Builds the adapter with MSBuild from the `aravis-windows` branch of
   [HazenBabcock/mmCoreAndDevices](https://github.com/HazenBabcock/mmCoreAndDevices/tree/aravis-windows).
4. Installs a current Micro-Manager nightly build, adds the adapter and its
   DLLs, and checks that the adapter loads.

## Status

Work in progress; the workflow is being written. The upstream discussion is
[micro-manager/mmCoreAndDevices#465](https://github.com/micro-manager/mmCoreAndDevices/issues/465).
