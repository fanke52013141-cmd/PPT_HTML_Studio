# AI Mask 拆分精度 A/B 对比报告（自适应背景 + 细粒度检测转默认）

日期：2026-09-27
分支：`ai-mask-accuracy-optimization`
对应方案：`docs/plans/ai_mask_accuracy_optimization_plan_20260927.md`（WP1 + WP3 第一步）
对应调研：`docs/RESEARCH_2026-09-27_ai_mask_accuracy.md`

## 1. 改动内容

| 文件 | 改动 |
| --- | --- |
| `ai_mask_component_detection.py` | 新增 `background_mode` 设置（`white`/`auto`）：auto 模式从四边 border 带估计背景色（中位数 + MAD + 离群剔除），底色仍满足白底判定时**逐位保持旧公式**（path=`legacy_white`），否则切换为"与估计背景的最大通道距离 ≤ 容差"判定（path=`adaptive`），垫边颜色同步改为背景色；自适应路径新增细粒度检测器的 pale 门控（防止整幅背景成为支持层）与 1px 抗锯齿边缘环支持层（贴内容、与背景有差异的像素并入归属波前）；`background_mode` 进入检测设置指纹 |
| `ai_mask_engine.py` | `DEFAULT_SETTINGS` / `normalize_settings`：`background_mode="auto"`、`fine_grained_detection=True`（原 False） |
| `static/ai_mask_extension.js` | 设置弹窗新增"背景色模式"下拉框（select 控件支持） |
| `scripts/ai_mask_benchmark.py` | baseline 增加 `--background-mode` 参数 |
| `scripts/ai_mask_nonwhite_benchmark.py` | 新增非白底基准（生成/基线/评分，真值=与案例背景色有任何差异的像素） |
| `docs/ai-mask-optimization/validation_nonwhite/` | 新增 3 个非白底冻结案例（米色卡片、浅灰密排、淡彩浅色卡） |
| `checks/test_ai_mask_adaptive_background.py` | 新增 6 项单测（白底逐位一致、非白底拆分、白底模式失败模式固化、细粒度支持层门控、缓存指纹） |
| `checks/test_ai_mask_automation.py`、`checks/test_ai_mask_fine_grained_detection.py` | 闭运算路径测试显式 opt-in `fine_grained_detection=False`；默认值断言更新为 True（依据即本报告 A/B） |

## 2. 实验方法

- 同一代码基线上先跑 before（分支前代码），再跑 after（本改动，生产默认设置等效：细粒度 + auto 背景）。
- 白底集：`docs/ai-mask-optimization/validation`（11 冻结案例）；非白底集：`docs/ai-mask-optimization/validation_nonwhite`（3 新案例）。
- 指标：macro IoU、coverage、pale_recall、逐组 precision/recall、通过门（coverage≥0.995 且逐组 p/r≥0.99 且零重叠）。
- 复现命令：
  ```powershell
  python scripts/ai_mask_benchmark.py baseline --root docs/ai-mask-optimization/validation --output <out> --fine-grained --background-mode auto
  python scripts/ai_mask_nonwhite_benchmark.py baseline --root docs/ai-mask-optimization/validation_nonwhite --output <out> --background-mode auto --fine-grained
  ```

## 3. 结果

### 3.1 白底集（w7，11 案例）

