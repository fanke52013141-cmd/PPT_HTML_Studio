# 标准组件库 1.0

现行交付入口是 `standard/` 的 24 张 1920×1080 白底 PNG；`standard-library.html` 是可离线打开的截图与组件调用工具。所有标准截图只有黑、白、中性灰。独立配色仍使用 `palettes.json`，图片风格由统一风格参考约束。

## 覆盖

| 分类 | 参考页 | 登记内容 |
| --- | --- | --- |
| 总览 | 1 | 六组代表组件 |
| 基础组件 | 7 | 32 项：文字、箭头、卡片、形状、标记、关系、数据时间 |
| 呈现变体 | 4 | 16 项：标题、强调、容器、标签；复用父组件语义 |
| 静态效果 | 7 | 28 项：渐变、阴影、描边、透明、裁切、纹理、文字 |
| 组合示例 | 4 | 18 项：排版、精细关系、效果用法、图片融合 |
| 字体 | 1 | 5 种本机实际字体 |

使用 `standard-pages.json` 查页码、内容 ID 与截图名称；`standard/contact-sheet.png` 只用于浏览，喂给生图时选相关分类的原尺寸 PNG。

## 美化与实现

使用内置生图生成的 `assets/monochrome-beauty-ai-v2.png` 研究标题层级、细分隔线、低对比边界、圆角和柔和阴影。代码复刻保留可编辑文字与精确 SVG 关系，不用整页生成图作为底图。各类参考页沿用统一的留白、字阶与表面规则；并非每一页都单独调用了生图。

`standard-library.css` 是统一组件外观源，`standard-library.js` 复用登记的基础组件、变体、效果与组合渲染函数。`build-standard-library.cjs` 从分类目录生成完整页清单与离线 HTML。改变源文件后必须重建并重新导出。

```powershell
node html_engine/reference-library/build-components.cjs
node html_engine/reference-library/export-standard-library.cjs
python html_engine/reference-library/verify-standard-pixels.py
node html_engine/reference-library/verify-components.cjs
node html_engine/reference-library/component-query.cjs --id PV11
```

导出需将 `HPS_CHROME` 设置为本机 Chromium 路径。字体需安装 Noto Sans SC、Noto Serif SC、楷体、Arial、Consolas；未随库打包。

## 调用

在 `standard-library.html` 中可调用：

```js
StandardLibrary.render({ id: 'T01', text: '让重点被看见' });
StandardLibrary.render({ id: 'C03', text: '清楚的结构', variantId: 'PV11' });
StandardLibrary.render({ id: 'PV11', text: '清楚的结构', paletteId: 'science', role: 'secondary' });
StandardLibrary.render({ id: 'E05' });
StandardLibrary.render({ id: 'H02' });
```

返回 DOM 节点，可追加到任意容器。未知 ID、错误变体归属、超过 36 个字符的基础示例文案、未知配色角色会报错。文字使用 textContent。E/P/V/X/H 是固定参考示例，不能传入任意数值、拓扑或内容；该接口是离线参考工具，不代表生产 scene 或应用 API 已完成适配。

## AI 输入规则

选择 1–3 张相关分类参考 + 一份独立配色 + 图片风格参考 + 准确文案与关系。要求 AI 学习比例、字阶、容器、线条和层次；禁止照抄页码、组件编号、样例文案及说明文字。真实内容的文字、数字、标注和语义关系最终由代码控制。

代码擅长准确文字、几何、图表、可编辑卡片、关系、渐变、阴影、描边、裁切和规则纹理。复杂真实物体、人物、自然材质和光影交给生图；图片作为少量独立资产与代码组件融合。

## 验证边界

导出脚本检查全 24 页的尺寸、逐页登记 ID、基础边界、文本横向溢出、比例环线宽、错误输入拒绝、文字安全、离线请求与图片解码。PNG 灰阶另作像素检查。视觉检查不由几何绿灯代替；记录见 `STANDARD-REVIEW.md`。用户最终审美签收与生产适配分开记录。
