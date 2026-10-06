# mm-aravis-windows-ci

Continuous integration that builds the [Micro-Manager](https://micro-manager.org)
Aravis camera adapter for Windows and checks that it works in a Micro-Manager
installation.

[Aravis](https://github.com/AravisProject/aravis) is an open-source library for
GenICam cameras (GigE Vision and USB3 Vision). Micro-Manager's adapter for it
currently builds on Linux only. This repository works out what a Windows build
needs, so that the adapter can be added to the Windows nightly builds.

Micro-Manager's Windows build does not compile its third-party libraries. It
takes prebuilt headers and libraries from a directory called `3rdpartypublic`,
which changes rarely. This repository works the same way: one workflow builds
the Aravis files, a release made from its output fixes them, and a second
workflow builds and tests the adapter against that release.

Aravis and its dependencies are built as static libraries, so the adapter
links them into its own DLL and needs no other DLLs at run time, only Windows
and the Visual C++ runtime.

## Workflows

**Aravis for 3rdpartypublic** (`.github/workflows/aravis.yml`) runs when one of
its own inputs changes, or when started by hand. It:

1. Builds Aravis and its dependencies (GLib, libffi, libintl, libiconv, PCRE2,
   libxml2, libusb and zlib) as static libraries against the dynamic C runtime,
   with [vcpkg](https://vcpkg.io) and MSVC, from a pinned vcpkg release.
   Compiled packages and downloaded sources are cached between runs.
2. Arranges the headers and static libraries in the directory layout that
   Micro-Manager's Windows build expects to find in `3rdpartypublic`, and saves
   that directory as the artifact `3rdpartypublic-Aravis-<version>`. It
   contains `Aravis\aravis-<version>-bin`, with the license of every package a
   library comes from and a `BUILD-INFO.txt` recording how it was built and
   which libraries a project must link to use it.
3. Saves the Aravis command-line tools (`arv-tool`, `arv-fake-gv-camera` and
   others) with the same licenses and `BUILD-INFO.txt` as the artifact
   `aravis-tools-<version>`, after checking that they load nothing but Windows
   DLLs. Static linking leaves the tools without Aravis's built-in fake-camera
   description, so the artifact also holds `arv-fake-camera.xml` from the same
   Aravis release; start the fake GigE camera with
   `arv-fake-gv-camera-0.8 -g arv-fake-camera.xml`. The workflow serves it on
   the loopback interface and reads it back with `arv-tool`.
4. Links a small test program against the arranged files alone, checks that
   it loads nothing but Windows DLLs, and runs it. The program grabs a frame
   from Aravis's built-in fake camera, so it needs no hardware.

**Aravis adapter** (`.github/workflows/adapter.yml`) runs when its own files
change, or when started by hand with a choice of mmCoreAndDevices repository and
branch. It:

1. Downloads the release named in the workflow and unpacks it as
   `3rdpartypublic`.
2. Builds the adapter with MSBuild from the `aravis-windows` branch of
   [HazenBabcock/mmCoreAndDevices](https://github.com/HazenBabcock/mmCoreAndDevices/tree/aravis-windows)
   (by default), and saves the adapter and its DLLs as the artifact
   `mmgr_dal_AravisCamera-staged`.
3. Loads the adapter with [pymmcore](https://github.com/micro-manager/pymmcore)
   and lists the cameras it finds, then snaps an image from Aravis's fake GigE
   camera served on the loopback interface.

To test another branch:

```sh
gh workflow run adapter.yml -R HazenBabcock/mm-aravis-windows-ci -f ref=<branch>
```

Still to come: installing a current Micro-Manager nightly build, adding the
adapter and its DLLs, and checking that the adapter loads there.

## Publishing the Aravis files

Releases are made by hand, after checking a successful run of the Aravis
workflow, so that the files the adapter is tested against change only when
someone decides they should. Each release holds two zip files: one unpacks
into `3rdpartypublic`, the other holds the tools.

```sh
run=<id of the successful run>
version=0.8.36
gh run download $run -R HazenBabcock/mm-aravis-windows-ci \
    -n 3rdpartypublic-Aravis-$version -D release/3rdpartypublic
gh run download $run -R HazenBabcock/mm-aravis-windows-ci \
    -n aravis-tools-$version -D release/tools
(cd release/3rdpartypublic && zip -r ../3rdpartypublic-Aravis-$version.zip .)
(cd release/tools && zip -r ../aravis-tools-$version.zip .)
gh release create aravis-$version -R HazenBabcock/mm-aravis-windows-ci \
    release/3rdpartypublic-Aravis-$version.zip release/aravis-tools-$version.zip \
    --title "Aravis $version for 3rdpartypublic" \
    --notes-file release/3rdpartypublic/Aravis/aravis-$version-bin/BUILD-INFO.txt
```

A rebuild of the same Aravis version gets a numbered tag such as
`aravis-0.8.36-3`. Either way, update `ARAVIS_RELEASE` in `adapter.yml` to
switch the adapter tests to the new release. Releases `aravis-0.8.36` and
`aravis-0.8.36-2` hold DLL builds from before the switch to static linking.

## Files

- `.github/workflows/aravis.yml`, `.github/workflows/adapter.yml`: the
  workflows.
- `scripts/arrange_3rdpartypublic.py`: builds the `3rdpartypublic` layout from
  vcpkg's output, taking the libraries from pkgconf's static link line for
  Aravis.
- `license-overrides/`: license texts used in place of what vcpkg installs,
  where vcpkg installs a pointer to the license rather than the license
  itself. Its README says where each one came from.
- `tests/smoke.cpp`: the test program.
- `tests/check_imports.py`: checks that Windows binaries load only DLLs that
  come with Windows.
- `tests/load_adapter.py`: loads the adapter with pymmcore, and optionally
  snaps from a camera.
- `triplets/x64-windows-static-md-release.cmake`: the vcpkg triplet for the
  static libraries.
- `triplets/x64-windows-release.cmake`: the vcpkg triplet for the tools vcpkg
  runs during the build.

## Status

Work in progress. The upstream discussion is
[micro-manager/mmCoreAndDevices#465](https://github.com/micro-manager/mmCoreAndDevices/issues/465).

## License

BSD 3-clause; see [LICENSE](LICENSE). This covers the files in this
repository. The Aravis files the workflow produces keep their own licenses,
which it copies into the artifact.
