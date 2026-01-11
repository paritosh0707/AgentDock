#!/usr/bin/env python3
"""
Build script for dockrion package.

This script copies all sub-packages into the dockrion package directory,
builds the wheel, and then cleans up. This is necessary because setuptools
doesn't support relative paths outside the package directory when building
from an sdist.

Usage:
    python build_package.py        # Build wheel and sdist
    python build_package.py clean  # Remove copied packages
"""

import shutil
import subprocess
import sys
from pathlib import Path

# Package directory (where this script is located)
PACKAGE_DIR = Path(__file__).parent
PACKAGES_DIR = PACKAGE_DIR.parent  # The packages/ directory

# Sub-packages to include
SUB_PACKAGES = [
    ("common-py", "dockrion_common"),
    ("schema", "dockrion_schema"),
    ("adapters", "dockrion_adapters"),
    ("policy-engine", "dockrion_policy"),
    ("telemetry", "dockrion_telemetry"),
    ("runtime", "dockrion_runtime"),
    ("sdk-python", "dockrion_sdk"),
    ("cli", "dockrion_cli"),
]


def copy_packages():
    """Copy sub-packages into the package directory."""
    print("📦 Copying sub-packages...")
    for pkg_dir, pkg_name in SUB_PACKAGES:
        src = PACKAGES_DIR / pkg_dir / pkg_name
        dst = PACKAGE_DIR / pkg_name
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"  ✓ {pkg_name}")
        else:
            print(f"  ✗ {pkg_name} not found at {src}")
            sys.exit(1)


def clean_packages():
    """Remove copied sub-packages."""
    print("🧹 Cleaning up copied packages...")
    for _, pkg_name in SUB_PACKAGES:
        dst = PACKAGE_DIR / pkg_name
        if dst.exists():
            shutil.rmtree(dst)
            print(f"  ✓ Removed {pkg_name}")


def build():
    """Build the package."""
    print("🔨 Building package...")
    result = subprocess.run(
        ["uv", "build"],
        cwd=PACKAGE_DIR,
        capture_output=False,
    )
    return result.returncode


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        clean_packages()
        return 0

    try:
        # Copy packages
        copy_packages()

        # Build
        result = build()

        if result == 0:
            print("\n✅ Build successful!")
            print(f"   Packages are in: {PACKAGE_DIR.parent.parent / 'dist'}")
        else:
            print("\n❌ Build failed!")

        return result

    finally:
        # Always clean up
        clean_packages()


if __name__ == "__main__":
    sys.exit(main())
