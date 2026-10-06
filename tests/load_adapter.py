"""Load the Micro-Manager Aravis adapter with pymmcore and report what it finds.

    python load_adapter.py STAGE_DIR [--snap TEXT]

STAGE_DIR holds mmgr_dal_AravisCamera.dll and the DLLs it depends on, as a
Micro-Manager installation directory would. With --snap, the first camera
whose Aravis id contains TEXT is opened and one image is snapped.

Exits non-zero if the adapter is not found, fails to load, or the snap fails.
"""

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stage", type=Path)
    parser.add_argument("--snap", metavar="TEXT",
                        help="snap from the first camera whose id contains TEXT")
    args = parser.parse_args()
    stage = args.stage.resolve()

    # MMCore loads adapters with plain LoadLibrary, so Windows looks for their
    # dependencies beside the running program rather than beside the adapter.
    # In Micro-Manager that is the installation directory, which holds both.
    # Here the program is python.exe, so add the staging directory to both
    # search mechanisms Windows might be using.
    if sys.platform == "win32":
        os.add_dll_directory(str(stage))
        os.environ["PATH"] = str(stage) + os.pathsep + os.environ["PATH"]

    import pymmcore

    core = pymmcore.CMMCore()
    core.setDeviceAdapterSearchPaths([str(stage)])
    print(f"pymmcore {pymmcore.__version__}, {core.getAPIVersionInfo()}")

    adapters = list(core.getDeviceAdapterNames())
    print(f"Adapters in {stage}: {adapters}")
    if "AravisCamera" not in adapters:
        print("AravisCamera is not among them", file=sys.stderr)
        return 1

    # Loads the DLL and runs the adapter's InitializeModuleData, which asks
    # Aravis for its cameras; raises if the DLL or a dependency fails to load.
    cameras = list(core.getAvailableDevices("AravisCamera"))
    print(f"Cameras the adapter lists: {cameras}")

    if args.snap is None:
        return 0

    matches = [c for c in cameras if args.snap in c]
    if not matches:
        print(f"No camera id contains {args.snap!r}", file=sys.stderr)
        return 1
    core.loadDevice("Camera", "AravisCamera", matches[0])
    core.initializeDevice("Camera")
    core.setCameraDevice("Camera")
    core.setExposure(10.0)
    core.snapImage()
    image = core.getImage()
    print(f"Snapped {core.getImageWidth()} x {core.getImageHeight()} "
          f"from {matches[0]}, {core.getBytesPerPixel()} byte(s) per pixel, "
          f"pixel values {image.min()} to {image.max()}")
    core.unloadAllDevices()
    return 0


if __name__ == "__main__":
    sys.exit(main())