| 案例 | IoU 旧→新 | coverage 旧→新 | pale_recall 旧→新 |
| --- | --- | --- | --- |
| 01_separated | 0.990 → 0.999 | 0.999 → 1.000 | 0.100 → 0.912 |
| 02_gap_8px | 0.323 → 0.999 | 0.999 → 1.000 | 0.100 → 0.912 |
| 03_gap_2px | 0.323 → 0.999 | 0.999 → 1.000 | 0.100 → 0.912 |
| 04_arrow_bridge | 0.990 → 0.998 | 0.999 → 1.000 | 0.100 → 0.912 |
| 05_pale | 0.314 → 0.999 | 0.111 → 1.000 | 0.034 → 1.000 |
| 06_dense_15 | 0.998 → 1.000 | 1.000 → 1.000 | 0.100 → 0.912 |
| 07_nested | 0.161 → 1.000 | 0.999 → 1.000 | 0.100 → 0.912 |
| 08_detached | 0.978 → 0.997 | 0.980 → 0.997 | 0.081 → 0.860 |
| 09_pale_nested_combo | 0.651 → 1.000 | 0.551 → 1.000 | 0.526 → 1.000 |
| 10_dense_20 | 0.085 → 1.000 | 1.000 → 1.000 | 0.211 → 1.000 |
| 11_halo_lines | 0.964 → 1.000 | 0.961 → 1.000 | 0.175 → 1.000 |
| **通过门** | **0/11 → 11/11** | 均值 0.873 → 0.9997 | 均值 0.148 → 0.939 |

auto 模式在全部白底案例上走 `legacy_white` 快捷路径（四边中位数为纯白），与旧代码逐位一致——白底提升全部来自细粒度检测器转默认，与背景改动零耦合。

### 3.2 非白底集（3 新案例）

| 案例 | IoU 旧 → 新 | coverage 旧 → 新 | 通过门 |
| --- | --- | --- | --- |
| 12_beige_cards（米色底） | 0.082 → 1.000 | 1.000 → 1.000 | 否 → **是** |
| 13_gray_dense（浅灰密排 15 组） | 0.004 → 1.000 | 1.000 → 1.000 | 否 → **是** |
| 14_tint_pale（淡蓝浅色卡） | 0.082 → 1.000 | 1.000 → 1.000 | 否 → **是** |

旧代码在非白底上把整幅图熔成单一组件（IoU≈0.05，即调研预测的完全失效模式）；auto 模式逐组 precision/recall 全部 1.000。修复抗锯齿边缘环（真值按"任何差异"计前景、检测按"距离≤容差"计背景造成的 1-2px 混合壳丢失）后，标题细笔画组的召回从 0.955 提到 1.000。

### 3.3 检测耗时（w7 11 页合计，CPU，冷缓存）

旧默认闭运算 36.3s → 新默认细粒度 67.3s（约 +31s/页 → +6s/页）。换来了通过门 0/11→11/11 与浅色召回 0.15→0.94，符合"不许用漏像素换速度"红线的反向取舍；逐页秒级增量在批量生产节奏中可接受。

## 4. 回归验证

- `checks/test_ai_mask_adaptive_background.py`：6/6 通过。
- AI Mask 全家桶（automation/fine_grained/benchmark_metrics/benchmark_runner/benchmark_tools/provenance/registration/semantic_batches/semantic_protocol/services/doclayout/mask_source_pair/mask_editor_services + e2e/reveal_integrity/concurrency/ui）：145 通过、7 跳过（doclayout 设备矩阵，环境无关）。
- `checks/agent/`：423 通过；`generate_agent_contracts.py --check`：能力矩阵最新。
- `node --check static/ai_mask_extension.js`、`node checks/test_visible_flow.js`：通过。
- `compileall`（ai_mask 模块 + scripts + checks）：通过。

## 5. 决策与遗留

**决策：采纳（替换默认行为并入库）。** 两套基准 14/14 全过、旧基线 0/14，无任何案例回退。

遗留边界（后续工作包）：
1. 非白底页的 reveal 图层下游（`scripts/build_reveal_scene.py` 抠图白底地板）尚未适配非白底——生产上非白底页建议配合 WP9"上传图规范化贴白底"使用；本次仅承诺检测层精度。
2. 极端纹理/渐变底（band MAD 大）容差自动放大上限 60，更极端的底建议走 WP11 BiRefNet 兜底臂（凭证据立项）。
3. `background_mode=auto` + 回滚闭运算路径的组合不获得边缘环支持（细粒度路径专属）；回滚用户保持回滚语义。
4. 全屏铺边内容（无背景带）会触发离群剔除仍可能估偏，此场景走 `background_mode=white` + WP9。
