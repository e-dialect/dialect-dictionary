# 第二轮有界验收

从干净 a080719 开始；用户授权15点后继续，无新截止。保持本地候选，不改原三仓，无push、生产迁移或账号/OS权限操作。

## 实际结果

- `docker compose build --no-cache website`：684.9秒通过。两个构建阶段先断言node_modules不存在，再frozen安装，主机依赖排除在上下文外；Web→Uni依次编译，Node堆1536MiB。最终源码再基于该干净依赖层构建通过。
- 后端真实容器28项测试通过，涵盖策略schema/时限/错误关闭、角色与原审核权限、历史读取、合成业务与媒体。微信静态目标构建通过；DCloud真实预处理器校验13个脚本×H5/MP，客户端能力失败关闭回归通过。
- quick-start沿固定上游脚本改造，8项合成测试通过；另在真实Django迁移schema中导入自编TSV与ffmpeg生成的静音MP3，FK和未公开状态通过。仅IPA入IPA，未伪造拼音。原词汇.tsv未复制或执行。
- 新空白Compose后端生成合成源；停止后用SQLite backup API、媒体与配置的校验清单打包，恢复至全新目录。用户/词条/语音计数1/2/1一致，SQLite integrity/FK检查、全部文件哈希、来源CC0标注、站点/策略与版本元数据一致。
- 独立恢复Compose使用标准源码镜像（未使用prebuilt override），健康、H5、原媒体URL与原字节一致。staff-only拒绝普通合成账号；开放authenticated仍拒绝未登录；合法合成账号可提交待审申请；关闭后同一旧token再次写入被拒。没有创建管理员权限或审核识别机制。
- 策略用只读目录挂载，原子替换可见。首次立即断言在挂载传播期间保守收到关闭，未生成申请；回读确认后，以容器可见文件hash同步再测，最终角色/撤销全部通过。不宣称跨主机零延迟一致性。
- 验收后源/恢复实例均stop，保留合成目录与备份；没有模型、worker、压力测试或新调度。

机器日志保留evidence内但不入共享摘要。结构化结果见 `docs/development/evidence/round2-summary.json`。`tools/verify_synthetic_restore.py`仅为验收夹具：要求runtime目录、拒绝覆盖既有恢复目录，不是生产备份/ETL工具；媒体为自生成静音，没有真实人声。恢复后的HTTP写入阶段另新增一条合成待审申请，原备份包保持不变。

## 配置与边界

默认 `config/feature-policy.example.json`关闭词条贡献写入。显式兴化示例在`feature-policy.hinghwa.example.json`，需选择策略文件并核验合法发布条件；30天以内有效期到期即关闭，不自动延长。它只覆盖wordApplications写操作，其他旧展示开关不被宣称为安全权限系统。

备份包括合成SQLite、MP3、公共站点配置、私有只读功能策略、内容来源/许可与版本元数据；本轮不迁移生产密钥、登录会话、SMTP/COS凭据、真实数据或模型。公开端点保持原值，源实例停止后由恢复实例接管相同本机端口，仅用于验收。

## 尚未核验

微信官方原规范入口/API文档读取失败，DCloud原文可读；不能据代码成功声称当前微信审核条款已完整核验。真实AppID/HTTPS域名、微信开发工具、真机授权/音频/分享及正式审核仍待做。quick-start没有上游LICENSE，NOTICE保留许可例外；未授权公开发布。

