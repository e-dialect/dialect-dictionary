# quick-start 实际整合核对

**交付边界（2026-10-28）：下文是本地历史适配记录。源码交付包排除 `integrations/quick-start/sql.js`、`test_sql.py` 和依赖它的旧恢复验收脚本；不存在已许可的公开导入器交付承诺。仅保留说明与NOTICE。安装与当前快照恢复不依赖此适配。**

核对日期：2026-10-25。候选核对基点 `a08071947cc1c63db7f4d8ff34c7e37d3644f89d`；本轮其他协作者的未提交修改不算入此基点。只读 GitHub connector 核实目标为 [e-dialect/quick-start](https://github.com/e-dialect/quick-start)，默认 `main` 提交为 [`1391fc01e08fa194f68082bcd6e0762b7988d9e3`](https://github.com/e-dialect/quick-start/commit/1391fc01e08fa194f68082bcd6e0762b7988d9e3)（2024-03-26，init）。没有猜测其他地址或修改原仓库/远端。

## 真实上游范围

GitHub 递归树 SHA `e87a70f5cb21932686b1921815c43ba0d6c415e4` 完整返回，只有根 `readme.md`、`data-import/readme.md`、`data-import/sql.js` 和 `data-import/词汇.tsv`。文件名为小写 `readme.md`，不是 `README.md`。没有 Compose、后端/前端源码、备份恢复工具、API 导入脚本、AGENTS 或 skills 文件。该路径本机未发现 quick-start 检出；核对了 本地上游工作区 目录线索，未写入其中任何文件。候选根及祖先适用路径未找到 AGENTS，候选未找到 `.agents`/SKILL.md 指令文件。

根指南只提出后端部署、前端部署、数据导入三步，并说明当时仍需修改莆仙服务源码的地区配置。数据指南介绍五列 TSV、FLV→MP3、媒体 URL 及 `word.sql`/`pron.sql` 导入；接口导入明确“暂缺”。不能据此宣称存在完整的一键部署框架或已有可复用备份 CLI。

## 已整合与尚未整合

| 范围 | 核对基点状态 | 本轮完成后的实际状态 |
| --- | --- | --- |
| 可配置 Web/H5 + 旧 Django 服务部署 | 候选已有 `compose.yaml`、运行配置生成、独立 SQLite/本地媒体卷；不是复制 quick-start 中不存在的部署文件 | 继续复用已有 `ops/docker/` 与 Compose；此子任务没有改部署代码或运行部署 |
| quick-start 语保 TSV 导入逻辑 | 候选没有 quick-start 代码或明确整合入口 | 本地审阅适配 `integrations/quick-start/sql.js` 沿用原双生成函数；该代码不在交付包中 |
| 上游来源及权利 | 既有三仓来源清单不包含 quick-start | 新目录 [NOTICE.md](../integrations/quick-start/NOTICE.md) 固定 SHA/原文件 blob 与说明链接；无上游 LICENSE，不能宣称 AGPL；未授权公开再分发 |
| 上游词汇/音频 | 未整合 | 仍未复制、未读取词汇 TSV 内容、未运行真实数据；测试全部合成 |
| 备份/恢复、数据库自动执行 | quick-start 没有提供 | 本入口仅生成 SQL；没有新增同类通用工具，也未连接真实数据库 |
| API 导入、音频转换、小程序发布、线上迁移 | 不属于 quick-start 已完成能力 | 仍未完成；不把 SQL 生成或 Compose 运行等同于生产迁移 |

## 旧脚本已核验问题及最小修复

原固定提交的 `data-import/sql.js`：第 13 行只传目录给第 41 行带 `ipa` 参数的函数，参数遮蔽第 7 行全局对象，第 47 行访问会失败；原脚本因此不能完成语音 SQL。第 18 行只按 CRLF 拆行并使用默认 UTF-8，而文档允许 Excel Unicode 输出，不能可靠处理 UTF-16。第 35/57 行直接拼接未转义字段；引号或注释可破坏 SQL。第 28 行生成的 `[普通话]` 不是 JSON 数组。硬编码媒体/用户/地区配置所在路径为 `data-import/sql.js`，不在本文输出其值。

与候选 `apps/backend/hinghwa-dict-backend/word/models.py` 对照：当前 `Word.tags` 是必填列、Django 层默认 `[]`，旧直接 INSERT 不提供该列会失败；语音上传时间及 FK 也需要核对。原固定词条编号和用户编号不能无声覆盖已有记录。

本轮只在原双函数流程上补齐参数、严格解码/五列验证、SQLite 单引号转义、JSON 与必填列、显式身份/地区/媒体配置、四位文件编号映射核验及重复输出拒绝。发音列仅写入 IPA 字段；缺少独立拼音资料，两个拼音字段留空，不沿用旧脚本将 IPA 当拼音的做法。使用普通 INSERT，不做 REPLACE、忽略错误或 ID 重排。执行时的用户存在性/旧 ID 冲突由启用 FK 的 SQLite 事务检查；生成器不对数据库作猜测。受支持入口和事务要求见 [README](../integrations/quick-start/README.md)。

## 本轮证据与边界

`python3 -B integrations/quick-start/test_sql.py`：8 项通过（合成 SQLite 内存库；包含 UTF-8 BOM、UTF-16LE/BE BOM、LF/CRLF、中文/单双引号/反斜线、关联、缺用户拒绝、重复 ID 冲突、孤儿/歧义文件拒绝、配置/编码/格式拒绝、防覆盖）。测试没有读取上游词汇或真实音频，没有连接生产数据库。它证明脚本兼容合成相关表约束，不能证明真实生产 schema、业务信号/审核或媒体可播放性。

未编译前端、未启动部署、未 push、未改原仓库或远端。本次模型/推理/Standard 偏好来自任务参数，并非运行时服务 tier 证据；没有可用的 tier 核验接口，不能证明实际使用何种计费通道或额度状态。
