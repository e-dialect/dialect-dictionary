# 可配置在线词典 · 本地整合候选

本仓库将真实兴化语记后端、Web 与 Uni-App 源码整合为独立部署候选。新增通用配置与移动端词条纠错/新建申请，保留原项目版权、许可证、第三方声明、数据边界和固定上游提交归属。此公开仓库仅上传已清理的当前源码快照；未部署生产服务。

源码交付版本见 `VERSION`；从归档安装请先阅读[完整安装、快照恢复与回滚指南](docs/install.md)，执行 `python3 scripts/verify_package.py` 核对包内 `RELEASE.json` 和 `MANIFEST.json`。该入口针对解压后的包，不依赖 Git；开发工作区没有生成的两份元数据时，先打包再验收。

候选4修正：候选3的许可清单遗漏了讯飞示例派生代码和购买素材，不能视作已清理的通用部署成品。当前候选实际移除两份识别实现和三份购买素材；旧普通话识别入口改为文字查词/查音，积分图标为新建中性SVG，证书页为新建学习记录画布。普通话麦克风识别、购买证书外观及其二维码不再随包提供。原项目代码与历史声明保留；详见[本轮许可修复记录](docs/license-cleanup-validation.md)。

## 启动两个不同品牌/方言的独立网站

需要 Docker Engine 和 Compose v2。首次构建需要网络下载基础镜像和锁定依赖。请在本仓库根目录执行；无需修改源码：

```sh
COMPOSE_PARALLEL_LIMIT=1 docker compose -p dictionary-coast config --quiet
COMPOSE_PARALLEL_LIMIT=1 docker compose -p dictionary-coast up --build -d
curl http://localhost:18080/healthz
```

Web：`http://localhost:18080`；移动网页：`http://localhost:18080/mobile/`。
第二份配置复用同一组镜像，使用独立端口和独立数据库卷：

```sh
SITE_CONFIG=./config/examples/mountain.json HTTP_PORT=18081 \
  docker compose -p dictionary-mountain config --quiet
SITE_CONFIG=./config/examples/mountain.json HTTP_PORT=18081 \
  docker compose -p dictionary-mountain up -d --no-build
curl http://localhost:18081/healthz
```

海岚词典（闽南语）与山城语库（客家话）仅为配置示例，不自带真实方言词典、语音或用户数据。首次空库会创建一个明确标为“技术演示”的自编词条。已有非空词库不插入/覆盖演示词条。设置 `SEED_DEMO=0` 禁用演示种子；导入真实资料前核验授权。

默认仅绑定本机回环端口。停止实例用 `docker compose -p dictionary-coast stop`，保留数据库卷。不要用删除卷命令清理有价值的数据。

如果主机 Docker 自动地址池耗尽，先核验已有 Docker/主机路由，再用 `compose.network.yaml` 与 `DICTIONARY_SUBNET` 指定不重叠的私有网段；不要清理其他项目网络。第一轮运行验证使用了 `compose.prebuilt.yaml`；第二轮已用标准 `deploy/website.Dockerfile` 完成镜像内全新frozen安装/源码构建，并从空白配置和恢复目录启动验证。prebuilt入口仍保留为可选产物运行方式。

## 配置与运行范围

选择或复制 `config/examples/*.json`，通过 `SITE_CONFIG` 指定。配置控制站名、简称、Logo、方言名称/代码、API、Web/H5地址、内容来源及基础功能开关。公开配置会发送到浏览器，不能填入密钥。Compose 在容器启动时从同一个 JSON 生成 Web/H5 运行时配置；切换配置无需改源码或重构镜像。修改挂载内容后重建容器以重生成 JS。

`config/examples/hinghwa.json`单独保留并开启莆仙音系、亲属、地区等原有能力；不导入生产数据。

默认关闭原项目音系教学、拼音合成、亲属称谓、地区、日常用语、测试等方言专属内容；保留其来源说明。开启旧功能不等于完成新方言适配。`phonologyAudioBase` 可选，默认空，只有显式启用拼音且提供自己的音频端点才播放示例。参见 [前端配置说明](frontends-config/README.md)。

后端使用同一份 Django 业务与模型、独立 SQLite 卷、本地媒体存储、单 worker Gunicorn 和轻量关键词搜索。默认不下载模型，不启动语义索引或后台定时任务。完整上游语义检索源码与依赖说明仍在 `backend/`。邮件默认输出至容器日志；微信登录、云存储、真实邮件服务需自行配置，未包含线上凭据。可执行 `docker compose -p dictionary-coast exec backend python manage.py createsuperuser` 建立自己的管理账号。

## 小程序

