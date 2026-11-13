#!/usr/bin/env -S bash -c 'exec "$BASH" "$(dirname "$0")/run-in-hermes-env" python3 "$0" "$@"'
"""Build an enterprise download page from existing qualified channel metadata."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("record", "manifest", "manifest-sha256", "repository", "app-id", "channel", "public-base", "output"):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    from hermes_cli.release_channels import ChannelError
    from scripts.releases.downloads import qualified_manifest, read_metadata, render_download_page
    from utils import atomic_write_text

    try:
        manifest = qualified_manifest(
            read_metadata(Path(args.record)), read_metadata(Path(args.manifest)),
            expected_sha256=args.manifest_sha256, repository=args.repository, app_id=args.app_id,
            channel=args.channel, base_url=args.public_base,
        )
        page = render_download_page(manifest, expected_sha256=args.manifest_sha256)
        atomic_write_text(Path(args.output), page, preserve_mode=True)
    except (ChannelError, OSError) as exc:
        print(f"Download page build failed: {exc}", file=sys.stderr)
        return 1
    print("Download page built from qualified release metadata")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
