# 来源与发布边界

`sql.js` 是对 E方言既有 `e-dialect/quick-start/data-import/sql.js` 的本地审阅适配，继续使用其 TSV → 词条 SQL → 语音 SQL 的流程和两个生成函数；不是独立另建一套导入系统。

- 仓库：https://github.com/e-dialect/quick-start
- 核验日期：2026-10-25；默认分支：`main`
- 固定提交：`1391fc01e08fa194f68082bcd6e0762b7988d9e3`
- 原脚本：[data-import/sql.js](https://github.com/e-dialect/quick-start/blob/1391fc01e08fa194f68082bcd6e0762b7988d9e3/data-import/sql.js)，blob `1c2f7de1efd613dcf4025d579875fcbc8096de4b`
- 原说明：[data-import/readme.md](https://github.com/e-dialect/quick-start/blob/1391fc01e08fa194f68082bcd6e0762b7988d9e3/data-import/readme.md)，blob `7ec46a1b1a2381567d63e136d2e7802d26715711`
- 原服务指南：[readme.md](https://github.com/e-dialect/quick-start/blob/1391fc01e08fa194f68082bcd6e0762b7988d9e3/readme.md)，blob `f97ce64e82639d7151e3093be07c3cf7a4a298e3`

GitHub 只读接口返回该提交的完整递归树（`truncated=false`），其中没有 LICENSE 文件。因此本目录不主张上游脚本已经获得 AGPL 或其他开源许可证授权；候选根目录的 AGPL 声明不能补足此处权利。此适配仅用于本地审阅，公开发布或再分发前需要单独确认上游授权并保留其权利。上游贡献者与 E方言的来源署名保留；本说明不转让任何数据、录音或商标权利。

未复制或运行上游 `data-import/词汇.tsv`，未复制其硬编码媒体配置值；不包含生产数据库、录音或账号配置。测试中的文字、ID、文件字节和 `.invalid` 域名均为合成资料。
