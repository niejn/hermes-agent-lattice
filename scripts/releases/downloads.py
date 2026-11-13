"""Render a download page from an independently pinned native channel release.

This is a build-time consumer of the existing channel protocol, not an updater.
The expected digest and product identity come from a trusted release receipt.
"""
from __future__ import annotations

import base64
import hashlib
from html import escape
from pathlib import Path
from urllib.parse import quote

from hermes_cli.release_channels import (
    MAX_METADATA, ChannelError, decode_json, public_base, require_sha256,
    validate_manifest, validate_name, validate_record,
)

_PLATFORMS = {"darwin": "macOS", "win32": "Windows"}
_ARCHITECTURES = {"arm64": "ARM64", "x64": "x64"}
_INSTALLERS = {"darwin": {".dmg", ".zip"}, "win32": {".msix", ".exe"}}


def read_metadata(path: Path) -> bytes:
    """Bound local metadata before decoding, including growing files."""
    with path.open("rb") as stream:
        body = stream.read(MAX_METADATA + 1)
    if len(body) > MAX_METADATA:
        raise ChannelError("Download metadata exceeds size limit")
    return body


def qualified_manifest(record_body: bytes, manifest_body: bytes, *, expected_sha256: str,
                       repository: str, app_id: str, channel: str, base_url: str) -> dict:
    """Check the receipt, archive authority and product before making links."""
    require_sha256(expected_sha256)
    if max(len(record_body), len(manifest_body)) > MAX_METADATA:
        raise ChannelError("Download metadata exceeds size limit")
    if hashlib.sha256(manifest_body).hexdigest() != expected_sha256:
        raise ChannelError("Download manifest does not match release receipt")
    record = validate_record(decode_json(record_body), name=validate_name(channel), repository=repository)
    if record["state"] != "active" or record["policy"] == "source-branch" or record["head"] is None:
        raise ChannelError("Download channel has no active native release")
    if record["head"]["sha256"] != expected_sha256:
        raise ChannelError("Download channel head does not match release receipt")
    if record["identity"]["appId"] != app_id:
        raise ChannelError("Download product does not match release receipt")
    manifest = validate_manifest(decode_json(manifest_body), record, public_base(base_url))
    for package in manifest["packages"]:
        suffix = Path(package["artifact"]["key"]).suffix
        if suffix not in _INSTALLERS[package["platform"]]:
            raise ChannelError("Download artifact is not a supported installer")
    return manifest


def _package_card(package: dict, base_url: str) -> str:
    platform = _PLATFORMS[package["platform"]]
    arch = _ARCHITECTURES[package["arch"]]
    artifact = package["artifact"]
    filename = artifact["key"].rsplit("/", 1)[-1]
    # Encode '+' in object names and escape the resulting HTML attribute.
    href = escape(f'{base_url}/{quote(artifact["key"], safe="/")}', quote=True)
    size = artifact["size"] / (1024 * 1024)
    signing = package["teamId" if package["platform"] == "darwin" else "publisher"]
    return f'''<article class="package">
  <h2>{platform} <span>{arch}</span></h2>
  <p class="filename">{escape(filename)}</p>
  <p>{size:.1f} MiB · 版本 {escape(package["version"])}</p>
  <a class="download" href="{href}" aria-label="下载 {platform} {arch} 安装包">下载安装包</a>
  <details><summary>校验信息</summary>
    <p>发布清单中的签名身份：<code>{escape(signing)}</code></p>
    <p>SHA-256</p><code class="hash">{artifact["sha256"]}</code>
  </details>
</article>'''


def render_download_page(manifest: dict, *, expected_sha256: str) -> str:
    """Render only a manifest returned by qualified_manifest; never infer packages."""
    request = manifest["request"]
    name = escape(request["identity"]["displayName"])
    cards = "\n".join(_package_card(package, request["publicBase"]) for package in sorted(
        manifest["packages"], key=lambda row: (row["platform"], row["arch"])))
    # Inline CSS is fixed build-owned content; no script or network font is required.
    style = (Path(__file__).with_name("downloads.css")).read_text(encoding="utf-8-sig")
    style_hash = base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
    csp = escape(f"default-src 'none'; style-src 'sha256-{style_hash}'; base-uri 'none'; form-action 'none'", quote=True)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<meta name="referrer" content="no-referrer">
<title>{name} · 桌面版下载</title><style>{style}</style></head>
<body><main>
<nav aria-label="当前位置">狼腾知光 / 桌面应用</nav>
<header><p class="brand">Langton Photonics</p><h1>{name} 桌面版</h1>
<p>选择与你的操作系统和处理器匹配的安装包。</p>
<p class="release">频道 {escape(request["channel"])} · 版本 {escape(request["version"])}</p></header>
<section class="packages" aria-label="可下载的安装包">{cards}</section>
<section class="help"><h2>安装与更新</h2>
<p>安装后打开桌面应用，按企业指引完成配置。系统登录通过公司统一登录页面完成。</p>
<p>页面仅列出本次发布提供的安装包。其他系统与架构请联系 IT 服务台。</p>
<p>已有用户请使用应用内的更新入口；更新是否可用以你的客户端和企业发布策略为准。</p></section>
<footer>内部使用 · 构建 {escape(request["commit"][:12])}
<details><summary>发布记录</summary><p>发布清单 SHA-256</p><code class="hash">{expected_sha256}</code>
<p>下载后仍须校验安装包和操作系统签名。</p></details></footer>
</main></body></html>\n'''
