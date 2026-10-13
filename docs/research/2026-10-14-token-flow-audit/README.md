# Token 生成与还原审核归档

- [详细审核报告](report.md)
- [图像对照页](evidence/index.html)（下载此目录后用浏览器打开）
- [五页量测](evidence/results.json)
- [同播放器控制对照](evidence/controlled-comparison/comparison.png)
- [动态修复前](evidence/motion-evidence-before.json)、[修复后](evidence/motion-evidence.json)

报告和所选对照证据一起入库；运行数据库、凭据、原始供应商请求日志、音频与视频不在此归档中。
证据是2026-10-14实测快照，并不授予正式作品批准。
完整复现实验脚本需要报告所列的本地历史输入和独立素材；此目录不是完整课程运行数据库。

线上发布使用独立分支 `codex/token-flow-audit-20261014`。远端main另有设计还原实现，后续合并需完成版本兼容；保留审核时的失败结论，不因代码上传更改签收状态。
