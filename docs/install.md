# 源码包安装、备份恢复与回滚

本文面向交付源码包及 Docker Compose v2。示例只发布本机 Web/H5，不连接生产实例。全新目录、独立 Compose project 和独立数据卷用于隔离；在同一主机执行不代表已在第二台主机验证。

## 1. 包与运行前提

- 需要 Docker Engine、Compose v2、宿主 Python 3.10 或更高版本、`tar`、`curl`；另机源码构建还需要网络、基础镜像仓库和依赖仓库可达。
- 包内 `VERSION` 为发行版本，`RELEASE.json` 记录来源/发行信息，`MANIFEST.json` 记录交付文件校验信息；以实际文件为准，不以可变的 `latest` 标签作为版本证据。
- 这是源码包，不是离线镜像包。首次运行前必须有相应镜像，或按下文顺序构建。机器架构必须与所用镜像匹配。
- 包不包含运行卷、真实词典/用户数据、私有配置、凭据、远端对象或模型。镜像、数据快照与源码包是三类独立交付物。

将收到的包解压到尚不存在的安装目录。以下包路径、目录名均应替换为自己的值；目录名不要与先前验收目录重复：

```sh
SOURCE_PACKAGE=/absolute/path/to/dialect-dictionary-kt2-source.tar.gz
mkdir dictionary-install-fresh
tar -xzf "$SOURCE_PACKAGE" -C dictionary-install-fresh
cd dictionary-install-fresh/dialect-dictionary
python3 scripts/verify_package.py
cat VERSION
cat RELEASE.json
```

先完成校验，再生成本地配置。校验失败应停止，不要用重新生成 manifest 的方式消除差异。哈希校验用于发现内容变动；收到的包本身仍须来自可信交付渠道。

## 2. 本机配置与镜像选择

```sh
cp .env.example .env
cp config/examples/coast.json config/site.json
```

`.env.example` 仅含公共部署参数，站点 JSON 会送到浏览器，均不得填入密钥。检查 `.env` 中的 `SITE_CONFIG=./config/site.json`、`HTTP_PORT=18080`、策略目录与文件名；`config/site.json` 的 `webUrl`、`mobileUrl` 必须与实际访问地址/端口一致。默认 API 为同源 `/api`。

Compose 的镜像由 `BACKEND_IMAGE`、`WEBSITE_IMAGE` 选择。**同机复用已有镜像**，先查看身份与平台：

```sh
export BACKEND_IMAGE=dialect-dictionary-candidate-backend:latest
export WEBSITE_IMAGE=dialect-dictionary-candidate-website:latest
docker image inspect "$BACKEND_IMAGE" --format '{{.Id}} {{.Os}}/{{.Architecture}}'
docker image inspect "$WEBSITE_IMAGE" --format '{{.Id}} {{.Os}}/{{.Architecture}}'
```

将 ID、平台与 `RELEASE.json` 的 `validatedLocalImages`（另见 `deploy/validated-images.json`）及交付验收记录比对。这些是已验证主机上的本地身份，不是可从远端拉取的镜像地址。找不到镜像、平台不匹配或身份不符时停止复用；`latest` 同名不保证内容相同。必要时直接将上面两个变量设为核验后的本地 `sha256:...` 镜像 ID。

**另一台主机从源码安装**，在确认 Docker 构建上下文是本包后顺序执行：

```sh
export BACKEND_IMAGE=dialect-dictionary-candidate-backend:0.1.0-candidate.4
export WEBSITE_IMAGE=dialect-dictionary-candidate-website:0.1.0-candidate.4
COMPOSE_PARALLEL_LIMIT=1 docker compose -p dictionary-coast build backend
COMPOSE_PARALLEL_LIMIT=1 docker compose -p dictionary-coast build website
docker image inspect "$BACKEND_IMAGE" --format '{{.Id}} {{.Os}}/{{.Architecture}}'
docker image inspect "$WEBSITE_IMAGE" --format '{{.Id}} {{.Os}}/{{.Architecture}}'
```

此分支独立设置正常可构建标签，不依赖上面的同机分支或仅供Compose读取的`.env`变量，也不会沿用先前导出的`sha256:...`作为构建标签。记录新构建的镜像 ID。此流程会下载基础镜像及锁定依赖，不声称已离线安装或与已有镜像逐字节相同。`compose.prebuilt.yaml` 仅替换网站构建入口，不能代替完整镜像的离线分发。

## 3. 启动与健康验收

以下两项固定测试值仅供空库、合成数据的本机复现；它们是公开示例，不是可用于实际服务的凭据，也不会提供安全身份保证。测试时显式传入，避免自动生成持久密钥：

```sh
export SECRET_KEY=local-synthetic-only-do-not-use-for-real-data
export JWT_KEY=local-synthetic-only-do-not-use-for-real-data
docker compose -p dictionary-coast config --quiet
docker compose -p dictionary-coast up -d --no-build --pull never
docker compose -p dictionary-coast ps
curl --fail http://localhost:18080/healthz
curl --fail http://localhost:18080/site-config.json
curl --fail -o /dev/null http://localhost:18080/
curl --fail -o /dev/null http://localhost:18080/mobile/
curl --fail http://localhost:18080/api/capabilities
```