Compose 发布的是 Web 与 Uni-App H5。微信小程序需提供自己的 AppID、绝对 HTTPS API、平台允许的服务器域名，使用开发工具预览、真机测试、上传及审核。原应用标识已清空。生成构建配置：

```sh
WECHAT_APP_ID=你自己的AppID node frontends-config/generate.mjs /path/to/public-config.json --mini-program
cd uni-app
yarn install --frozen-lockfile
yarn build:mp-weixin
```

静态构建成功不能替代平台注册、真机验证或发布。不要使用两个 H5 示例中的相对 `/api` 直接打包发布小程序。

## 验证与来源

- [真实功能差异矩阵与补齐依据](docs/feature-matrix.md)
- [验证记录与剩余事项](docs/validation.md)
- [兴化语记实例兼容、迁移与回滚边界](docs/migration-and-compatibility.md)
- [技术二共性数字服务底座映射](docs/technical-foundation.md)
- [三仓来源及固定提交](provenance/sources.json)，各组件历史摘要在 `provenance/*-history.txt`；上游完整历史可由固定提交追溯；此发布树不携带本地未经审阅的父历史。

定向测试：`python3 -B scripts/test_site_config.py`、`node frontends-config/test.mjs`、`node uni-app/scripts/test-word-application.mjs`。后端集成测试使用合成数据库，详见验证文档。

## 许可与交付

三个固定基线的授权原创软件均为 AGPL-3.0-only；各组件的 `LICENSE`、`LICENSING.md`、`THIRD_PARTY_NOTICES.md`、`ASSET_BOUNDARIES.md`、`DATA_PROVENANCE.md` 优先规定其各自边界。历史版本和第三方路径继续适用原条款。新整合代码除明确例外外按 AGPL-3.0-only 提供；`integrations/quick-start/` 的上游固定提交没有LICENSE，适配只作本地审阅，其NOTICE不授予上游许可，不得据根AGPL推断完整公开发布授权。不扩大词典、录音、用户内容、商标或购买素材授权。产品去品牌化不抹去 E方言及历史贡献者署名。

开发者在已审阅且干净的 Git 工作区运行 `python3 scripts/package_candidate.py`，创建 `artifacts/dialect-dictionary-kt2-source.tar.gz`、`SHA256SUMS` 与清单。包内保留来源、历史摘要、授权声明和固定依赖锁哈希；不含 `.git`、凭据、运行卷、模型、构建缓存、生产数据库/媒体、旧 API 录制 JSON、未获许可的 quick-start `sql.js`/`test_sql.py` 或依赖该适配的旧恢复验收脚本，以及已排除的讯飞派生实现/三份购买素材。排除路径和原字节哈希见 `provenance/excluded-materials.json`，打包会拒绝被改名后重新混入的相同字节。quick-start 的说明/NOTICE仅记录来源与未交付边界；当前部署和快照工具独立于它。完整本地候选历史不随本次公开快照上传。软件公开不额外授权数据、素材或商标，未来新增资料仍须核验其权利。

这是源码部署包，首次在另一环境构建需下载基础镜像与锁定依赖，不是离线二进制镜像包。`BACKEND_IMAGE`、`WEBSITE_IMAGE` 可指定自有固定标签或本地 image ID；使用 `--no-build --pull never` 复用镜像。`latest` 默认值不能代替版本记录，须保存实际镜像ID/平台。源码归档和快照都用SHA256检测损坏，未宣称数字签名或可跨架构复用本机镜像。

## 第二轮验收

已完成镜像内干净frozen安装与源码构建、28项后端回归、13脚本两编译目标隔离、微信目标静态构建，以及合成数据库/静音MP3/来源许可/站点与策略配置/版本元数据的备份恢复。独立恢复Compose健康、原媒体URL字节、真实角色限制与关闭后旧客户端拒绝写入均通过。见 [第二轮记录](docs/round2-validation.md)。

普通词条贡献写接口默认关闭；只读策略目录挂载由`FEATURE_POLICY_DIRECTORY`与`FEATURE_POLICY_FILE`选择。兴化已允许能力可显式选择`FEATURE_POLICY_FILE=feature-policy.hinghwa.example.json`，须先核验自身发布/内容资格并维护有效期；历史读取保留原权限。详情见[服务端开关](docs/server-feature-policy.md)。它不识别审核身份，不按审核状态隐蔽切换能力；公开capabilities不是授权。

[quick-start实际整合及许可例外](docs/quick-start-integration.md)与[平台差异/官方链接](docs/platform-capabilities.md)单独记录。微信官方原文入口当前读取失败，真机与平台审核未验证。
