# 前端功能差异审计

审计日期：2026-10-25。仅比较下述固定提交的静态源码，不包含未合并的 kinship 分支功能，也不保证线上服务、设备权限或第三方服务可用。

- Web master：`8be2e372db5df31e80cd9320ddb72754f40f766d`
- Uni-App master：`468aa59091af33f95a2a5112039fca0427f7fb09`
- 后端 develop（申请接口契约由主线核验）：`b08f367ede7d7e2eca90b2e02828b76b784ba2f0`

26 个关键文件通过 GitHub 连接器按固定 SHA 重读。路由入口以 Web `src/router/index.js`、Uni-App `src/pages.json` 为准。下表路径 W/U 分别相对 Web/Uni-App 仓库；“有”表示存在对应实现，不表示全部交互一致。尚未进行设备、真实账号或真实 API 写入验证。

| 功能 | Web | Uni-App 基线 | 静态证据 |
| --- | --- | --- | --- |
| 词语、字音、文章搜索 | 有 | 有 | W src/views/SearchResult.vue；U src/pages/search.vue，含三范围与历史 |
| 词条详情、释义、相关词文、发音 | 有 | 有 | U src/pages/words/details.vue；src/components/WordPronunciationButton.vue 支持真人音频、拼音/IPA 合成 |
| 词条创建、纠错申请 | 有 | 缺失 | W src/views/Words/WordEdit.vue:146 POST /words/applications；U words/details.vue:218–222 引导网页端修改 |
| 搜索整句试听 | 有 | 缺少搜索入口 | W SearchResult.vue:128；U services/pronunciation.js:54 已有 combinePronunciationByChinese |
| 逐词录音上传、语音列表、排行榜 | 有 | 有 | U pages/words/pronunciations/upload.vue、pronunciations.vue、ranking 路由 |
| 批量快速录音队列 | 有 | 缺失 | W views/Tools/QuickRecording.vue，GET /record 分页、预填县乡；U 仅逐词上传 |
| 拼音教学、条件查词、音序词典 | 有 | 有 | U pages/tools/pinyin.vue、condition.vue、dictionary 路由 |
| 亲戚计算、日常用语 | 有 | 有对应入口 | 两端均注册相应页面，不应列为迁移遗漏 |
| 词单浏览、创建 | 有 | 有 | U pages/lists/index.vue、upload.vue、details.vue |
| 编辑已有词单 | 有 | 缺失 | W WordListEditor.vue:55 PUT /lists/:id；U services/lists.js 仅 GET/POST |
| 文章发布、编辑、预览 | 有 | 有 | U pages/articles/edit.vue 调 createArticle/updateArticle，发布和更新需审核 |
| 积分商城、积分历史 | 有 | 有 | U pages/products/index.vue、history.vue；services/point.js |
| 用户设置、消息邮件 | 有 | 有对应入口 | U 用户设置及 pages/mails/index、details、send 路由 |
| 答题、组卷、答题记录 | 有 | 有 | U pages/quizzes/*，不可笼统判定答题缺失 |
| 题目创建 | 有 | 缺少入口 | W views/Quiz/QuizEdit.vue POST /quizzes；U 添加题目按钮被注释 |
| 方言曲库 | 有 | 缺失 | W views/Music/MusicList.vue:68 GET /music、changeMusic；U 无对应页面 |
| 录音与词条申请审核 | 有 | 缺少管理页面 | W components/Admin/Record.vue；views/Words/Application.vue；Tools/WordConfirming.vue |
| 证书展示、二维码 | 有 | 缺少对应页面 | W views/Users/Certificate.vue:99 GET /certs/:id |
| 普通话/方言录音识别 | 有代码 | 缺少入口 | W views/Translation/*；方言识别 POST /pronunciation/translate，服务未验证 |

## 优先顺序

1. 词条纠错申请：移动端现有文案明确要求去网页修改；复用已有申请审核流程。先闭合纠错，再支持 word=0 的新词申请。
2. 搜索整句试听：已有 Uni-App service，可补交互；需保留失败提示和合成参考说明。
3. 编辑自己的词单：补 PUT /lists/:id，闭合创建后的维护流程。
4. 快速录音队列：方便贡献者批量采集；需沿用现有上传、登录与地区配置。
5. 方言曲库：普通用户有价值，需处理跨端播放器生命周期。
6. 审核、题目创建、证书：按管理员实际需求安排。
7. 录音识别：先验证旧接口。旧 xtpTranslation.vue 在 stop 后立即使用 recordSource，而赋值发生于异步 onstop，存在录音时序风险。

## 本次候选实现

本地隔离候选新增 Uni-App 词条纠错/新词申请页面 `src/pages/words/edit.vue`，详情页增加本地贡献入口，新增 `createWordApplication` service 和独立 payload helper。

- 使用 POST /words/applications，body 为 {word, content, reason}，word=0 代表新建。
- content 只允许 word、standard_pinyin、standard_ipa、definition、annotation、mandarin、tags、related_words、related_articles。
- 保留详情中的原有关联 ID，排除 visibility、verifier、contributor、views 与 definitions 等字段。
- 对申请模型限制校验：名称 60 字、拼音/IPA 各 30 字、说明 200 字；普通话词与标签为数组。
- 登录前校验，加载失败禁提交，提交期间锁定，成功后说明“等待审核”并阻止重复提交。
- `apps/mobile/scripts/test-word-application.mjs` 覆盖白名单、关联保留、无源对象突变、新建、编号、必填及长度边界。
- 配置代理负责 pages.json 的 pages/words/edit 路由。本文件不声明完整构建或设备验证通过；最终验证见主线交付记录。

## 候选4许可修复后的能力差异（2026-10-28）

普通话麦克风识别不再随通用包提供：原Web讯飞demo派生实现未建立再分发许可，已从候选当前树移除。原`ptxTranslation`路由改为独立文字查词/可选拼音合成，没有以隐藏按钮保留原识别实现。它不再作为“Web有、Uni遗漏但通用包现成可补”的可用能力。

购买积分图标由原创建模几何SVG替代；证书API/旧路由与下载/打印学习记录保留，但购买底图、印章式外观及二维码移除，不宣称整站原视觉/认证效果完整保留。后端记录、原项目源码与历史授权边界均保留。详见`docs/license-cleanup-validation.md`与`docs/attribution/sources/excluded-materials.json`。
