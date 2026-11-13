# 受信发布回执生成企业下载页

`scripts/build_desktop_downloads.py` 为已经验收的 Hermes native channel release 生成静态中文下载页。
LDSP/IDSP 与 Lumi AI 可以链接同一页面，安装包来自原有版本化制品库。
复用 `hermes_cli.release_channels` schema，不定义新更新协议，不改客户端更新器。

## 使用

准备经过既有 qualification gate 的 channel.json 和原始 build.json。
从可信 CI 发布回执**独立取得**仓库、appId、channel、publicBase、build.json SHA-256；不能从尚未信任的输入自行推导期望值。

```bash
just desktop-downloads \
  --record .scratch/release/channel.json \
  --manifest .scratch/release/build.json \
  --manifest-sha256 <可信回执中的64位小写SHA256> \
  --repository <组织>/<仓库> \
  --app-id <企业appId> \
  --channel <发行频道> \
  --public-base https://downloads.example.com/desktop \
  --output .scratch/release/index.html
```

已激活环境也可运行 `python scripts/build_desktop_downloads.py` 加相同参数。
无需模型、网络、员工账号、发布密钥；不改 profile/config/runtime。

校验元数据上限、重复 JSON key、独立摘要、head、仓库/产品/频道/发布源、包 namespace、
平台/架构/版本/签名身份字段及安装包扩展名。
现有协议支持 Windows/macOS x64/arm64，没有记录的包不生成链接；不伪造协议未支持的 Linux 按钮。
页面只输出必要包字段，不输出 bundleEnv/密钥/本地路径；HTML 转义，无 JS/外部资源，固定 CSS 由 CSP SHA-256 授权。
制品键的 `+` 做 URL 编码。成功原子替换页面，失败非零退出、保留旧页；流水线必须检查退出码，禁止失败后发布旧页充数。

## 信任边界

独立摘要保证与指定回执一致，**不是签名，不证明安装包实际签名有效或 URL 可下载**。
生成器不下载/执行安装包，原生签名/证书/发布授权由前置 gate 验证；页面签名身份仅代表清单中的字段。
调用者负责回执来源和新鲜度：旧合法回执可生成历史页面，本工具不能单独防回滚。
服务器负责 TLS、HTTP CSP/frame-ancestors、文件可用性、下载权限与灰度/撤回。
静态页不按员工过滤灰度，只能发布已批准该入口受众的版本；受限版本须后端鉴权/权限隔离，不能靠隐藏链接。
实际下载跳转/凭据仍由客户端更新器处理。

未改 Lumi AI/门户，未上传页面、登记 release 或配置证书。旧 Lumi Lattice 的 latest.yml 不可当输入，
先按 [整体方案](langton-enterprise-solution.md) 完成产品/协议隔离。

## 验证

```bash
scripts/run_tests.sh tests/scripts/test_desktop_downloads.py
python scripts/check
```

测试运行真实 CLI，覆盖成功链接/CSP、摘要/产品/仓库/频道、路径越界/重复包/签名身份缺失、
不支持包型/空 head/退役、重复 JSON key/大小上限。生产分发还需视觉、真实下载、原生签名/安装/升级验收。
