# 可配置在线词典

把自己的方言资料整理成可检索、可听录音的网站。一个部署同时提供电脑网页和手机网页，可配置站名、方言、Logo 与内容来源。源码来自兴化语记的后端、Web 和 Uni-App，保留原作者与组件许可。

完整的[中文使用指南](docs/README.md)按安装、资料包、代理和备份组织；不了解目录时先看[目录说明](docs/directory.md)。

## 先在自己电脑上试用

按[安装指南](docs/install.md)获取源码，安装 Docker（含 Compose v2）和 Python 3.10+，启动 Docker，然后在本目录打开终端：

```sh
./dictionary init
./dictionary start
```

首次启动会下载依赖并构建镜像，需要网络和一些时间。完成后打开：

- 电脑网页：<http://localhost:18080>
- 手机网页：<http://localhost:18080/mobile/>

`init` 生成 `.env` 和 `config/site.json`，已有文件不会被覆盖。修改 `config/site.json` 中的站名、方言和来源说明，再运行 `./dictionary start` 应用配置。配置会发给浏览器，不能填写密钥。

空库默认只有明确标记的“技术演示”词条。示例品牌、合成资料包和示例音频均用于演示，**不是真实语保资料包或真实方言词典**。

日常停止：`./dictionary stop`，保留数据。已有本地镜像时可用 `./dictionary start --no-build --pull never` 重新启动。更多安装、端口和排错说明见[安装指南](docs/install.md)。

## 我有一整包资料

先把资料整理为本仓库支持的目录或 ZIP，再预览检查：

```sh
./dictionary preview "/你的路径/资料包.zip"
```

预览只检查包，不写数据库。格式为本项目的 `legacy-tsv-v1` 适配格式：`metadata.json`、五列 `words.tsv`、按四位编号命名的 WAV/MP3 录音；FLV 暂不支持。**这不是官方统一资料包标准**。字段、来源许可声明、地区映射和示例见[整包导入指南](docs/packages/README.md)。

启动网站后，用自己建立的账号导入；用户名是登录用户名，不是数据库 ID：

```sh
./dictionary manage createsuperuser
./dictionary import "/你的路径/资料包.zip" --importer 你的用户名
```

创建账号时按提示设置自己的凭据。上面的方式保持私有，录音保存在私有目录；命令成功不代表已经公开。首次导入时，若已核验发布授权并在包中明确声明，可改用下面的公开方式（二选一，不是先私有导入再重复执行）：

```sh
./dictionary import "/你的路径/资料包.zip" --importer 你的用户名 --publish
```

同包、同内容和同公开状态重导不会新增条目；相同包 ID 内容变化或请求切换公开状态会被拒绝。本轮不提供已导入包的就地发布/撤回，请在首次导入前选择状态。先按导入指南核验来源、许可和发布范围。

已导入包可按[输入法词库指南](docs/ime-export.md)导出Pouleng附加词库。需要人工核验的编号/输入码对照表；默认不导私有资料，输入法本体仍在独立仓库，不是自动把IPA变成输入法。

## 给别人访问

默认地址只供这台电脑访问。准备使用域名提供服务时，已有 Traefik 的主机按 [Traefik 接入指南](docs/traefik.md)配置 `.env.traefik` 和 HTTPS 站点地址，再运行：

```sh
./dictionary --traefik start
```

此方案接入已有 Traefik，不启动第二套代理、不占用新的 80/443、不修改现有证书管理。全新服务器还没有代理时，可按同一指南选择显式的独立 Traefik 方案 `./dictionary --traefik-standalone start`；有代理的机器不要运行这个分支。域名、DNS、已有网络和证书设置需由部署者提供；真实域名的 TLS 与公网可达性仍需在目标主机验证。

## 备份与搬家

数据在 Docker 数据卷中，复制源码目录不能备份词库。升级、搬家前先停写，备份数据库、录音和有效配置，并在新目录恢复验证。按[备份、恢复与回滚指南](docs/backup.md)操作；快照含私有内容，单独妥善保存。不要用 `docker compose down -v` 日常停止服务，它会删除数据卷。

## 源码在哪里

| 目录 | 用途 |
| --- | --- |
| `apps/backend/` | Django 后端；业务工程在 `hinghwa-dict-backend/` |
| `apps/web/` | 电脑网页 |
| `apps/mobile/` | Uni-App 手机网页与小程序源码 |
| `config/` | 站点配置与服务端功能策略示例 |
| `packages/examples/` | 合成资料包示例 |
| `ops/docker/`、`ops/compose/` | 镜像构建与可选部署组合 |
| `tools/` | 导入、校验、打包、备份和前端配置工具 |
| `docs/development/` | 开发说明与历史验收证据 |
| `docs/attribution/` | 来源、固定上游提交与署名 |

Compose 提供 Web 和手机 H5；微信小程序需自有 AppID、HTTPS API、服务器域名及平台审核，见[平台边界说明](docs/development/platform-capabilities.md)。站点配置见[前端配置说明](tools/frontend-config/README.md)，贡献功能的开关和账号权限见[服务端策略](docs/server-feature-policy.md)。

## 许可与来源

根 [LICENSE](LICENSE) 及三个组件的 [后端](apps/backend/LICENSE)、[Web](apps/web/LICENSE)、[移动端](apps/mobile/LICENSE)许可和各自的 `LICENSING.md`、第三方声明、素材与数据边界共同适用。新整合代码除明确例外外按 AGPL-3.0-only 提供；历史第三方内容继续适用其原条款。

软件许可不扩大真实词典、录音、用户内容、商标或购买素材的授权。去品牌化仍须保留 E方言及历史贡献者署名。[固定来源记录](docs/attribution/sources/sources.json)可追溯组件基线；未获许可的 quick-start 实现未随包交付，其[来源说明](docs/attribution/quick-start.md)不授予再分发权。

这是源码部署包；首次构建需要网络，不包含真实资料、凭据、运行卷或可跨机器直接运行的离线镜像。当前工作对应的验证范围以[本轮验收记录](docs/development/onboarding-validation.md)为准，历史记录不代表本轮已通过。
