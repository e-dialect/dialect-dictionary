# 安装与日常使用

从[README](../README.md)的两条启动命令开始；本文处理安装包校验、配置与常见问题。备份和迁移见[独立指南](backup.md)。所有命令在仓库或解压包根目录执行。

## 准备环境与源码

需要 Docker Engine、Compose v2、Python 3.10+。首次构建需要访问基础镜像与依赖仓库。Docker Desktop 用户先启动桌面程序，再在终端检查：

```sh
docker version
docker compose version
python3 --version
```

第一次获取源码可选择 Git：

```sh
git clone https://github.com/e-dialect/dialect-dictionary.git
cd dialect-dictionary
```

也可在仓库页面选择 **Code → Download ZIP**，解压后进入包含 `dictionary`、`compose.yaml` 的目录。不要直接在压缩包预览窗口运行命令。GitHub 自动生成的源码 ZIP 没有本项目的发布清单，不需要运行下方清单校验；可先执行 `python3 dictionary version` 查看可用版本信息，未包含提交元数据时会显示 unknown。

使用带 `RELEASE.json` / `MANIFEST.json` 的专门交付归档时，把包解压到新的安装目录，进入其中的 `dialect-dictionary/`，先核对交付清单：

```sh
python3 tools/verify_package.py
cat VERSION
```

`RELEASE.json` 和 `MANIFEST.json` 由打包流程产生；Git 工作区通常没有这两份文件。校验失败时停止并核实交付来源，不要重写清单消除差异。文件哈希用于发现内容变化，不等同于发布者签名。

## 初始化和修改站点

```sh
./dictionary init
```

这会从示例生成 `.env`、`config/site.json`，不覆盖已有文件。用文本编辑器修改：

| 文件 | 常改内容 |
| --- | --- |
| `.env` | `HTTP_PORT`（本机端口）、`COMPOSE_PROJECT_NAME`（实例名）、`SEED_DEMO`（是否插入空库演示词条） |
| `config/site.json` | 站名、方言、Logo、内容来源、`webUrl`、`mobileUrl` |

默认端口是 `18080`。换成 `18081` 时，也把 JSON 中的 `webUrl` 改为 `http://localhost:18081`，`mobileUrl` 改为 `http://localhost:18081/mobile`。默认 API 为同源 `/api`。公开 JSON 不得填写密钥。

空库默认插入技术演示词条；`.env` 设置 `SEED_DEMO=0` 可禁用。已有非空词库不会被演示内容覆盖。方言专属教学、称谓等功能默认关闭，打开开关还需完成内容与方言适配，见[配置说明](../tools/frontend-config/README.md)。

## 启动、检查、停止

```sh
./dictionary start
docker compose ps
curl --fail http://localhost:18080/healthz
```

首次构建可能较慢。浏览器打开首页和 `/mobile/`，确认站名、方言和词条读取；健康接口可达并不证明全部业务和权限正确。导入整包按[资料包指南](packages/README.md)操作。

```sh
./dictionary stop
./dictionary start --no-build --pull never
```

停止保留数据；第二条适用于已有所需本地镜像。另一台主机没有镜像时用普通 `./dictionary start` 从源码构建。镜像平台必须与主机匹配；可变的 `latest` 标签不能证明是同一版本，搬家时记录镜像 ID 和平台。

## 遇到问题

- **Docker 无法连接**：先确认 Docker 服务已启动。
- **端口占用**：修改 `.env` 的 `HTTP_PORT`，同步 JSON 中两个访问地址，再启动。
- **网站未就绪**：运行 `docker compose ps` 和 `docker compose logs --tail=80 backend website`，检查构建、迁移或配置错误。日志可能含邮箱和重置链接，分享前先去除私有信息。
- **网络地址池耗尽**：检查主机与 Docker 路由，请管理员确认一个未占用且不重叠的私有 CIDR，然后在同一终端导出 `DICTIONARY_SUBNET`（例如 `export DICTIONARY_SUBNET=10.253.23.0/24`，这个值只是示例，不能未经检查照抄）。再运行 `./dictionary start --no-build --pull never`，复用此次已完成的镜像。CLI 会加入 `ops/compose/network.yaml`；仅写入 `.env` 不能让当前 CLI 选择该覆盖文件。后续操作在该终端保留此变量；不要清理其他项目的网络。
- **管理账号**：运行 `./dictionary manage createsuperuser`，按提示设置自己的账号和密码。真实邮件、微信登录、云存储需另配服务；默认邮件输出到容器日志。

默认仅绑定 `127.0.0.1`。已有 Traefik 的域名部署请使用[专门指南](traefik.md)，不要把本机 HTTP 地址当成已部署的 HTTPS 服务。使用 Traefik 时启停都带 `--traefik`。

## 多个独立词典与升级

新手建议为每个词典复制一份干净安装目录，分别初始化，使用不同的 `COMPOSE_PROJECT_NAME`、`HTTP_PORT` 和站点配置。实例名决定默认数据卷隔离；已有数据的实例不要随意改名，也不要让两个可写实例共享恢复目录。

升级前按[备份指南](backup.md)停写并演练恢复，保存旧源码、旧镜像及有效配置。需要回滚时使用旧镜像与匹配的升级前快照；不能直接把新版本已迁移的数据库交给旧版本。