等待两个服务变为 healthy。健康接口检查后端可达，不证明业务、媒体或权限全部正确；另用浏览器检查站名、方言、Web 与 `/mobile/`，并检查实际词条读取。若验收包含合成媒体，比较恢复前后媒体 URL 返回的字节及哈希。

默认 `SEED_DEMO=1`，仅空词库插入明确标记的技术演示词条；非空词库不会被覆盖。需要禁用时在部署配置设 `SEED_DEMO=0`。示例品牌没有真实方言词典或录音，不应作为语言学数据使用。

实际数据部署应沿用已审阅的私有密钥管理方式，或由部署者提供私有环境变量；不要使用上面的测试值，也不要把密钥提交进源码包。若此前使用卷内持久密钥，恢复时保留该卷内容，并取消测试环境变量覆盖，避免改变签名密钥导致会话/token 失效。默认邮件输出容器日志；真实邮件、微信登录、云存储需另配自己的服务。

排查时只在本地查看必要日志，注意日志可能含邮箱、重置链接等私有信息：

```sh
docker compose -p dictionary-coast logs --tail=80 backend website
```

默认 HTTP 仅绑定 `127.0.0.1`。访问地址决定后端允许的 Host、CORS 与 CSRF 来源；修改域名后同步修改站点 JSON 并重建容器。开放公网、TLS、反向代理与生产运维需另行配置和验证。

## 4. 第二品牌独立运行

同一组已核验镜像可供另一实例使用；project、端口和站点配置必须分别指定：

```sh
SITE_CONFIG=./config/examples/mountain.json HTTP_PORT=18081 \
  docker compose -p dictionary-mountain config --quiet
SITE_CONFIG=./config/examples/mountain.json HTTP_PORT=18081 \
  docker compose -p dictionary-mountain up -d --no-build --pull never
curl --fail http://localhost:18081/healthz
curl --fail http://localhost:18081/site-config.json
```

默认 Compose 命名卷按 project 隔离。用浏览器确认两端站名和方言分别正确，并验证两库互不写入。若修改示例的端口，也要复制配置并修改其 `webUrl`、`mobileUrl`。不要复用同一个 `RESTORED_DATA` 目录给两个可写实例。

停止时同样传入该实例的配置与 project。`docker compose ... stop` 保留卷；`down -v` 会删除命名卷，不是日常停止方式。地址池耗尽时参照 `compose.network.yaml`，先检查主机与 Docker 路由，再显式选择不重叠网段，不能清理他人网络来绕过。

## 5. 停写后备份

快照包含 SQLite 数据、本地媒体和其他卷内文件、站点/策略配置、发行元数据；可能包含私有内容和卷内密钥。它不是可公开源码包：禁止上传到 Library、公开仓库或混入源码交付归档。按私有数据方式保存与传递；远端 COS 对象不在本地卷中，必须另做对象备份并核验访问配置。

以下以标准海岚实例为例，要求当前有效站点文件为 `config/site.json`、策略文件位于 `config/`。若运行配置来自别处，先将其整理为与实际生效内容一致的备份配置目录，并相应修改挂载；仅备份示例文件不能恢复真实部署配置。使用外部环境变量的密钥需通过原有私有渠道单独保管。

先停止本实例全部写入来源，包括 Web/H5、后端、外部脚本、管理任务以及任何共享该卷的进程，再备份。不要在写入过程中复制 SQLite 或仅备份 `.sqlite3` 主文件：

```sh
docker compose -p dictionary-coast stop website backend
docker compose -p dictionary-coast ps -a
mkdir -p backups
docker compose -p dictionary-coast run --rm --no-deps --entrypoint python \
  -v "$PWD:/package:ro" \
  -v "$PWD/config:/instance-config:ro" \
  -v "$PWD/backups:/backups" \
  backend /package/scripts/offline_snapshot.py backup \
  --data /data --config /instance-config \
  --release /package/RELEASE.json --output /backups/snapshot.tar.gz
```

`--no-deps` 避免自动启动网站或后端服务，替换 entrypoint 避免正常启动迁移。快照脚本校验文件哈希、SQLite integrity 和外键，并拒绝覆盖已有输出。若 `snapshot.tar.gz` 已存在，选择新文件名；不要为复用名称覆盖上一份备份。

备份成功后，如需继续原实例，使用原镜像、配置、密钥重新执行：

```sh
docker compose -p dictionary-coast up -d --no-build --pull never
curl --fail http://localhost:18080/healthz
```

恢复演练操作副本；保留原快照。只有完成下一节的恢复、内容及权限核验，才能确认该快照具有已验证的恢复路径。

## 6. 恢复到新目录与新实例

