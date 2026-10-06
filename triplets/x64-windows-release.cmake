# 64-bit DLLs against the dynamic C runtime, release build only. The workflow
# uses this as vcpkg's host triplet, for the tools it runs during the build
# (GLib's resource compiler, pkgconf and so on). vcpkg's built-in x64-windows
# triplet would also build a debug copy of each, which nothing here uses.
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE dynamic)
set(VCPKG_BUILD_TYPE release)
