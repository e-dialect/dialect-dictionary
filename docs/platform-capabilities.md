# H5 / 微信小程序能力边界

本轮基线为候选 `a080719`，原三仓未修改。项目 DCloud 核心/CLI 固定为 `3.0.0-4080720251210001`，Vue 范围 `^3.4.21`，Vite `5.4.21`；这是依赖版本核对，不代表最新版本。实际已安装 DCloud 核心/CLI 均为该固定版本，Vue 为 `3.5.27`，Vite 为 `5.4.21`。本轮未升级。agent 请求配置沿用 gpt-6.1-sol/high；运行时 service tier 无核验接口，不声称已验证档位。

## 官方证据

DCloud [条件编译说明](https://uniapp.dcloud.net.cn/tutorial/platform.html)定义 H5/WEB、MP-WEIXIN 编译目标与 JS/模板注释语法；运行时 if 不会从其他平台产物移除浏览器实现。[跨端差异说明](https://uniapp.dcloud.net.cn/matter.html)明确小程序没有 window/document 等浏览器对象。本项目保留当前版本支持的 H5 写法。

2026-10-25，下列微信原始文档准确 URL 经工具直连均返回 non-retryable fetch error，限定官方域名检索无结果。因此没有以第三方博客代替原规范，也没有声称已逐字核验微信当前审核/运营规则。发布者仍需核对原文与自身账号条件：

- [微信登录](https://developers.weixin.qq.com/miniprogram/dev/api/open-api/login/wx.login.html)
- [录音管理器](https://developers.weixin.qq.com/miniprogram/dev/api/media/recorder/wx.getRecorderManager.html)
- [分享回调](https://developers.weixin.qq.com/miniprogram/dev/reference/api/Page.html#onShareAppMessage-Object-object)
- [网络与服务器域名](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)

## 能力矩阵

技术兼容性与发布/内容使用许可分别核验；不能从某一个 API 限制推出所有微信能力都应关闭。

| 能力 | H5 | MP-WEIXIN | 已核验边界及待验条件 |
| --- | --- | --- | --- |
| 浏览器标题、UA、URL 与跨端跳转 | 保留 | 编译移除 | App、mob2pc/pc2mob、组件使用 H5 条件编译；胶囊尺寸仅微信分支 |
| 普通账号登录 | 保留 | 保留 | 自身业务 API，不依赖微信身份 |
| 微信 code 登录/注册/绑定 | 普通登录或明确不可用 | MP-WEIXIN 且 wechat 开关启用 | provider=weixin，服务端独立验凭据；不把其他小程序 code 发给微信接口。[DCloud 登录](https://uniapp.dcloud.net.cn/api/plugins/login.html) |
| 主动分享 | 不模拟微信分享 | 保留原生 hook | 朋友圈 hook 仅微信；不再使用 success/fail 宣称已送达。[DCloud 分享](https://uniapp.dcloud.net.cn/api/plugins/share.html) |
| 真人录音播放 | 保留 | 保留 | InnerAudioContext 两端受支持；格式、静音与域名需真机验证。[音频兼容表](https://uniapp.dcloud.net.cn/api/media/audio-context.html) |
| 贡献录音 | MediaRecorder 能力检测后使用 | 原生 recorderManager | H5 不调用不支持的 uni 录音管理器；微信授权拒绝保留失败处理，不虚构成功。[录音兼容表](https://uniapp.dcloud.net.cn/api/media/record-manager.html) |
| 查询/词典/文章/拼音/亲属/音乐 | 按实例保留 | 按实例保留 | 不按平台一刀切；莆仙实例保留其音系和地域，其他实例需自身数据与授权；缺开关关闭 |
| 请求/上传/远端音频 | 自身 API/跨域配置 | 真实 HTTPS 接口及对应域名 | /api 仅 H5；开发工具宽松设置不是生产验证。[DCloud 请求说明](https://uniapp.dcloud.net.cn/api/request/request.html)，微信原文访问状态见上 |
| 外部反馈 | 显式配置网页 | 显式配置反馈小程序 | legacyLinks+完整配置；反馈 AppID 不替代本站 AppID |

旧迁移 Polyfill 在 API 缺失时会虚构部分成功回调。本轮停止加载该入口，保留文件与版权，继续使用 uni 原生 API 和原有 Vue mixin。富文本屏幕信息改为 uni.getSystemInfo。没有审核识别、审核后启用或隐蔽切换内容的实现。

## 验证

`cd uni-app && node tests/platform-isolation.cjs` 使用已安装版本的 DCloud 预处理器产生 H5/MP-WEIXIN 脚本并解析；验证目标微信输出无浏览器全局、无 window/document VM 中启动成功、登录分支正确、分享不宣称送达。此测试不运行完整构建或网络请求。

主线负责串行完整 H5/MP-WEIXIN 构建。真实 code 交换、授权拒绝、录音上传/回放、分享、反馈跳转、域名、客户端与基础库版本尚待真机验证。微信原文访问受阻，不能据本轮技术检查宣称已通过审核或满足全部发布要求。

## 词条申请的服务端状态

Uni 表单每次进入与每次提交前重新 GET `/capabilities`，不持久化开启状态。只接受 version=1、enabled 严格为 true、15秒内有效时间窗；网络失败、过期、字段无效均关闭。全局 enabled 是界面提示，不是用户授权，服务端仍独立校验身份、角色和功能策略。设备时间偏差可能保守关闭；不延长服务端有效时间。关闭后保留当前草稿，禁止本次 POST。`cd uni-app && node tests/capabilities.cjs` 验证过期/畸形/离线、无开启缓存、每次提交复查与草稿保留。

主线补查：2026-10-25官方产品/运营规则入口 https://developers.weixin.qq.com/miniprogram/product/ 同样返回non-retryable fetch error；官方域名精确标题检索无结果。该阻塞不被DCloud说明或代码测试替代。主线本轮镜像内H5源码构建、微信目标静态构建及28项后端测试已通过；仍没有真实设备或平台审核结论。
