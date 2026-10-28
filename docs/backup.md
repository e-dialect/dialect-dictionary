# 备份、搬家与回滚

备份前停止所有写入，恢复到新目录验证后再切换。复制源码目录不会带走 Docker 数据卷；不要只复制运行中的 SQLite 主文件。

以下命令适用于默认 `.env` 实例，在安装根目录执行。若用了自定义配置、额外 Compose 覆盖或 Traefik，先确认命令选中原来的 project、数据卷和有效配置。Traefik 实例启停使用 `./dictionary --traefik stop` / `./dictionary --traefik start --no-build --pull never`。

## 备份前准备

快照包括数据库、本地媒体、私有导入录音、卷内其他文件、配置和版本记录，可能包含密钥、个人信息和未公开资料。它是私有备份，不可混入公开源码包或上传公开仓库。远端对象存储内容、外部环境变量中的密钥、Traefik 和 DNS 配置需要单独保存。

确认 `config/site.json` 与 `config/` 中策略文件就是实际使用的内容；若 `.env` 指向其他目录，下方 `/instance-config` 挂载须改为对应的有效配置目录。另行私下保存 `.env`、`.env.traefik` 和外部密钥来源。

记录版本和所用镜像，保存输出到自己的运维记录：

```sh
./dictionary version
docker compose images
```

`config/version.json` 记录本地源码版本；它不证明运行镜像由同一份源码构建。用 `docker image inspect 你的镜像名` 另记镜像 ID、系统和架构；保留旧镜像或自行导出镜像以便搬家。源码包与数据快照均不包含镜像。

## 停写并生成快照

先停止网站、后端，以及外部脚本、管理任务和其他共享此数据卷的写入进程：

```sh
./dictionary stop
docker compose ps -a
mkdir -p backups
docker compose run --rm --no-deps --entrypoint python \
  -v "$PWD:/package:ro" \
  -v "$PWD/config:/instance-config:ro" \
  -v "$PWD/backups:/backups" \
  backend /package/tools/offline_snapshot.py backup \
  --data /data --config /instance-config \
  --release /package/config/version.json \
  --output /backups/snapshot.tar.gz
```

`--no-deps` 防止启动服务，替换入口避免应用自动迁移。脚本检查 SQLite 完整性和外键，生成文件哈希清单，拒绝覆盖已有输出。已有 `snapshot.tar.gz` 时换一个新名字；保留原备份和命令返回的 SHA256。

脚本为兼容快照结构，将传入的版本记录在归档内命名为 `RELEASE.json`。它仍只是本地版本记录，不是额外的发布认证或签名。

备份成功后，如需继续原实例：

```sh
./dictionary start --no-build --pull never
curl --fail http://localhost:18080/healthz
```

按实际端口调整健康检查。一次备份成功还不等于恢复可用，继续在副本演练。

## 恢复到新目录

把源码、私有快照和所需镜像带到目标主机，保持原始快照不变。下方目标目录 `runtime/recovery-check` 必须不存在：

```sh
python3 tools/offline_snapshot.py restore \
  --archive backups/snapshot.tar.gz --target runtime/recovery-check
cat runtime/recovery-check/RELEASE.json
```

工具验证归档路径、哈希、SQLite 完整性与外键，创建 `data/` 和 `config/`。目标存在会拒绝覆盖；校验失败保留现场，不要继续启动。

恢复前选择与快照数据库结构匹配的后端、网站镜像。新镜像启动可能执行迁移；不能随意使用新版本检验旧备份。若依赖外部私有密钥，通过原有私有渠道恢复；使用卷内密钥时保留恢复数据中的密钥，避免环境变量意外覆盖。

只修改恢复副本的 `config/site.json`，将 `webUrl` 改为 `http://localhost:18082`，`mobileUrl` 改为 `http://localhost:18082/mobile`。这不会自动修改数据库中已有的绝对媒体 URL。然后设置：

```sh
export RESTORED_DATA="$PWD/runtime/recovery-check/data"
export SITE_CONFIG="$PWD/runtime/recovery-check/config/site.json"
export FEATURE_POLICY_DIRECTORY="$PWD/runtime/recovery-check/config"
export FEATURE_POLICY_FILE=feature-policy.example.json
export HTTP_PORT=18082
export BACKEND_IMAGE=你保存的后端镜像标签
export WEBSITE_IMAGE=你保存的网站镜像标签
```

将策略文件名改为备份时实际生效的文件名；过期策略仍应关闭，不能为恢复演练擅自延长授权。不要将 `RESTORED_DATA` 指向原实例，也不要让两个可写实例共享此目录。

```sh
docker compose -p dictionary-restored -f compose.yaml \
  -f ops/compose/restore.example.yaml config --quiet
docker compose -p dictionary-restored -f compose.yaml \
  -f ops/compose/restore.example.yaml up -d --no-build --pull never
docker compose -p dictionary-restored -f compose.yaml \
  -f ops/compose/restore.example.yaml ps
curl --fail http://localhost:18082/healthz
```

保持 `compose.yaml` 为第一个文件，辅助文件里的相对路径以根目录为基准。独立 project 配合恢复目录隔离数据；同一主机恢复演练不能证明另一台主机或另一种架构可用。

## 检查后再切换

至少核对以下内容，并记录镜像 ID 与版本：

- 首页和手机网页的站名、方言、代表性词条、记录数量。
- 录音播放和恢复前后文件哈希，私有录音不会通过公开媒体地址泄漏。
- 来源、许可和发布状态仍正确，私有资料不会自动公开。
- 真实账号角色权限，以及贡献关闭后后端仍拒绝写入。

演练结束，用同样两项 `-f` 和 project 停止副本：

```sh
docker compose -p dictionary-restored -f compose.yaml \
  -f ops/compose/restore.example.yaml stop
```

通过检查后再安排域名或代理切换，并让新旧实例的写入安排明确。保留原快照、原镜像和恢复记录。

## 升级失败时回滚

升级前先保存可恢复快照、旧源码、旧镜像和配置。回滚使用**旧镜像和匹配的升级前快照**，按上述步骤恢复到新目录；已被新版本迁移的数据库不能直接交给旧版本。

回到旧快照会丢失其后产生的修改。切换前停止写入，另存新版本当前快照，并审阅新增数据的导出与合并方案；没有完成方案时保留副本，不覆盖原数据。这里不提供生产环境的自动回滚或无损合并保证。
