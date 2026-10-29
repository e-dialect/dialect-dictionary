# 常见错误与排查

先确认终端位于项目根目录。以下原始英文提示保留原样，便于对照；不要把完整日志中的邮箱、重置链接、私有路径或密钥公开发出。

## 安装与启动

| 现象/提示 | 含义与处理 |
| --- | --- |
| `./dictionary: No such file or directory` | 当前目录不对，进入包含 `dictionary` 和 `compose.yaml` 的目录 |
| `Permission denied`（执行入口时） | 可先用 `python3 dictionary init` / `python3 dictionary start`；不要为此修改系统安全策略 |
| `Cannot connect to the Docker daemon` | Docker服务未启动或当前用户无已有访问权限；先用 `docker version` 检查，不自动提升账号权限 |
| 提示先执行 `./dictionary init` | 尚无 `.env`；初始化后编辑配置，再 `./dictionary check` |
| `port is already allocated` | 端口占用；同步修改 `.env` 的 `HTTP_PORT` 和站点JSON的两个网页URL |
| `all predefined address pools have been fully subnetted` | 本机自动网络池耗尽；按[安装指南](install.md#遇到问题)核验空闲子网后使用现有network组合，不删除其他项目网络 |
| 不识别 `!override` | Traefik组合需要 Compose 2.24.4或更新版本；不要删除该标记，否则可能保留本机端口 |
| `network ... declared as external, but could not be found` | 已有Traefik网络名称不对或尚不存在；找管理员核对，不自动创建同名替代网络 |
| `DOMAIN必须是小写ASCII域名` / HTTPS地址不一致 | `DOMAIN`不填scheme或端口；JSON的 `webUrl`、`mobileUrl` 与同一域名对应，API为同域 `/api` |

下载依赖较慢时先看构建日志，不同时重复启动多套构建。失败后修复具体问题；已有两张完整本地镜像时，可用 `./dictionary start --no-build --pull never`，这不会替你补上缺失镜像。

网站未就绪时查看：

```sh
docker compose ps -a
docker compose logs --tail=80 backend website
```

这两条适用于普通 `.env` 实例。使用代理、恢复副本或自定义组合时，必须沿用原来的 `--env-file`、`-p`、`-f`，否则可能查错项目；[备份指南](backup.md)提供三种模式的统一选择方式。

## 资料包

| 提示中的关键词 | 含义与处理 |
| --- | --- |
| `expected five-column header` | 词表必须是五列TSV，首行为“编号、普通话、方言、发音、注释”，用真正TAB分隔 |
| `decode/parse failed` | 按[资料包格式](packages/README.md)保存UTF-8或带BOM的UTF-16，不猜编码、不静默改音标 |
| `missing audio` / `Extra audio` / `Duplicate` | 编号与音频缺失、多余或冲突；根据预览的行号和文件名修正 |
| `Unsupported/extra file` / `FLV` | 不支持该文件或多了一层ZIP根目录；只支持声明的格式，不自动转码 |
| `exceeds limits` | 超过5000个条目、32MiB单文件或128MiB总量；不能宣称大包已适配 |
| `Unsafe package path` / `Symlink forbidden` | 路径不安全或存在链接；保留原件，整理有权使用的普通文件，不绕过校验 |
| `Importer ... does not exist` | 需要已存在的登录用户名；先按指南建立自己的账号，不填数据库ID |
| `different digest` | 同包ID的内容发生变化；核对来源，为新的资料版本使用新ID，不覆盖旧包 |
| `different publication state` | 同包已按另一公开状态导入；当前不提供就地切换，不改ID制造一份意外公开副本 |
| `Import busy` | 同包正在被另一进程导入，等待结束再重试；不要删除正在使用的锁文件 |
| `Residual import ...` | 上次中断的残留与本次包不完全一致；停写、备份并核对，不直接删除有价值资料 |

`preview` 无写入；`--publish` 的预览也不会发布。默认导入是私有，成功后匿名详情403/录音404可能是正确行为。公开包也须保持包回执、词条和语音都公开，不能把隐藏按钮当成媒体权限。

## 备份与恢复

`FileExistsError` 或目标已存在时换一个新的快照文件名/恢复目录，不覆盖旧备份。校验和、SQLite完整性或外键检查失败时保留原件，停止恢复；不要重写清单让错误“通过”。

恢复后站点可用但录音仍指向旧域名时，检查数据库中保留的绝对媒体URL。修改站点JSON不会重写已有URL；保留旧地址兼容或另外制定可回滚的URL迁移，不对原库批量替换。完整步骤见[备份恢复指南](backup.md)。
