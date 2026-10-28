# 服务端合法功能策略

本策略管理普通合法功能的部署状态与账号角色范围，不识别审核人员、不按客户端平台或审核阶段改变行为，也不构成小程序/网站所需的内容、隐私或平台许可。没有相应许可时，应保持关闭并按平台要求完成许可。

## 范围与默认行为

当前仅支持 `wordApplications`（词条贡献）。默认独立实例关闭：策略文件缺失、无效、版本过旧、未生效、过期、未知/重复键、角色不合法或无法读取，全部拒绝贡献写入。拼音、词典浏览、录音上传等其他能力不由此策略整体禁用。

| 接口方法 | 策略校验 | 原有权限 |
| --- | --- | --- |
| POST /words/applications | 每请求重新读取并检查开关、真实账号角色 | 必须具有有效 token；申请仍进入待审核，不直接发布 |
| PUT /words/applications/:id | 同上 | 仍必须是原接口要求的 superuser，authenticated/staff 白名单不会赋予审核权 |
| 上述两个资源未来的 PATCH/DELETE 或其他非读取方法 | 先检查策略，再由现有 View 返回 405；未来新增方法默认覆盖 | 不创建新权限 |
| GET /words/applications | 不受贡献开关影响 | 原管理员查看权限 |
| GET /words/applications/:id、HEAD | 不受贡献开关影响 | 原申请人/管理员查看权限 |
| OPTIONS | 不受贡献开关影响 | 仅方法元信息；不读写申请数据 |
| GET /capabilities | 公开，只读，无缓存 | 只返回全局状态，绝不是账号授权结果 |
| 非 GET /capabilities | 405 | 无写入接口 |

这是一道附加门禁，不替代原权限。用户角色来自已校验 token 对应的服务端 User，且账号须 active；客户端 header/body 中的 role、platform、review 身份不参与判断。Django Admin 已有管理功能及其他词条 API 不属于这个贡献申请接口策略范围，仍受各自原权限约束。

## 只读策略文件

环境变量 `FEATURE_POLICY_PATH`，默认 `/config/feature-policy.json`。部署端将文件只读挂载；应用仅读取，既不提供修改接口，也不写回配置。每次贡献写入重新打开文件，没有保留上次开启状态的授权缓存。

复制 `config/feature-policy.example.json` 到部署使用的策略路径。精确结构：

```json
{
  "version": 1,
  "issuedAt": "2026-10-25T00:00:00Z",
  "expiresAt": "2026-11-24T00:00:00Z",
  "features": {
    "wordApplications": {
      "enabled": false,
      "roles": []
    }
  }
}
```

- 仅版本 1，所有键严格匹配，未知/重复键拒绝。
- 时间必须为带 Z 的 UTC 时间，issuedAt <= 当前服务端时间 < expiresAt；最长有效期 30 天。示例日期会过期，启用前须设置当前有效日期。
- enabled 必须是 JSON 布尔值。roles 必须是无重复的数组，成员仅允许 authenticated、staff、superuser。
- authenticated：任意已认证且 active 的账号；staff：User.is_staff；superuser：User.is_superuser。采用匹配任一角色的规则。空角色数组即没有获准账号。
- 文件最多读取 16 KiB。更新时用原子替换，读取中断或损坏只会关闭贡献。
- 不在该文件存放 token、用户 ID、生产账号、平台凭证或许可材料。

兴化实例若已有合法贡献业务，可以显式设置 `enabled: true`、`roles: ["authenticated"]` 并更新有效日期；需要仅管理员试运行时可用 `["superuser"]`。这不会提高账号原权限：普通贡献者依然不能审核。独立新实例示例保持关闭，不自动套用兴化授权或业务资格。

策略失效后，已有历史申请仍可按原权限读取，写入和审核写入停止。恢复需由部署操作者在自己的授权范围内更新只读配置来源；没有“失效时自动恢复开启”的回退。

## 客户端契约

`GET /capabilities` 返回 `Cache-Control: no-store, max-age=0` 及 `Pragma: no-cache`：

```json
{
  "version": 1,
  "generatedAt": "2026-10-25T07:15:00Z",
  "expiresAt": "2026-10-25T07:15:15Z",
  "ttlSeconds": 15,
  "features": { "wordApplications": { "enabled": false } }
}
```

有效期上限 15 秒，且不会超过策略本身到期时间。enabled 只说明全局策略有效且配置了允许角色，不表示当前用户有权限，也不表示已取得平台许可。服务端最终授权仍在每次写入时执行。

客户端进入贡献表单以及每次提交前重新请求；只在版本、结构、布尔值及有效期均校验通过时显示/启用。网络异常、非 2xx、解析失败、未知版本、到期或缺字段，一律关闭。不得持久化开启状态或以旧值回退；同时使用本地接收时间限制 15 秒寿命。过期响应或旧缓存不能使新会话默认开启。服务端可能在 capability 响应后关闭，因此提交遇 401/403 应显示失败并保持草稿，不能绕过检查重试。

Web 可保留既有 UI，但开关关闭或角色不允许时其写入同样被后端拒绝。展示入口从来不是权限边界。

## 验证

轻量纯策略测试，无 Django、数据库或外部网络：

```sh
cd apps/backend/hinghwa-dict-backend
python3 -m unittest HinghwaDict.test_feature_policy -v
```

Django 请求门禁与原合成业务回归（使用项目现有隔离测试设置/容器，禁止接生产数据库）：

```sh
python manage.py test HinghwaDict.test_feature_policy HinghwaDict.test_feature_access HinghwaDict.test_standalone word.tests
```

覆盖缺失/损坏/过期/未来/旧版本/未知键/重复键/非法角色、即时关闭、active 与角色判断、所有非读取方法、伪造客户端角色、实际申请 View 接线和公开接口只读/不缓存。原合成贡献测试使用临时显式启用策略，验证待审核流程未变化。

本地 stdlib 测试已通过；当前宿主 Python 未安装 Django，Django 测试由主线在现有隔离容器串行运行。本文件不声称完整 Docker 重建、真实账号、设备或平台审核验证已完成。

Compose使用只读策略目录挂载：`FEATURE_POLICY_DIRECTORY`（默认`./config`）与`FEATURE_POLICY_FILE`（默认`feature-policy.example.json`）。目录挂载使运营者原子替换JSON时后端下一次打开能见新文件，避免单文件bind固定旧inode。不要把密钥放进公开站点JSON；策略也不返回角色白名单。兴化合法贡献可显式选择`FEATURE_POLICY_FILE=feature-policy.hinghwa.example.json`，有效期届满必须重新审阅配置，不能自动延长。
