#!/usr/bin/env python3
"""
Unified data manager for downloading and verifying tool data.

Provides consistent interface for managing cached data across all tools,
with checksum verification for reproducibility.

Usage:
    python -m tools.data_manager status
    python -m tools.data_manager download gdsc
    python -m tools.data_manager download lincs --version harmonizome_2024
    python -m tools.data_manager verify all
    python -m tools.data_manager verify depmap

For Zenodo archival (requires zenodo-client):
    python -m tools.data_manager archive depmap 25Q3
"""

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
SUPPORTED_TOOLS = [
    "depmap",
    "gdsc",
    "lincs",
    "encode",
    "biogrid",
    "ccle",
]


def load_manifest(tool: str) -> dict:
    """Load data manifest for a tool."""
    manifest_path = TOOLS_DIR / tool / "data_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest found for {tool} at {manifest_path}")
    with open(manifest_path) as f:
        return json.load(f)


def get_cache_dir(tool: str, version: str | None = None) -> Path:
    """Get cache directory for a tool."""
    base = TOOLS_DIR / tool / "cache"
    if tool == "depmap" and version:
        return base / f"depmap_{version.lower()}"
    elif tool == "lincs":
        return base / "harmonizome"
    return base


def compute_sha256(filepath: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_file(filepath: Path, expected_sha256: str) -> tuple[bool, str]:
    """Verify file checksum. Returns (is_valid, actual_hash)."""
    if not filepath.exists():
        return False, "FILE_NOT_FOUND"
    actual = compute_sha256(filepath)
    return actual == expected_sha256, actual


def download_file(url: str, dest: Path, verbose: bool = True) -> bool:
    """Download a file from URL to destination."""
    if verbose:
        print(f"  Downloading {dest.name}...")

    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest.with_suffix(dest.suffix + ".tmp")

    try:
        urllib.request.urlretrieve(url, temp_path)
        temp_path.rename(dest)
        if verbose:
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"    Downloaded {size_mb:.1f} MB")
        return True
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        if verbose:
            print(f"    Failed: {e}")
        return False


def cmd_status(args):
    """Show status of all tools' data."""
    print("Data Status")
    print("=" * 60)

    for tool in SUPPORTED_TOOLS:
        try:
            manifest = load_manifest(tool)
        except FileNotFoundError:
            print(f"\n{tool}: No manifest found")
            continue

        print(f"\n{tool.upper()}")
        print("-" * 40)

        versions = manifest.get("versions", {})
        for version, version_info in versions.items():
            status = version_info.get("status", "unknown")
            print(f"  Version: {version} ({status})")

            cache_dir = get_cache_dir(tool, version)
            files = version_info.get("files", {})

            present = 0
            missing = 0
            invalid = 0

            for filename, file_info in files.items():
                filepath = cache_dir / filename
                expected_sha = file_info.get("sha256", "")

                if not filepath.exists():
                    missing += 1
                    print(f"    [ ] {filename} (missing)")
                elif expected_sha:
                    is_valid, actual = verify_file(filepath, expected_sha)
                    if is_valid:
                        present += 1
                        print(f"    [x] {filename} (verified)")
                    else:
                        invalid += 1
                        print(f"    [!] {filename} (checksum mismatch)")
                else:
                    present += 1
                    print(f"    [?] {filename} (present, no checksum)")

            total = present + missing + invalid
            print(f"  Summary: {present}/{total} files verified", end="")
            if missing:
                print(f", {missing} missing", end="")
            if invalid:
                print(f", {invalid} invalid", end="")
            print()


def cmd_download(args):
    """Download data for a tool."""
    tool = args.tool
    version = args.version

    if tool == "all":
        for t in SUPPORTED_TOOLS:
            print(f"\n=== Downloading {t} ===")
            _download_tool(t, version, args.force)
    else:
        _download_tool(tool, version, args.force)


