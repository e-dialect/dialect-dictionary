# 第一轮验证与安全收口（第二轮结果另见round2-validation.md）

日期：2026-10-25。硬截止07:00 UTC / 北京时间15:00；本轮不自动延长。

三仓当前基线由GitHub只读连接器核验，并精确fetch进隔离候选，见 `provenance/sources.json`。完整Git父历史、作者与许可证保留。本轮未推送、创建远端仓库、改主线、操作生产或迁移原站数据。原后端两处用户改动、Web未跟踪`.env`与Uni工作区状态保持不变；未复制私有`.env`。

| 验证 | 最终结果 | 证据 |
| --- | --- | --- |
| 配置schema/两通用实例/兴化能力保留 | 4项Python测试通过 | `scripts/test_site_config.py` |
| 两品牌两端runtime、开关、音频、生成顺序隔离、反馈 | 9组通过 | `frontends-config/test.mjs` |
| 词条申请白名单、关系保留、Unicode/长度、无对象突变 | 通过 | `uni-app/scripts/test-word-application.mjs` |
| 后端真实容器集成 | 7项通过：查词、纠错待审、新建待审、拒绝未登录、本地媒体与路径、录音地区开关、媒体删除 | `HinghwaDict/test_standalone.py`；本地raw log |
| Django迁移一致性 | `makemigrations --check --dry-run`无变化；测试库迁移通过 | 本地raw log |
| Web实际production build | 最终通过 | `evidence/frontend-final.json` |
| Uni-App H5、mp-weixin实际静态build | 最终均通过；微信目标自身AppID为空 | 同上；不等于真机或发布 |
| 两前端锁完整性 | 均通过；Uni按原安装flags使用`--ignore-scripts`检查 | 同上 |
| 后端锁/镜像 | Python3.10的36包哈希锁实际安装，`pip check`通过，镜像构建成功 | `deploy/requirements.dictionary.lock` |
| 两配置Compose真实运行 | 同一组backend/website镜像；海岚/nan和山城/hak均健康、查词返回1个自编演示词、H5=200、旧H5路径转跳正确 | `evidence/compose-runtime.json` |
| 浏览器Web/H5 | 两品牌站名/方言/来源显示正确；Web查词可见演示词；390x844桌面浏览器视口中H5详情→纠错→登录保护通过；通用配置听句子入口关闭；Logo高度40px | 浏览器实际检查，非真实手机 |
| 敏感数据边界 | 原私有配置/生产DB/媒体未复制；交付包排除Git、运行卷、旧HTTP录制JSON、缓存/模型 | `scripts/package_candidate.py`和交付清单 |

环境：macOS iMac；本机Node24.11.0/Yarn1.22.22，Web Vue2.7.16/CLI5.0.9，Uni Vue3.5.27/Vite5.4.21/DCloud3.0.0-4080720251210001。Docker29.8.2、OrbStack10vCPU约16GiB。前端编译串行，Node堆1536MiB；未做压力/并发实验，未下载模型/启动索引worker或后台定时任务。后端镜像Python3.10、Django5.0.3、Gunicorn23.0.0、NumPy1.26.4；锁文件SHA256在 `evidence/validation-summary.json`。

## 本机容量问题及实际运行方式

第一次后端构建因慢速下载达到420秒上限，已结束；缓存重试5分54秒成功。Docker默认网络地址池已耗尽，未清理其他任务网络；只读核验Docker与主机路由后，给两个本任务实例选用互不重叠的私有测试网段（具体值仅留本地）。四个容器均达到healthy后已stop，保留卷和镜像。没有本任务持续AI/构建/索引/调度任务。

为避免重复下载前端依赖，本轮实际运行镜像使用已经本机构建成功的产物：`compose.prebuilt.yaml`。标准 `deploy/website.Dockerfile` 的镜像内全新frozen安装/构建**尚未验证**；不要将产物运行验证说成全新依赖安装验证。

原验证实例的精确网络值不随公开快照提供；新主机按安装指南独立核验私有网段。源代码交付包不含dist；在另一台机器可用根README的标准源码构建入口，或者先按锁安装并串行构建Web/H5，再用prebuilt入口。

## 剩余事项

- 完整语义检索/模型/索引worker部署未验收；轻量模式明确回退关键词检索。完整源代码没有删除，迁移差异详见 `migration-and-compatibility.md`。
- 兴化实例配置保留莆仙工具，但未导入真实数据、跑完整专属能力回放或迁移原站。SMTP、微信、COS及识别服务需由运营者提供自己的私有配置并单独验收。
- 小程序只有静态构建；自身AppID/HTTPS域名注册、开发工具、真实设备权限/录音、上传审核均未完成，Compose不发布小程序。
- 未执行线上迁移/回滚；实际线上版本、数据库/媒体备份恢复及原H5域名深链仍需授权后的隔离演练。
- 搜索整句试听、编辑已有词单等Uni功能缺口尚未补；本轮优先关闭了词条纠错/新建的实际断点。

所有证据按验证层次记录；可重试的首次失败也保存在本地raw logs，不作为最终通过证据。源码包只包含可共享摘要，不包含本机网络清单或原始终端日志。

