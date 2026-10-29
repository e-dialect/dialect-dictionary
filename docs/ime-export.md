# 从词典资料包导出本地输入法词库

输入法本体、方案与操作系统安装仍在独立仓库；本项目只导出你有权使用的附加词库，不安装输入法、不修改系统输入源、不自动上传或同步。

## 已定位的输入法与适配范围

用户提到的名称对应组织内 [e-dialect/hinghwa-ime](https://github.com/e-dialect/hinghwa-ime)，默认分支master。本轮核验固定提交 [`e3b392032dd3dff586948553f944ca628e4cbd33`](https://github.com/e-dialect/hinghwa-ime/tree/e3b392032dd3dff586948553f944ca628e4cbd33)，它是Yaryou/HinghuaFactory的分支，基于Rime，根许可为MPL-2.0。Pouleng方案及词典版本是 `2019.11.22.1`；另有 `HinghuaBUC` 平话字方案，本轮**没有**实现平话字导出。

导出格式叫 `pouleng-rime-v1`：UTF-8、LF、Rime文本词典，正文为“词条<TAB>输入码<TAB>固定权重100”。配套文件通过 `import_tables: [Pouleng]` 加上原有词表，并提供修改 `translator/dictionary` 的补丁示例；不复制上游词库、输入法本体、图片或第三方依赖。原方案与数据的署名/许可仍须保留，不能把软件许可当成录音、词表和参考书数据的授权。导出数据继续适用其原授权，不会自动变成本工具的软件许可证。

目前只导出**已经成功导入并有回执的一个资料包**，每条词都有原编号、来源与许可。尚不支持没有包级来源的散装词条导出；不要伪造包来源补齐它。每次导出一个包，不提供跨包自动合并或双向同步。

## 为什么需要输入码对照表

[资料包](packages/README.md)中的发音列是IPA，后端不会猜拼音。Pouleng输入码与IPA不是同一种编码，也不能把任意其他方言拼音当成该方案。先由熟悉目标方言和方案的人审核对照表，再预览。

把下面两列保存为 **UTF-8 TSV**（可BOM），中间是真正TAB：

```text
external_id	code
0001	ceh6 si4
```

这只是合成技术示例，不表示真实方言读音。将自己的对照表放在例如 `packages/private-ime-codes.tsv`；它是独立文件，**不要塞进原资料包**，原包校验会拒绝未知文件。`external_id` 必须与回执保存的原编号完全一致，`1`和`0001`不能擅自互换。必须完整覆盖该包，缺少、多余、重复编号都拒绝，不静默漏导。

本版接受小写ASCII字母组成的音节，可带1–8调号，多个音节以单个空格分开。IPA字符、上标、括号、额外空格、9调号及其他未声明表示法会拒绝，不自动替换或删调号。工具只检查结构，不证明音韵正确。上游Pouleng在输入时本来忽略调号，候选注释保留调号；本工具在文件中原样保留输入码和数字，不改变其拼写规则。

## 一次预览，一次导出

先按[安装指南](install.md)从包含本功能的源码构建/启动实例。旧镜像不一定有新命令；`--no-build`不会更新它。模式和原站点一致：已有Traefik在 `export-ime` 前加 `--traefik`，独立代理用 `--traefik-standalone`。

这些是服务器运营者的本地管理命令，不是公开HTTP接口。`--requester`指定用于审计与权限范围检查的现有活跃账号，**仅填写用户名不等于用户登录认证**；只应让已有服务器管理权限的人执行命令，不得把它无认证包装成下载接口。

```sh
./dictionary export-ime 你的资料包ID --mapping "packages/private-ime-codes.tsv" --requester 你的用户名 --version 2026.10.29.1 --preview
```

默认只允许包、词条、语音全部公开，任何一条撤回都会拒绝整包导出。预览不改数据库、不创建导出文件；会显示当前词条、代码、原始IPA/拼音和来源，预览输出也可能含敏感内容，不要公开贴日志。

确认文字、输入码和预期的本地使用均获许可后导出：

```sh
./dictionary export-ime 你的资料包ID --mapping "packages/private-ime-codes.tsv" --requester 你的用户名 --version 2026.10.29.1 --output my-package-2026.10.29.1.zip --authorization-statement "填写实际授权范围与本次用途，不填密钥"
python3 tools/verify_ime_export.py exports/my-package-2026.10.29.1.zip
```

`--version`必须显式填写；同名输出拒绝覆盖，更新请使用新的版本与文件名。授权声明由操作者负责核验，工具不替你获得许可。输出仅在安装根目录的 `exports/`，新目录/文件默认私有，已从Git、Docker构建上下文与源码交付打包中排除；不会放进公开媒体目录。文件哈希用于发现变化，不是发布者签名。不要把导出ZIP提交公共仓库或放入网站静态目录。

**确需本地使用私有资料**时，在预览和导出两条命令中都显式加 `--include-private`；仅原包导入者或超级管理员可通过。账号停用、未指定该参数、非所有者或有撤回条目的默认导出都会拒绝。这个选项不把资料变成公开，也不授予再分发许可。

包内内容：

| 文件 | 作用 |
| --- | --- |
| `dictionary_local_*.dict.yaml` | 附加词库，含原Pouleng码表引用及本次词条；权重100为固定默认值，非词频统计 |
| `Pouleng.custom.example.yaml` | 手动合并用的配置示例，不会自动覆盖已有配置 |
| `source.json` | 原包ID/哈希/元数据、输入码表哈希、导出版本、操作者、公开/私有选择及每条原IPA/拼音；不含账号凭据、录音URL或内部存储路径 |
| `MANIFEST.json` | 每个文件的大小和SHA256 |
| `INSTALL.txt` | 简短安装提醒 |

词库不包含录音、释义和完整账号资料，不是词典备份。原IPA/拼音保存在source.json作核对，不会被当作输入码或静默转换；原库及原资料包不变。词条若包含TAB、换行、控制字符、注释前缀等无法安全表达的内容，整次拒绝而不是改写。完全相同的词/码重复也拒绝，避免无提示合并。

## 在自己的设备安装

1. 从[Rime官方入口](https://rime.im/download/)选择适合系统的实现（Windows小狼毫、macOS鼠须管，Android可按官方链接查同文等第三方实现）。本项目不安装应用，也不变更输入源、安全权限或注册服务。
2. 按[固定上游说明](https://github.com/e-dialect/hinghwa-ime/blob/e3b392032dd3dff586948553f944ca628e4cbd33/README.md)安装Pouleng方案及依赖，保留其许可/署名。先确认原方案能用；不要用本ZIP替代输入法本体。上游Android路径是历史说明，当前应用版本目录应从其设置查看，不盲目使用旧路径。
3. 打开Rime用户文件夹，备份现有内容。官方列出小狼毫默认 `%APPDATA%\Rime`、鼠须管 `~/Library/Rime`，也可从输入法菜单打开；不同前端目录以[Rime用户资料说明](https://github.com/rime/home/wiki/UserData)及实际配置为准，不写入程序安装目录或build缓存。
4. 校验ZIP后，在临时目录解压。只把生成的 `dictionary_local_*.dict.yaml` 放入用户目录。如果没有 `Pouleng.custom.yaml`，可把示例另存为此名；已有文件时只合并 `patch` 中的 `translator/dictionary`，保留其他自定义项，不能多写一个重复patch。若已引用其他附加词库，先人工核对合并方案，不覆盖原引用。一次只激活一个本工具词库；多包合并未实现。
5. 在输入法中执行“重新部署”，选择Pouleng，输入对照表中的码，逐项检查候选字、调号提示和原词库仍可用。编译出错时看输入法日志，先恢复备份的custom配置并重新部署，不删除整个用户目录或用户学习词库。

升级/撤回导出文件不会撤回已复制到别人设备的数据。私有词库可能进入输入法用户词典或云同步目录；只在许可范围内使用，关闭或自行核对对应同步，不把它推送公共同步仓库。恢复旧版本时使用备份配置及配套词库重新部署，保留用户学习数据。

## 真实验证与未验证

本轮以原创合成词条、静音包及人工合成输入码测试：默认私有拒绝、所有者/超级管理员显式私有选择、撤回/停用拒绝、无写入预览、错误输入码/编码/编号拒绝、原IPA和调号保真、确定性ZIP、原子写出、拒绝覆盖和损坏/路径穿越校验。没有安装Rime，没有运行引擎编译、真实键盘输入、操作系统输入源或微信真机验收；不要把文件测试称为设备可用性保证。

格式依据：[Rime输入方案设计书](https://github.com/rime/home/wiki/RimeWithSchemata)的UTF-8/TSV词典与字典绑定，以及[librime维护者对import_tables的说明](https://github.com/rime/librime/issues/379)。只为已核验固定版本提供Pouleng附加词库；未来上游或其他方言方案变化需要另行适配，不承诺通用输入法自动生成。

官方[DictSettings::GetTables实现](https://github.com/rime/librime/blob/master/src/rime/dict/dict_settings.cc)亦核对了自身码表与导入码表的组合语义（2026-10-29）。这属于源码/格式核验，不代替引擎实际编译。