def _download_tool(tool: str, version: str | None, force: bool):
    """Download data for a single tool."""
    manifest = load_manifest(tool)
    versions = manifest.get("versions", {})

    # Determine version to download
    if version:
        if version not in versions:
            print(f"Error: Version {version} not found. Available: {list(versions.keys())}")
            return
        target_version = version
    else:
        # Find current version
        target_version = None
        for v, info in versions.items():
            if info.get("status") == "current":
                target_version = v
                break
        if not target_version:
            target_version = list(versions.keys())[0]

    version_info = versions[target_version]
    cache_dir = get_cache_dir(tool, target_version)
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {tool} version {target_version} to {cache_dir}")

    # Check for auto_download setting
    notes = manifest.get("notes", {})
    if not notes.get("auto_download", True):
        print(f"\n  Note: {tool} requires manual download.")
        instructions = version_info.get("download_instructions", "")
        if instructions:
            print(f"  {instructions}")
        print("\n  Files needed:")
        for filename, file_info in version_info.get("files", {}).items():
            filepath = cache_dir / filename
            if not filepath.exists() or force:
                url = file_info.get("upstream_url", "N/A")
                print(f"    - {filename}")
                print(f"      URL: {url}")
        return

    # Download files
    files = version_info.get("files", {})
    for filename, file_info in files.items():
        filepath = cache_dir / filename

        if filepath.exists() and not force:
            print(f"  {filename} already exists, skipping (use --force to redownload)")
            continue

        url = file_info.get("upstream_url")
        if not url:
            print(f"  {filename}: No download URL available")
            continue

        success = download_file(url, filepath)
        if success:
            expected_sha = file_info.get("sha256")
            if expected_sha:
                is_valid, actual = verify_file(filepath, expected_sha)
                if is_valid:
                    print("    Checksum verified")
                else:
                    print("    WARNING: Checksum mismatch!")
                    print(f"      Expected: {expected_sha}")
                    print(f"      Got:      {actual}")


def cmd_verify(args):
    """Verify checksums for a tool's data."""
    tool = args.tool

    if tool == "all":
        all_valid = True
        for t in SUPPORTED_TOOLS:
            if not _verify_tool(t):
                all_valid = False
        sys.exit(0 if all_valid else 1)
    else:
        valid = _verify_tool(tool)
        sys.exit(0 if valid else 1)


def _verify_tool(tool: str) -> bool:
    """Verify a single tool's data. Returns True if all valid."""
    print(f"\nVerifying {tool}...")

    manifest = load_manifest(tool)
    versions = manifest.get("versions", {})

    all_valid = True
    for version, version_info in versions.items():
        if version_info.get("status") != "current":
            continue

        cache_dir = get_cache_dir(tool, version)
        files = version_info.get("files", {})

        for filename, file_info in files.items():
            filepath = cache_dir / filename
            expected_sha = file_info.get("sha256")

            if not expected_sha:
                print(f"  {filename}: No checksum in manifest")
                continue

            is_valid, actual = verify_file(filepath, expected_sha)
            if is_valid:
                print(f"  {filename}: OK")
            elif actual == "FILE_NOT_FOUND":
                print(f"  {filename}: MISSING")
                all_valid = False
            else:
                print(f"  {filename}: MISMATCH")
                print(f"    Expected: {expected_sha}")
                print(f"    Got:      {actual}")
                all_valid = False

    return all_valid


def cmd_compute_checksums(args):
    """Compute and print checksums for files (utility for updating manifests)."""
    tool = args.tool
    version = args.version

    manifest = load_manifest(tool)
    versions = manifest.get("versions", {})

    if version and version in versions:
        target_version = version
    else:
        target_version = next(
            (v for v, info in versions.items() if info.get("status") == "current"),
            list(versions.keys())[0] if versions else None,
        )

    if not target_version:
        print(f"No versions found for {tool}")
        return

    cache_dir = get_cache_dir(tool, target_version)
    print(f"Computing checksums for {tool} version {target_version}")
    print(f"Cache directory: {cache_dir}")
    print()

    files = versions[target_version].get("files", {})
    for filename in files:
        filepath = cache_dir / filename
        if filepath.exists():
            sha = compute_sha256(filepath)
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f'"{filename}": {{')
            print(f'  "sha256": "{sha}",')
            print(f'  "size_mb": {size_mb:.1f}')
            print("}")
        else:
            print(f"{filename}: NOT FOUND")


def main():
    parser = argparse.ArgumentParser(description="Manage data for retro_testing_data tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status command
    status_parser = subparsers.add_parser("status", help="Show data status for all tools")
    status_parser.set_defaults(func=cmd_status)

    # download command
    download_parser = subparsers.add_parser("download", help="Download data for a tool")
    download_parser.add_argument("tool", choices=SUPPORTED_TOOLS + ["all"])
    download_parser.add_argument("--version", help="Specific version to download")
    download_parser.add_argument("--force", action="store_true", help="Redownload even if exists")
    download_parser.set_defaults(func=cmd_download)

    # verify command
    verify_parser = subparsers.add_parser("verify", help="Verify checksums")
    verify_parser.add_argument("tool", choices=SUPPORTED_TOOLS + ["all"])
    verify_parser.set_defaults(func=cmd_verify)

    # compute-checksums command (utility)
    checksum_parser = subparsers.add_parser(
        "compute-checksums", help="Compute checksums for manifest updates"
    )
    checksum_parser.add_argument("tool", choices=SUPPORTED_TOOLS)
    checksum_parser.add_argument("--version", help="Specific version")
    checksum_parser.set_defaults(func=cmd_compute_checksums)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
