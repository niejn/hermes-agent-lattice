"""The download build consumes real channel metadata through its CLI."""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys

import pytest

from hermes_cli.release_channels import MAX_METADATA, canonical_json


class DownloadPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.csp = ""
        self.styles = []
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "a":
            self.links.append(attributes["href"])
        if tag == "meta" and attributes.get("http-equiv") == "Content-Security-Policy":
            self.csp = attributes["content"]
        self.in_style = tag == "style"

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)


@pytest.fixture
def release():
    from hermes_cli.release_channels import build_prefix, package_versions
    identity = {
        "token": "a" * 16, "displayName": "Lattice Example", "appId": "com.example.lattice",
        "appNamePascal": "Lattice", "artifactNamePascal": "Lattice", "cliName": "lattice",
        "windowsExecutableName": "Lattice", "msixAppIdWithOrg": "Example.Lattice",
    }
    version, windows_version = package_versions(1)
    request = {
        "schema": 1, "buildId": "b" * 32, "channel": "enterprise-preview", "sequence": 1,
        "repository": "example/lattice", "commit": "c" * 40, "sourceVersion": "1.2.3",
        "version": version, "windowsVersion": windows_version, "identity": identity,
        "bundleEnv": {}, "publicBase": "https://downloads.example/desktop",
    }
    prefix = build_prefix(request["buildId"])
    packages = []
    for platform, arch, extension in (("win32", "x64", "msix"), ("darwin", "arm64", "dmg")):
        mac = platform == "darwin"
        packages.append({
            "platform": platform, "arch": arch, "variant": "bundled",
            "identity": identity["appId" if mac else "msixAppIdWithOrg"],
            "version": version if mac else windows_version,
            "teamId" if mac else "publisher": "ABCDEFGHIJ" if mac else 'CN=Example & "Company"',
            "artifact": {"key": f"{prefix}{platform}/Lattice+{arch}.{extension}", "sha256": "d" * 64, "size": 1000},
            "feed": {"key": f"{prefix}{platform}/stable.yml", "channel": "stable"},
        })
        if not mac:
            packages[-1]["teamId"] = "Unrelated metadata must not replace the Windows publisher"
    manifest = {"schema": 1, "request": request, "packages": packages}
    digest = hashlib.sha256(canonical_json(manifest)).hexdigest()
    record = {
        "schema": 1, "name": request["channel"], "repository": request["repository"],
        "policy": "preview", "state": "active", "revision": 1, "nextSequence": 2, "identity": identity,
        "head": {"buildId": request["buildId"], "sequence": 1, "manifestKey": prefix + "build.json", "sha256": digest},
    }
    return record, manifest


def build_page(tmp_path, record, manifest, *, receipt=None):
    record_path = tmp_path / "channel.json"
    manifest_path = tmp_path / "build.json"
    record_path.write_bytes(canonical_json(record))
    manifest_path.write_bytes(canonical_json(manifest))
    request = manifest["request"]
    command = [
        sys.executable, str(Path(__file__).resolve().parents[2] / "scripts/build_desktop_downloads.py"),
        "--record", str(record_path), "--manifest", str(manifest_path),
        "--manifest-sha256", receipt or hashlib.sha256(canonical_json(manifest)).hexdigest(),
        "--repository", "example/lattice", "--app-id", "com.example.lattice",
        "--channel", "enterprise-preview", "--public-base", request["publicBase"],
        "--output", str(tmp_path / "index.html"),
    ]
    return subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)


