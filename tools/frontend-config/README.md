# Web与Uni-App前端配置

两个前端使用同一份公开站点JSON。普通Compose部署只需修改根目录的 `config/site.json`，再按原模式重启实例；无需手工运行本页的生成器，也无需改源码或重新编译。部署入口在应用启动前生成 `window.__DICTIONARY_CONFIG__`：Web读取 `/site-config.js`，H5读取 `/mobile/site-config.js`；H5固定放在 `/mobile/`。浏览器重新加载后使用新的运行时配置。公开配置不能放凭据。

## 普通部署者配置什么

| 配置项 | 作用 |
| --- | --- |
| `name`、`shortName`、`dialect` | 站名、简称、方言名称与代码 |
| `logo` | 自己有权使用的公开标识地址 |
| `webUrl`、`mobileUrl`、`apiBase` | 网页、手机网页和API端点；同源网页可用 `/api` |
| `contentSource` | 内容来源名称、署名链接和授权说明，不是自动导入源 |
| `features` | 展示功能开关；必须显式为布尔值true才开启 |
| `phonologyAudioBase` | 可选音韵教程样例媒体源；默认空，不使用旧站的远端主机 |

`config/examples/coast.json` 与 `mountain.json` 展示不同品牌/方言；兴化语记专属能力通过 `hinghwa.json` 保留。示例配置不含真实词典。相关来源表、教学算法、地理映射和媒体仍须适配自己的方言，打开开关不能自动完成适配或获得许可。

默认关闭 `pinyin`、`kinship`、`geography`、`music`、`quiz`、`dailyExpressions`、`translation` 和 `legacyLinks` 等可选功能。核心词典文本和已授权真实录音保持可用。关闭geography会隐藏上游县区/乡镇选择，不会替换成其他方言的地区表。`pinyin`包括上游音韵教程、查表与合成读音；要加载教程样例还须填写已授权的 `phonologyAudioBase`，文件名遵循保留的上游表键。

## 开发或小程序构建时生成配置

生成器会改写两个前端的public配置、编译备用JSON、小程序名称及导航标题。它不编译、不部署、不上传。先保留自己的源码改动，只在准备构建的工作副本运行：

```sh
node tools/frontend-config/generate.mjs config/examples/coast.json
```

小程序必须使用自己注册的 `WECHAT_APP_ID`，以及已经在平台登记的绝对HTTPS API地址。`UNI_APP_ID`用于自己的Uni-App应用标识；原有标识默认留空。将自己的配置另存为例如 `config/my-mini-program.json`，确认 `apiBase` 后运行：

```sh
WECHAT_APP_ID=你自己的小程序AppID node tools/frontend-config/generate.mjs config/my-mini-program.json --mini-program
cd apps/mobile
yarn install --frozen-lockfile --non-interactive
yarn build:mp-weixin
```

从根目录生成后再进入 `apps/mobile`；旧目录名 `uni-app` 已不适用。生成器只检查必要的配置格式，不代表AppID有效、HTTPS服务可用或平台批准。编译产物仍需微信工具、设备测试和审核；Compose只提供Web/H5。各端能力与合规的服务端开关见[平台边界](../../docs/development/platform-capabilities.md)及[权限策略](../../docs/server-feature-policy.md)，不提供审核识别或隐蔽开放机制。

## 开发者接口与回归

每个前端的 `src/config/site.js` 默认导出 `siteConfig`；`featureEnabled(name)` 只接受显式true。Vue模板使用 `$site` 和 `$featureEnabled`；Web的 `routeEnabled(name)` 与Uni-App的 `pageEnabled(path)` 同时控制导航和直接访问。公开页面开关不替代后端授权。

```sh
node tools/frontend-config/test.mjs
```

这条无依赖测试从仓库根目录运行，执行实际配置/守卫模块，检查两种品牌、关闭的可选功能、开放的核心路径、严格布尔值以及无浏览器全局变量的小程序备用配置。使用自动清理的临时项目，不代表浏览器渲染、微信真机或审核已通过。

安全默认值统一在 `tools/frontend-config/defaults.json`，生成器同步到各前端。运行时配置缺省的开关会变为false，可选音频/反馈为空；不会因为曾编译为兴化语记而继承其专属设置。源码和第三方声明保留原归属，改站名不扩大数据授权。

可选 `feedback` 包含 `webUrl`、`miniProgramAppId`、`productId`。只有 `legacyLinks=true` 且配置齐全时，H5打开配置的网页，微信端打开配置的反馈小程序；生成的 `mp-weixin.embeddedAppIdList` 才包含该反馈AppID。反馈AppID不是你自己的 `WECHAT_APP_ID`。
