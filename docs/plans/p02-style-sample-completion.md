# P02 首版科普风格试制记录

日期 2026-10-07。阶段状态：首版参数与参考样稿已制作，等待用户视觉审阅；
风格为 draft，尚非可生产版本。下一步 P03 需先补样稿暴露的公共定义，再实现静态内核。

## 交付

- [直接打开样板](../styles/science-explainer/samples/index.html)：初始、讲蒸发、讲凝结、最终、长正文按钮。
- [首版设计规则与经验](../styles/science-explainer/DESIGN.md)：色系、实际字体、空间、素材及扩展需求。
- [风格参数子集](../styles/science-explainer/style.draft.json)：遵守 P01 字段，draft/pending。
- [最终画面](../styles/science-explainer/samples/screenshots/final.png) 及其他状态截图、1366 宽观看截图。
- [素材/字体证据](../styles/science-explainer/asset-font-evidence.json)、
  [浏览器检查](../styles/science-explainer/sample-checks.json)、[知识来源](../styles/science-explainer/content-sources.md)。

## 实测和审阅

固定 Chromium 155.0.8059.12，四状态素材均解码、页脚不越界；长正文两卡文字未超出卡片；
没有脚本错误；正文使用实际 Microsoft YaHei（CDP 字体记录）。在 1366×900 观看尺寸保存截图。
人工查看最终画面：标题/正文/素材主次清楚，无截断；两概念独立、来源与示意说明可见。
这是实施者视觉检查，用户审阅仍 pending，不据此把全部风格参考设为 accepted。

代码审查采用 code-review-and-quality 的五维检查：状态有限、固定内容通过 textContent
修改、不执行外部输入、无业务服务耦合； resize 只整体缩放；按钮带状态与焦点可见。
尚未建立生产字段校验、目标测量、音频时间求值或导出，样稿不用它们的成功状态。

布局压力结论限于本次样例。长文变体通过显式去除重复例子区域腾出空间（原数据保留），
真正内核必须根据配方与 required 内容判定是否允许；否则只能报容量错误。
未检验无标题、多页、替换图片比例、数字人/字幕安全区、跨平台字体与可编辑 PPTX。

下一步：依据视觉审阅调整首版风格；补来源区域、辅助文字角色、比较卡组合、素材面板
和多色文本等定义/能力声明，建立 P03 正式 Schema 与受约束静态渲染。用户桌面应用
仍运行原框架，本 HTML 位于唯一项目目录，通过独立文件审阅，不另建应用副本。
