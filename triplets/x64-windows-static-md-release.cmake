# 64-bit static libraries against the dynamic C runtime (/MD), release build
# only. This is what the Aravis adapter links: Micro-Manager's device adapters
# use the dynamic C runtime, and linking the libraries statically means the
# adapter needs no DLLs of its own.
set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE static)
set(VCPKG_BUILD_TYPE release)

# A static library can only be linked by a toolset at least as new as the
# compiler that built it, so build with the toolset micromanager.sln uses
# (v143, Visual Studio 2022), not the newest one installed. Version 14.44 is
# the v143 compiler on GitHub's windows-2025 runners.
set(VCPKG_PLATFORM_TOOLSET v143)
set(VCPKG_PLATFORM_TOOLSET_VERSION 14.44)

# No whole-program optimization: /GL objects can only be linked by exactly
# the compiler version that built them. vcpkg appends these flags after each
# project's own options, so they override a project that asks for /GL
# (libusb's MSBuild projects do).
set(VCPKG_C_FLAGS "/GL-")
set(VCPKG_CXX_FLAGS "/GL-")
