# 本地同步与跨机编辑器指纹修复 · 2026-10-20

## 范围与基线

本机既有应用源码目录为 `D:\Program Files (x86)\PPT_HTML_Studio`，本次从
`1eac2ac` fast-forward到`00fb81d43c77968a9e0bc734a75a2fd44689457c`，与远程main一致。
原data/runs已备份到该目录的`.tmp/sync-backup-20261020-194906/`；数据库使用SQLite在线备份。
当前聊天目录下`C:\Users\Administrator\Desktop\html动画\PPT_HTML_Studio`仅作本轮隔离验证副本，
不作为另一套日常应用启动。本批修复同步到既有应用源码目录，未发布、未启动应用服务。
继续以[发布 handoff](handoff-release-2026-10-20.md)为业务交接依据。

用户确认 Token 课程和 `outputs/pi-design-alignment-20261020` 位于另一台电脑。
既有本机应用有此前课程数据，但没有本次原失败任务目录和供应商终态回执；
不从 Git 文档猜测失败字段，不把隔离夹具当作原现场，也不重发旧 unknown 请求。

## 已定位并修复的阻断

最新远程 [CI 39405586077](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/actions/runs/39405586077)
已经失败；实际停在 `Verify editor build closure`，三项源指纹断言失败。
后续 canonical full 尚未执行，不能把本次远程 CI 描述为全量测试失败或通过。

根因是部分编辑器指纹用 CRLF 源字节生成，而 GitHub checkout 使用已提交的 LF 字节。
例如 build.mjs 的旧期望为 `1961a4e42c16b08326f7874f5820d43170ef65cbf95545d67b7f96a6ad71f3e8`，
实际已提交 LF 字节为 `e96a5bda820c6430fc0acfe1f6a705320b9bbd5dd657cd7d93a8ecf73e3e421c`。
本机默认 autocrlf=true 还导致 package.json 等源文件不匹配。

- `.gitattributes`仅固定编辑器源文件和已纳入清单的消费者为 LF。
- 许可证归档和生成产物保留原字节；两份上游许可证原本使用 CRLF，不能为了统一换行而破坏其证据哈希。
- 通过原 `editor_ui/build.mjs` 重建三份清单；没有手改 hash、跳过校验或添加 CI 自动重建来掩盖过期发布物。
- 增加真实临时 Git 仓库的 add/checkout-index 回归，分别开启和关闭 autocrlf，逐文件对比源、归档和生成物字节；临时仓库不含用户数据。

这是 HPS-013/015/017/018 下现有源码闭包与可复现检查的修复；
无 scene/binding/API/数据库或业务门禁变化，合同包维持0.9.108、API维持1.59.0。
旧构建快照/签名包继续按原当前性守卫处理，不重写历史或批准。

## 本机验证

- 锁定 Python 依赖已安装，`python -m pip check`通过。
- 原编辑器17项（含新增跨机回归）通过；修改前原16项中3项失败。
- 使用CI同版Node22.19.0独立复测编辑器17项通过；本机默认Node24.12.0也通过。
- Remotion TypeScript检查通过。
- canonical full本机检查通过：quick、独立脚本与全量pytest均完成；pytest为2775 passed、8 skipped、2 warnings，耗时1048.34秒。警告为Starlette弃用提示及重复ZIP条目的预期测试提示。跳过项未记为通过。
- 远端 CI仍为上述旧提交的失败结果，本地通过不表示远端已通过。

日志保存在仓库外同级目录：`ppt-studio-full.log`、`ppt-editor-baseline.log`、
`ppt-editor-fixed.log`、`ppt-editor-build.log`、`ppt-remotion-typecheck.log`。
Node22复测日志为`ppt-editor-node22.log`。
本批未启动正式应用、配置模型或调用付费服务。

## 下一步

1. 本机full已通过；发布后需单独取得新提交的GitHub CI结果，不能沿用本机结果声称远端通过。
2. 无旧数据时继续使用版本化夹具验证工程边界，维持“非原事故复现”的标识。
3. 需要追溯原容量事故时，从原机私下迁移对应任务回执、候选scene/binding、冻结计划、原诊断和实际截图；凭据/完整数据库不进入Git。
4. 若原现场无法迁移，使用本机另建的隔离课程和新任务身份开展验收，重新配置明确的模型连接和预算；不接续旧任务，不声称完成原配对。
5. Legacy仍为默认；真实新页、编辑、听审和正式输出继续独立验收。

## 最终数据核对与审查

原应用目录6420个runs文件与同步前备份逐字节相同；SQLite逻辑内容与在线备份一致。原应用虚拟环境pip check通过，新Pi锁定依赖已安装。编辑器修复在原应用目录17项通过。未启动第二个应用实例。

按code-review-and-quality复核本批差异：换行属性限定编辑器源码闭包；归档许可证/生成物保留原字节；生成JS/CSS字节未变；新增测试在独立临时Git仓库执行，不访问课程数据。无新增依赖、模型调用或批准写入。代码修复与文档仍未提交、未推送；最新远程基线仍为00fb81d4。

本机正式源码目录的`.tmp/local-sync-validation/`保留本轮完整检查、修复前后编辑器检查、Node22复测及构建日志副本。后续真实容量诊断仍需原失败现场或独立新案例；此次全量工程通过不能证明原供应商超时已修复，也不能视为课程视觉/音频验收。
