# 64-bit static libraries against the dynamic C runtime (/MD), release build
# only. This is what the Aravis adapter links: Micro-Manager's device adapters
# use the dynamic C runtime, and linking the libraries statically means the
# adapter needs no DLLs of its own. vcpkg ships the same definition as a
# community triplet; it is repeated here so the build does not depend on it.
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE static)
set(VCPKG_BUILD_TYPE release)