def test_cli_builds_downloads_from_native_release_and_embeds_only_qualified_packages(tmp_path, release):
    record, manifest = release
    result = build_page(tmp_path, record, manifest)
    assert result.returncode == 0, result.stderr
    page = (tmp_path / "index.html").read_text()
    parsed = DownloadPage()
    parsed.feed(page)
    assert set(parsed.links) == {
        manifest["request"]["publicBase"] + "/" + row["artifact"]["key"].replace("+", "%2B")
        for row in manifest["packages"]
    }
    assert "CN=Example &amp; &quot;Company&quot;" in page
    assert "Unrelated metadata" not in page
    assert "Linux" not in page
    assert "default-src 'none'" in parsed.csp
    style_hash = base64.b64encode(hashlib.sha256("".join(parsed.styles).encode()).digest()).decode()
    assert f"style-src 'sha256-{style_hash}'" in parsed.csp
    assert record["head"]["sha256"] in page


@pytest.mark.parametrize("mutate,refresh_head", [
    pytest.param(lambda r, m, o: o.update(receipt="0" * 64), False, id="receipt"),
    pytest.param(lambda r, m, o: r["head"].update(sha256="0" * 64), False, id="head"),
    pytest.param(lambda r, m, o: r["identity"].update(appId="com.example.other"), True, id="product"),
    pytest.param(lambda r, m, o: r.update(repository="example/other"), True, id="repository"),
    pytest.param(lambda r, m, o: r.update(name="other"), True, id="channel"),
    pytest.param(lambda r, m, o: m["request"].update(publicBase="https://downloads.example/../other"), True, id="archive"),
    pytest.param(lambda r, m, o: m["packages"].append(deepcopy(m["packages"][0])), True, id="duplicate-target"),
    pytest.param(lambda r, m, o: m["packages"][0]["artifact"].update(key="releases/../evil.msix"), True, id="key"),
    pytest.param(lambda r, m, o: m["packages"][0].pop("publisher"), True, id="unsigned"),
    pytest.param(lambda r, m, o: m["packages"][0]["artifact"].update(key=m["packages"][0]["artifact"]["key"] + ".html"), True, id="installer"),
    pytest.param(lambda r, m, o: r.update(head=None), False, id="missing-head"),
    pytest.param(lambda r, m, o: r.update(state="retired"), True, id="retired"),
])
def test_cli_rejects_unqualified_metadata_without_overwriting_previous_page(tmp_path, release, mutate, refresh_head):
    record, manifest = deepcopy(release)
    options = {}
    mutate(record, manifest, options)
    if refresh_head:
        record["head"]["sha256"] = hashlib.sha256(canonical_json(manifest)).hexdigest()
    output = tmp_path / "index.html"
    output.write_text("previous qualified page")
    result = build_page(tmp_path, record, manifest, **options)
    assert result.returncode == 1
    assert "Download page build failed:" in result.stderr
    assert output.read_text() == "previous qualified page"


def test_metadata_read_is_bounded_and_duplicate_json_keys_are_rejected(tmp_path, release):
    from hermes_cli.release_channels import ChannelError
    from scripts.releases.downloads import qualified_manifest, read_metadata
    oversized = tmp_path / "huge.json"
    oversized.write_bytes(b" " * (MAX_METADATA + 1))
    with pytest.raises(ChannelError, match="size limit"):
        read_metadata(oversized)
    record, manifest = release
    body = canonical_json(manifest).replace(b'"schema":1', b'"schema":1,"schema":1', 1)
    digest = hashlib.sha256(body).hexdigest()
    record["head"]["sha256"] = digest
    with pytest.raises(ChannelError, match="Invalid channel JSON"):
        qualified_manifest(canonical_json(record), body, expected_sha256=digest,
                           repository="example/lattice", app_id="com.example.lattice",
                           channel="enterprise-preview", base_url=manifest["request"]["publicBase"])


@pytest.mark.platforms("linux", "macos")
def test_regeneration_preserves_page_permissions_for_the_web_server(tmp_path, release):
    record, manifest = release
    page = tmp_path / "index.html"
    page.write_text("previous page")
    page.chmod(0o640)
    result = build_page(tmp_path, record, manifest)
    assert result.returncode == 0, result.stderr
    assert page.stat().st_mode & 0o777 == 0o640
