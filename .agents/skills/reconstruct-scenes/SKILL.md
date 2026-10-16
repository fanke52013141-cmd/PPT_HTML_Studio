---
name: reconstruct-scenes
description: Build and validate exact-RLE PNG reveal assets for the PPT Studio image backend. Use for 图片Mask图层构建、Reveal场景重建; exclude editable HTML reconstruction and semantic rematching.
---

# 图片Reveal场景构建

读取 [共用边界](../workflow-contracts.md)，只用于image backend。输入为当前reveal_manifest、完整位图与已保存精确RLE/手工修正；输出为各页scene/timeline/report与被引用PNG层。

唯一生产builder为scripts/build_reveal_scene.py，版本从ai_mask_contracts.REVEAL_PIPELINE_VERSION读取。需要独立诊断时运行：

```powershell
python scripts/build_reveal_scene.py --manifest <run>/reveal_manifest.json --repo-root .
python scripts/validate_reveal_scene.py --run-dir <run> --repo-root .
```

无Mask是合法静态整页，不强制拆层。有Mask从项目视频背景开始，不以原整图当背景。遵守有效raw/master配对；每组只从Mask边界向内去近白，保留封闭白区、抗锯齿及手工修正。

语义所有权属于AI Mask阶段，builder不得重新匹配。自动Mask须达到99.5%前景覆盖、零未分配、零跨组像素重叠；失败回Mask阶段，不扩边/侵蚀来掩盖。

拒绝坏引用、错版本、陈旧/未引用资产；HTMLbackend转produce-editable-html，不能生成PNG层后冒称可编辑HTML。
