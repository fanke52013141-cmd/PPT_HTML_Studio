# Image2.5 VIP 2K / low 真实实验

2026-10-08，关联RES-20261008-04、HPS-026–030、036，契约0.9.8。用户授权ToAPIs测试，凭据仅内存；模型gpt-image-2.5-flare-vip，端点https://api.toapis.com。供应商[VIP文档](https://docs.toapis.com/docs/cn/api-reference/images/gpt-image-2.5-vip/generation.md)确认像素size、六档quality与可选background；模型名称为供应商任务标识，未独立证明上游内部权重。

| 实验 | 请求及实际尺寸 | 质量 / 背景 | 耗时 | settled费用USD |
| --- | --- | --- | --- | --- |
| 四对象拆分重排 | 2048×2048 | low / transparent | 118.90秒 | 0.020404 |
| 四对象完整插画 | 2048×1152 | low / 省略background | 65.37秒 | 0.013888 |

两次均使用原Token信息图为参考，通过文档支持的POST generations + reference_images方式图生图，n=1；上传、提交、轮询复用现有治理器，轮询同一任务，没有重复提交。费用为返回billing（合计0.034292美元），未独立查询账户账单；耗时包含上传、轮询间隔及下载，不能当纯推理时间。两种内容约束不同，不是性能对照组。

## 结果

拆分图RGBA，尺寸准确，alpha范围0–254。4,194,304像素中3,524,959完全透明（84.04%），无alpha=255像素；主体大量alpha=252/253，不能仅凭无255就判主体消失，也不能宣称严格不透明。四个主体顺序正确、无文字，但有光晕、微透明残留和重绘差异；机器人没有参考图旁的黄色光芒。原始图未缩放或增强alpha。

四槽各1024平方，严格source_alpha提取0/4，均SHEET_EDGE_CONTACT。启用既有显式清理threshold=1、guard_radius=2、max_removed_fraction=0.02后，3/4几何候选：robot删除12,833像素，tea删除20,305，brain删除12,295；灯泡SHEET_CLEANUP_BUDGET，未提高预算。三个候选已逐一查看，仍pending_review；未调用多模态审阅、未批准、未注册resources、未修改scene/audio。两次提取退出1表示部分结果。

完整图RGB，全部像素不透明，尺寸准确。四主体可辨认，但机器人补腿、大脑加表情和光芒，属于参考重绘，不是原像素剪贴。没有4次同模型、质量、有效对象像素尺寸单图基线及人工分钟，不能宣布效率提升。

## 实现与证据

修正ai_provider_service：仅两个2.5 VIP型号采用准确像素size及六档quality，省略resolution；可选透明默认省略，旧型号比例/resolution保持。html_image_provider转发transparent_background。未改变公共请求、Agent API、数据库或旧候选处理版本；面板1536×1024和单对象1024重试默认仍保持。2048平方满槽超现有单槽400万像素预算，2K产品默认须另定义符合预算的留边槽位，不能硬改。

scripts/test_image25_provider.py复用应用适配器，getpass无回显输入，不导入server、读取业务设置或数据库。独立运行目录outputs/image25-sheet/toapis-2k-low-v1/包含split.png、complete.png、evidence.json（安全wire摘要、任务、usage、billing）、spec.json、extraction/、extraction-clean/；参考URL和认证头不记录，运行目录不提交。

工程验证：参数/HTML适配/原供应商/网关18通过，治理恢复/素材板生成/模型绑定32通过。新模块Ruff通过；共享ai_provider_service已有CODE_INVALID_PARAMETERS未用导入导致全文件Ruff F401，本轮未改无关旧代码。git diff --check通过，既有CRLF提示。

下一步：针对无发光、无阴影、干净透明边界作一次有记录的提示词修正；仍失败时只重试灯泡。身份和边缘通过后，再做同模型low、控制对象有效尺寸的单图基线，比较总费用、墙钟及人工分钟。多模态审阅仍需可用文字模型，本次未验证Decisions API。
