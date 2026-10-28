# 接入已有 Traefik

本模式适用于已运行的 Traefik Docker provider。先由管理员确认已有 HTTPS entrypoint、证书 resolver 与外部 Docker network 的准确名称，然后填写 `.env.traefik.example` 所示公开参数；本项目不会启动第二个 Traefik、绑定 80/443、挂载 Docker socket、创建 ACME 账户或改写已有证书存储。resolver 的名称必须已经存在；本项目不提供 ACME 邮箱、密钥或证书存储配置。

最低 Docker Compose **2.24.4**。`ops/compose/traefik.yaml` 使用 `ports: !override []` 完整替换本机端口列表；普通 `ports: []` 无法移除基础文件的端口。旧版 Compose 必须升级后再解析，不能删除此标记来绕过兼容性检查。

## 公开配置与同域要求

`.env` 是独立的运维参数，不能混入站点 JSON，也不能直接接收未校验的用户输入。启动前的 onboarding 校验必须检查：

- `DOMAIN` 是小写 ASCII DNS 完整域名，每段 1–63 字符，总长不超过 253；仅允许字母、数字与段内连字符。不得含 scheme、端口、路径、通配符、反引号、引号、逗号、空白或 Compose 插值字符。国际化域名使用已核对的 punycode。
- `TRAEFIK_NETWORK`、`TRAEFIK_ENTRYPOINT`、`TRAEFIK_CERTRESOLVER`、`TRAEFIK_ROUTER_NAME` 仅接受 `[A-Za-z0-9][A-Za-z0-9_.-]*`；router 名须在已有 Docker provider 中唯一。
- 站点 JSON 的 `webUrl` 为 `https://DOMAIN`，`mobileUrl` 为 `https://DOMAIN/mobile`，`apiBase` 为 `/api` 或 `https://DOMAIN/api`。这些参数同时决定 Django Host 白名单、CORS 与 CSRF 来源；不要单独在 `.env` 另配宽泛的来源白名单。

Django 启动时会再次检查 DOMAIN 与站点 URL 的一致性。Compose 的 `${VAR:?}` 只保证非空，不能替代上述 schema 校验。直接运行 Compose 前也必须先完成参数校验；不要把外部文本拼进 label。

首次配置已有 Traefik 时，从仓库根目录执行：

```sh
./dictionary init
cp .env.traefik.example .env.traefik
# 用编辑器填写 .env.traefik 中现有的域名、network、entrypoint、resolver 和唯一 router 名。
# 同时把 config/site.json 的 webUrl/mobileUrl 改成上文一致的 HTTPS 地址。
./dictionary --traefik check
```

已有 `.env.traefik` 时直接编辑，不要再次复制覆盖。`check` 不构建、不启动服务，也不申请证书；校验通过后才运行 `./dictionary --traefik start`。停止使用 `./dictionary --traefik stop`，数据卷保留。

校验后可只读检查合并结果（从项目根目录运行，Compose 自动读取 `.env`）：

```sh
docker compose --env-file .env --env-file .env.traefik -f compose.yaml -f ops/compose/traefik.yaml config
```

检查 `website.ports` 为空、`backend` 无 published ports、`website` 同时连接项目 default 与既有外部 network、`backend` 只连接 default。然后沿用项目 onboarding 的构建/启动入口选择 Traefik 模式。`SITE_CONFIG` 挂载路径与常规模式一致。已有网络不存在时应停止并向它的管理员核对，不要自动新建同名网络或更改宿主安全策略。

## HTTPS 信任边界

流量路径为：浏览器 HTTPS → 已有 Traefik 的 TLS router → 外部 network 上的 `website:8080` → 项目 default network 上的 `backend:8000`。本 overlay 仅为 website 添加 labels 与外部 network；backend 显式设置 `traefik.enable=false`。

`PROXY_MODE=traefik` 使 website 选择 `ops/docker/nginx.traefik.conf`，其 `/api/` 代理将 `X-Forwarded-Proto` **固定覆写为 `https`**，不会读取客户端的同名 header，也不会信任逗号列表中的 scheme。Django 仅在这个明确模式下设置 `SECURE_PROXY_SSL_HEADER`，并启用 Secure session/CSRF cookie。这是 HTTPS-only 入口；不要为同一 website 再添加明文 HTTP router、host port 或旁路代理。HTTP→HTTPS 跳转如有需要，由已有 Traefik 的管理员统一维护。

共享外部 network 上的所有容器，以及项目 default network 上的容器，都在此信任边界内；它们可以直接访问内部 HTTP。该方案依赖这些网络成员可信，不提供不可信同网租户隔离。需要多租户隔离时，必须由管理员提供独立受控入口网络或审计严格的代理 IP 信任链，不能仅依靠转发 header。

