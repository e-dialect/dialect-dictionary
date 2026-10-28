# quick-start 既有导入脚本的本地适配

**仅为本地审阅历史。交付源码包不携带本页描述的 `sql.js`/`test_sql.py`，下文命令不是该包的可用安装入口。未获许可的适配没有被根 AGPL 重新授权。当前安装与快照工具见根 README 和 `docs/install.md`。**

实际入口是本目录 `sql.js`，来源与未解决的上游许可见 [NOTICE.md](NOTICE.md)。这是离线 SQL 生成入口，不在 Compose 启动时执行；不连接数据库、不上传音频、不做备份或恢复。只支持当前候选 SQLite 的 `word_word` / `word_pronunciation` 表。

使用自己的授权资料准备 UTF-8（可含 BOM）或含 BOM 的 UTF-16LE/BE TSV；支持 LF/CRLF。表头必须为以下五列、以 TAB 分隔，正文每行同样五列；不支持单元格内 TAB/换行或额外列：

```text
编号	普通话	方言	发音	注释
```

准备只包含 MP3 文件的目录。沿用原脚本文件名前四位编号映射；文件名必须以恰好四位数字开头，例如 `0007示例.mp3`，对应 TSV 的 `7` 或 `0007`。编号不会重排；未知/重复 TSV 编号、歧义文件名及缺少对应词条的音频会拒绝。可以有无录音的词条；脚本不检验 MP3 内容、不转码。

显式创建自己的 `options.json`（不得使用生产凭据；此处仅为合成示例）：

```json
{
  "dialect": "sqlite",
  "contributorId": 17,
  "verifierId": 23,
  "audioBaseUrl": "https://example.invalid/files/",
  "county": "合成县",
  "town": "合成镇"
}
```

贡献者和审核者必须是目标库已有、经核验的用户 ID；脚本不会创建用户，也不会将冲突 ID 自动映射。媒体 URL 应对应自行放置好的真实媒体目录。脚本只生成地址，不复制文件。生成到新的空输出目录：

```sh
node integrations/quick-start/sql.js /path/to/own.tsv /path/to/own-mp3 /path/to/options.json /path/to/new-output
python3 -B integrations/quick-start/test_sql.py
```

输出 `word.sql` 与 `pron.sql`。先完整校验两种输入再生成；已有输出拒绝覆盖。输出采用 SQLite 单引号字面量转义，显式输出 JSON `mandarin`、`tags`、语音时间，并修复原 IPA 映射参数缺失。TSV 的“发音”仅写入 `standard_ipa` / `ipa`；没有独立拼音资料或转换依据，因此 `standard_pinyin` / `pinyin` 留空，不把 IPA 复制成拼音。词条和语音均保持原未公开状态；直接 SQL 不经过 Django 审核、模型清理、信号或语义索引调度，正式流程仍需运营方核验。

导入执行不是此入口的职责。仅在已授权的隔离副本中审阅 SQL、核对用户及 schema/ID 后，由调用方启用 `PRAGMA foreign_keys=ON`，在同一个事务中依次执行两份 SQL，任一错误立即回滚；不得使用忽略错误、`INSERT OR REPLACE` 或重映射策略。先导入词条再导入语音。不能把本地合成测试通过称为生产迁移已完成。

已验证：8 项标准库测试覆盖合成 SQLite 的引号/Unicode 往返、必填列、关联、重复导入冲突、格式/编码/配置拒绝和防覆盖。该测试 schema 对齐当前模型的相关列约束，未声称验证所有 Django 业务或实际生产 schema。旧词汇数据、真实录音、转码、API 导入（上游本身标为暂缺）、MySQL/PostgreSQL、生产备份/迁移/回滚均未整合或执行。
