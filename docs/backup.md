# 备份、搬家与回滚

备份前停止所有写入，恢复到新目录验证后再切换。复制源码目录不会带走 Docker 数据卷；不要只复制运行中的 SQLite 主文件。

所有命令在项目根目录、Bash/Zsh终端执行。先选中**实际运行的模式**，本节三个命令块只执行一个；后面统一用 `"${DC[@]}"` 操作。独立Traefik模板可能设置不同的实例名，不能省略其env文件后对默认卷做备份。

普通本机实例：

<!-- compose-local -->
```sh
DC=(docker compose --env-file .env -f compose.yaml)
```

接入已有Traefik：

<!-- compose-existing-traefik -->
```sh
DC=(docker compose --env-file .env --env-file .env.traefik -f compose.yaml -f ops/compose/traefik.yaml)
```

新服务器独立Traefik：

<!-- compose-standalone-traefik -->
```sh
DC=(docker compose --env-file .env --env-file .env.traefik-standalone -f compose.yaml -f ops/compose/traefik.yaml -f ops/compose/traefik-standalone.yaml)
```

若原实例使用了地址池修复，保留原来已核验的 `DICTIONARY_SUBNET`，再执行：

<!-- compose-source-inspect -->
```sh
if [ -n "${DICTIONARY_SUBNET:-}" ]; then DC+=(-f ops/compose/network.yaml); fi
"${DC[@]}" config --services
"${DC[@]}" ps -a
```

确认显示的就是待备份实例；任何自定义组合都需加入同样的选项。不要在恢复副本的终端误操作原实例。

## 备份前准备

快照包括数据库、本地媒体、私有导入录音、卷内其他文件、配置和版本记录，可能包含密钥、个人信息和未公开资料。它是私有备份，不可混入公开源码包或上传公开仓库。远端对象存储内容、外部环境变量中的密钥、Traefik 和 DNS 配置需要单独保存。

确认 `config/site.json` 与 `config/` 中策略文件就是实际使用的内容；若 `.env` 指向其他目录，下方 `/instance-config` 挂载须改为对应的有效配置目录。另行私下保存实际使用的 `.env`、`.env.traefik` 或 `.env.traefik-standalone` 和外部密钥来源。

记录版本和所用镜像，保存输出到自己的运维记录：

```sh
./dictionary version
"${DC[@]}" images
```

`config/version.json` 记录本地源码版本；它不证明运行镜像由同一份源码构建。用 `docker image inspect 你的镜像名` 另记镜像 ID、系统和架构；保留旧镜像或自行导出镜像以便搬家。源码包与数据快照均不包含镜像。

## 停写并生成快照

先停止网站、后端，以及外部脚本、管理任务和其他共享此数据卷的写入进程：

```sh
"${DC[@]}" stop
"${DC[@]}" ps -a
mkdir -p backups
"${DC[@]}" run --rm --no-deps --entrypoint python \
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
"${DC[@]}" up -d --wait --no-build --pull never
curl --fail http://localhost:18080/healthz
```

按实际端口调整健康检查。一次备份成功还不等于恢复可用，继续在副本演练。

## 恢复到新目录

另开一个终端进入安装根目录，仅在这个终端设置恢复副本参数，避免影响原实例的配置。把源码、私有快照和所需镜像带到目标主机，保持原始快照不变。下方目标目录 `runtime/recovery-check` 必须不存在：

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
RC=(docker compose --env-file .env -p dictionary-restored -f compose.yaml -f ops/compose/restore.example.yaml)
# 若本机需要地址池修复，这里使用另一个已核验且不重叠的子网。
if [ -n "${DICTIONARY_SUBNET:-}" ]; then RC+=(-f ops/compose/network.yaml); fi
"${RC[@]}" config --quiet
"${RC[@]}" up -d --wait --no-build --pull never
"${RC[@]}" ps
curl --fail http://localhost:18082/healthz
```

保持 `compose.yaml` 为第一个文件，辅助文件里的相对路径以根目录为基准。独立 project 配合恢复目录隔离数据；同一主机恢复演练不能证明另一台主机或另一种架构可用。

## 检查后再切换

至少核对以下内容，并记录镜像 ID 与版本：

- 首页和手机网页的站名、方言、代表性词条、记录数量。
- 录音播放和恢复前后文件哈希，私有录音不会通过公开媒体地址泄漏。
- 来源、许可和发布状态仍正确，私有资料不会自动公开。
- 真实账号角色权限，以及贡献关闭后后端仍拒绝写入。

演练结束，用同一 `RC` 选择停止副本，再清除这个终端中的临时变量：

```sh
"${RC[@]}" stop
unset RESTORED_DATA SITE_CONFIG FEATURE_POLICY_DIRECTORY FEATURE_POLICY_FILE HTTP_PORT BACKEND_IMAGE WEBSITE_IMAGE
# 若这个终端也设置了仅供恢复副本使用的DICTIONARY_SUBNET，用完一并清除。
unset DICTIONARY_SUBNET
```

通过检查后再安排域名或代理切换，并让新旧实例的写入安排明确。保留原快照、原镜像和恢复记录。

## 升级失败时回滚

升级前先保存可恢复快照、旧源码、旧镜像和配置。回滚使用**旧镜像和匹配的升级前快照**，按上述步骤恢复到新目录；已被新版本迁移的数据库不能直接交给旧版本。

回到旧快照会丢失其后产生的修改。切换前停止写入，另存新版本当前快照，并审阅新增数据的导出与合并方案；没有完成方案时保留副本，不覆盖原数据。这里不提供生产环境的自动回滚或无损合并保证。


## 验证边界

已用合成SQLite/媒体/配置检查快照校验和、拒绝覆盖、非法路径和损坏快照，并在同一主机的隔离实例做过恢复验证。这不等于第二主机、不同架构或跨版本迁移/回滚已通过；当前图片、录音、远端对象与账号权限仍须按你的实际部署逐项核验。详见[验收记录](development/onboarding-validation.md)；错误含义见[常见错误](troubleshooting.md#备份与恢复)。
