# 2026-11-25 普通读者体验验收

本目录记录本地 Chrome 中使用纯合成 fixture 的产品验收截图。未访问真实词典资料，未修改生产数据，未执行生产部署；手机截图来自 320/390 像素浏览器视口，不能替代真机或微信设备验收。

| 范围 | Issue | PR | 证据目录 |
| --- | --- | --- | --- |
| 桌面搜索、结果状态与浏览进度 | [#34](https://github.com/e-dialect/dialect-dictionary/issues/34) | [#37](https://github.com/e-dialect/dialect-dictionary/pull/37) | [web/](web/) |
| 手机词单浏览与错误恢复 | [#35](https://github.com/e-dialect/dialect-dictionary/issues/35) | [#39](https://github.com/e-dialect/dialect-dictionary/pull/39) | [mobile/](mobile/) |
| 词条试听与播放反馈 | [#36](https://github.com/e-dialect/dialect-dictionary/issues/36) | [#38](https://github.com/e-dialect/dialect-dictionary/pull/38) | [audio/](audio/) |

手机词单截图覆盖列表、完整释义、长标题换行、加载、空列表、空词单、失败重试及不存在的词单。浏览器操作验证了列表 → 词单 → 词条 → 返回，以及列表/详情失败后重新加载和失效链接返回列表。原生下拉刷新收尾由组件回归验证，未做真机手势验收。

桌面截图记录搜索空态、第二页结果和音频播放状态。Chrome 验证词语/文章独立 URL 页码、词条后退、刷新、新关键词归第一页、空态修改关键词聚焦、503 后重试、非法及越界页码、200 条上限说明，1440px 无横向溢出。

音频验收使用可解码的 12 秒 PCM 静音 WAV，保留浏览器真实媒体实现，观察 playing/paused 状态，不代表真实方言录音听感或音质验收。Web 验证键盘 Enter 播放、重复停止、A→B 互斥、媒体失败重试、进入详情清理。H5 验证播放/结束/停止/重试、返回首页停止、搜索列表多按钮互斥、按钮点击不误入词条、词条往返后仍能播放，390px 无横向溢出。

审查修复了两个音频竞态：并发合成的最后一次点击优先，以及 UniApp onUnload 未触发 onHide 时的离页清理。最终音频提交由另一独立 subagent 确认；手机词单也经交叉审查。

验证提交：搜索 `8f4f74e`，词单 `7430c9d`，音频 `f30e146`。整合树 `a40e7f4` 包含全部代码，音频 13 项行为回归、搜索 Vue watcher 回归、词单状态回归通过；各端定向 lint 与 Web/H5/微信小程序 production 构建通过，组合状态 H5/微信构建再次通过。构建保留既有体积、Browserslist、Sass 与 uni-ui 提示。

仓库没有配置 GitHub Actions；远端提交状态与 check runs 为空，不将本地验证称为 CI 通过。GitHub Copilot 自动审查因配额未执行，独立代码审查由上述 Codex agents 完成。未做真机、真实资料、真实发音质量或生产部署验收。

早期 H5 验收与并发构建共用产物，重建清理了旧页面所需 chunk，导致一次导航超时；已在构建稳定后重新加载并完成相同流程。截图仅记录最终成功状态。