常规本机模式使用 `PROXY_MODE=local`（默认）与普通 nginx 模板：nginx 使用自身 `$scheme`，Django 的 `SECURE_PROXY_SSL_HEADER=None`，客户端伪造 `X-Forwarded-Proto: https` 不能让 HTTP 请求变为 secure。不要手工只给 backend 开启 Traefik 模式。

## 验证范围

```sh
python3 -m unittest discover -s tools -p test_proxy_config.py -v
# 在已有后端测试环境内，以合成配置/临时数据库运行：
python manage.py test HinghwaDict.test_proxy_scheme --settings=HinghwaDict.standalone
```

离线测试覆盖两种模式的真实设置代码、模板禁止透传客户端 scheme、overlay 移除 host ports；Django 测试覆盖 `request.is_secure()`、HTTPS 管理员登录的 CSRF token、恶意 Origin、Host 拒绝和 Secure cookie。完整容器检查还需覆盖 `/`、`/mobile/`、`/api/` 与媒体路径，以及伪造单个和逗号列表 scheme 时 nginx 的真实覆写行为。

这些检查使用合成 HTTP 请求，不代表公网 DNS、真实 TLS 握手、ACME 签发/续期或现有 Traefik 实例已经验收。本次配置工作未启动公网服务、未下载镜像、未申请真实证书。

## 官方依据（2026-10-28 核对）

- [Docker Compose merge](https://docs.docker.com/reference/compose-file/merge/)：`!override` 需要 Compose 2.24.4+，ports 默认合并行为不会自动清空绑定。
- [Traefik v3.5 Docker routing](https://doc.traefik.io/traefik/v3.5/reference/routing-configuration/other-providers/docker/) 与[当前 Docker routing 文档](https://doc.traefik.io/traefik/reference/routing-configuration/other-providers/docker/)：显式 network、router/service、TLS 与内部端口 labels。此处没有指定或升级既有 Traefik 镜像版本，管理员须核对其实际运行版本。
- [Traefik ACME resolver](https://doc.traefik.io/traefik/reference/install-configuration/tls/certificate-resolvers/acme/)：resolver/账户/存储由已有 Traefik 维护；本项目只引用 resolver 名称。
- [Django 5.0 proxy SSL 设置](https://docs.djangoproject.com/en/5.0/ref/settings/#secure-proxy-ssl-header)（对应项目 pin 5.0.3）与[受支持版本 5.2 文档](https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header)：只有代理保证覆写 header 时才可启用该设置。官方已将 Django 5.0 标为不再受支持；此次接入未擅自修改现有依赖锁。

## 新主机：由项目独立启动 Traefik

仅适用于尚无反向代理、80/443 空闲的新服务器；已有 Traefik 的主机必须使用前文接入分支，不能运行本分支。复制并填写公开参数，站点 JSON 仍须使用相同 HTTPS 域名：

```sh
cp .env.traefik-standalone.example .env.traefik-standalone
# 编辑 DOMAIN、ACME_EMAIL 与站点 JSON，确认网络名独一无二后：
./dictionary --traefik-standalone check
./dictionary --traefik-standalone start
```

CLI 依次合并 `compose.yaml`、`ops/compose/traefik.yaml`、`ops/compose/traefik-standalone.yaml`。第三层才会添加 `proxy` 服务，绑定 80/443、将 network 改为自有 bridge，并使用项目命名空间下的 `standalone-acme` 卷；不得指向已有代理的网络或 ACME 存储。`TRAEFIK_ENTRYPOINT` 不能为保留的 HTTP 入口 `web`。`ACME_EMAIL` 必须由运营者自行填写；启动将向证书机构注册并按条款申请证书，DNS 须预先指向服务器，80/443 须已可达。本次配置没有代为创建账户、开放防火墙或申请证书。

website/backend 继续使用上述固定 HTTPS scheme；HTTP 仅用于挑战和 HTTPS 重定向。Docker provider 使用 `exposedByDefault=false`，不启用 dashboard，socket 以只读挂载；只读挂载仍不等于 Docker API 权限隔离，能访问 socket 的 proxy 属于受信宿主管理边界。需要更细权限时由管理员另行配置受限 socket proxy；本示例不修改宿主权限。

2026-10-28 核对后固定为 [Traefik v3.7.16](https://github.com/traefik/traefik/releases/tag/v3.7.16)（2026-10-20 发布）；[支持矩阵](https://doc.traefik.io/traefik/deprecation/releases/)列出 3.7 仍受支持。provider/socket 边界见[官方 Docker provider 文档](https://doc.traefik.io/traefik/reference/install-configuration/providers/docker/)，email、存储及 HTTP-01 条件见[官方 ACME 文档](https://doc.traefik.io/traefik/reference/install-configuration/tls/certificate-resolvers/acme/)。本分支仅做 Compose 静态合并校验，未拉取或启动该镜像，公网、证书签发与续期未验证。
