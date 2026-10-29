# 目录与配置说明

普通部署者主要使用根目录的 `dictionary`、`.env`、`config/` 和 `docs/`。修改站名、方言或端点通常不需要修改 `apps/` 里的源码。

```text
dialect-dictionary/
  dictionary              日常命令入口
  compose.yaml            本机网站的服务定义
  .env.example            运行参数模板
  config/                 站点配置和服务端策略示例
  packages/examples/      原创合成资料包，供校验和演示
  docs/                   中文安装、导入、代理和备份指南
  apps/                   后端、电脑网页、Uni-App源码
  ops/                    镜像构建和可选部署组合
  tools/                  配置生成、备份、校验等工具
```

`./dictionary init` 创建 `.env`、`config/site.json` 和版本记录，不覆盖已有文件；它不创建账号，也不导入真实词典。

## 哪些地方由你填写

| 文件/位置 | 内容 | 注意 |
| --- | --- | --- |
| `.env` | 实例名 `COMPOSE_PROJECT_NAME`、本机端口 `HTTP_PORT`、镜像和策略文件位置 | 实例名决定默认数据卷名称；有数据后不要随意改名 |
| `config/site.json` | `name`、`shortName`、`dialect`、`logo`、`contentSource`、`webUrl`、`mobileUrl`、`apiBase` | 会发送给浏览器，不能填写密钥；默认 `/api` 只适用于同源网页 |
| `config/feature-policy.example.json` 或自己配置的策略文件 | 允许的贡献功能、平台、角色与有效期 | 按[服务端策略](server-feature-policy.md)配置；公开页面开关不代替后端权限 |
| `.env.traefik` | 已有代理的域名、网络、入口和证书解析器名称 | 从对应 example 复制；不启动第二套代理 |
| `.env.traefik-standalone` | 新服务器独立代理参数 | 从对应 example 复制；启动会注册/使用证书服务，须由运营者自行准备 |

`config/examples/coast.json` 与 `mountain.json` 是不同品牌/方言的演示配置；`hinghwa.json` 保留兴化语记实例所需的特有功能设置。启用开关不等于自动获得对应方言内容或媒体授权，见[前端配置](../tools/frontend-config/README.md)。

## 数据究竟在哪里

数据库、录音和实例私有文件保存在 Docker 的 `dictionary-data` 数据卷；它不是根目录的 `packages/`，也不是 `apps/`。`packages/examples/` 只放合成样例，自己的资料包可放在任意有权读取的目录，再把路径交给 `preview` / `import`。

新导入录音在容器内 `/data/private-imports/`，即使显式公开也由已提交回执和权限门禁控制读取。复制源码不能备份数据卷。`backups/` 是按[备份指南](backup.md)生成私有快照的位置，不应提交或公开上传。

## 开发者才需要关注的目录

- `apps/backend/hinghwa-dict-backend/`：Django业务工程；上层 `apps/backend/` 保留组件许可证。
- `apps/web/`：电脑网页；`apps/mobile/`：Uni-App手机网页与小程序源码。
- `ops/docker/`：镜像及代理模板；`ops/compose/`：Traefik、恢复副本、网络等可选组合。
- `tools/`：工具和离线测试；`docs/development/`：开发及历史验收；`docs/attribution/`：来源与第三方归属。

`runtime/`、`artifacts/` 和日志可能只存在于本地开发环境，不是安装必需项。不要删除许可证、署名或数据来源来简化目录。
