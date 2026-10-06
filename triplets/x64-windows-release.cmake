# 64-bit DLLs against the dynamic C runtime, release build only. vcpkg's
# built-in x64-windows triplet also builds a debug copy of every package,
# which nothing here uses and which doubles the build time.
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE dynamic)
set(VCPKG_BUILD_TYPE release)