解包恢复不启动应用。下面的目标 `runtime/recovery-check` **必须尚不存在**；脚本创建其中的 `data/`、`config/`、`RELEASE.json`，核对哈希及 SQLite integrity/外键。目标存在或校验失败即停止，保留现场诊断：

```sh
python3 scripts/offline_snapshot.py restore \
  --archive backups/snapshot.tar.gz --target runtime/recovery-check
cat runtime/recovery-check/RELEASE.json
export RESTORED_DATA="$PWD/runtime/recovery-check/data"
export SITE_CONFIG="$PWD/runtime/recovery-check/config/site.json"
export FEATURE_POLICY_DIRECTORY="$PWD/runtime/recovery-check/config"
export FEATURE_POLICY_FILE=feature-policy.example.json
export HTTP_PORT=18082
```

`FEATURE_POLICY_FILE` 必须改为备份时实际生效的文件名。检查恢复的发行信息，选用与数据库 schema 匹配的后端/网站镜像，重新 inspect 并记录 ID。启动可能运行迁移，不能盲用新镜像检验旧备份。

只修改恢复副本 `config/site.json`：将 `webUrl` 改为 `http://localhost:18082`，`mobileUrl` 改为 `http://localhost:18082/mobile`。真实内容中如存有绝对媒体 URL，也需要单独核验；修改公开站点配置不会自动改写数据库中的 URL。策略过期保持关闭，不能为了通过验收擅自延长授权。

先确认恢复副本采用的密钥方式。卷内密钥场景先执行 `unset SECRET_KEY JWT_KEY`；纯合成测试快照若原先使用上述公开测试值，可继续显式使用同样的值。外部私有密钥必须通过原部署渠道恢复，不从源码包推导。

```sh
docker compose -p dictionary-restored -f compose.yaml \
  -f compose.restore.example.yaml config --quiet
docker compose -p dictionary-restored -f compose.yaml \
  -f compose.restore.example.yaml up -d --no-build --pull never
docker compose -p dictionary-restored -f compose.yaml \
  -f compose.restore.example.yaml ps
curl --fail http://localhost:18082/healthz
curl --fail http://localhost:18082/site-config.json
curl --fail http://localhost:18082/api/capabilities
```

恢复覆盖文件将 `${RESTORED_DATA}` 挂到 `/data`，覆盖默认命名卷；路径必须指向刚校验的恢复数据目录。始终保留两项 `-f`、正确 project 和环境变量，避免误用原实例。原实例继续使用其命名卷，恢复实例使用副本；同机演练不证明跨主机兼容。

恢复验收至少记录：发行版本和镜像 ID、两个服务健康、Web/H5 品牌、数据库记录数量及代表性词条、媒体字节哈希、来源/许可字段、真实账号角色约束、关闭贡献后旧客户端被拒绝写入。只读健康或前端隐藏按钮不能替代后端权限校验。演练结束用相同的两项 `-f` 和 project 执行 `stop`，保留恢复目录供复核。

## 7. 升级与回滚边界

升级前停写并生成已验证可恢复的快照，记录旧源码版本、旧镜像 ID、有效配置和私有密钥来源。保留旧镜像；标签可变或镜像已被清理时，无法承诺可回滚。

回滚必须使用**旧镜像 + 与其 schema 匹配的升级前快照**。不能把已被新版本迁移的数据库直接交给旧版本，也不承诺自动反向迁移。按第 6 节恢复到新目录、新 project、新端口，使用旧镜像，完成验证后再由操作者安排切换；本文不提供生产自动回滚。

切换前停止新旧实例的全部写入来源。明确升级后产生的数据如何处理：保留一份新版本停写快照；比较并另行审阅新增/修改内容的导出、合并方案。回到旧快照会丢失快照时间之后的数据，不应悄然覆盖或宣称无损回滚。未确定合并方案时先保持数据副本，不启动两个共享数据目录的可写服务。

## 8. 功能、许可与验证范围

词条贡献策略只管理合法功能的部署开关与真实账号角色，不替代账号权限或平台/内容许可。默认关闭；文件缺失、损坏、过期或角色不合法均关闭写入，历史读取仍受原权限约束。需要开启时按[服务端策略说明](server-feature-policy.md)维护有效期和角色，不能按审核身份或审核阶段改变行为。

交付包排除无上游 LICENSE 的 quick-start `sql.js`、`test_sql.py` 及依赖它们的旧验收脚本。保留的历史适配文档仅说明本地审阅历史，不代表包内提供该导入器或授予再分发许可；不要执行其中依赖被排除文件的旧命令。

保留根及各组件的 AGPL、第三方声明、来源与素材/数据边界。软件许可不授予真实词典、录音、用户内容、商标或购买素材的使用权。导入资料前核验授权与来源署名。

已提供路径以本地 Web/H5 为范围；微信小程序需要自有 AppID、HTTPS API、服务器域名及真机/平台审核，静态编译不能证明已获准发布。可选 ML/语义检索、真实邮件、云对象恢复及生产部署不属于本指南已验证范围。实际通过项目以本次随包验收证据为准，历史构建记录不能替代当前源码包的运行验证。
