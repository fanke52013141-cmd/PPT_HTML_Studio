# 识别样本跨机迁移工具发布备注 · 2026-10-22

仓库 [PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)，main。
契约与评测见[固定识别评测](../plans/html-backend-development/feature-recognition-benchmark-2026-10-21.md)。

## 用途

真实跨课程识别样本不在本机，需要可审计的跨机传递。本批新增
`scripts/feature_recognition_bundle.py`（`hps.feature_recognition.bundle/0.1.0`）：

- `export --dataset DATASET.json --output BUNDLE.zip`：只收集 dataset 引用的
  reference/request/labels/response 与 dataset 本身，逐文件校验 SHA-256、路径越界、符号链接与体积预算；
- `import --bundle BUNDLE.zip --output NEW_DIR`：先验证 manifest、成员集合、dataset hash 与逐文件 hash，
  全部通过后才创建目标目录；已存在目录拒绝覆盖；
- 不运行服务、不调用供应商、不写作者、不签发批准；`approvals_transferred=false` 明确记录。

## 验证

- `checks/test_feature_recognition_bundle.py` 4 passed：往返字节一致、导入后计分结果与原数据集完全相同、
  篡改成员被拒且不落盘、路径越界/已存在目录被拒、导出拒绝覆盖与哈希不符。
- 受控 v0.2.0 夹具往返：8 个文件、2 页、69,258 字节；`by_provenance`/`by_ownership`/dataset hash 一致。

## 边界

工具只保证**材料字节与身份**可跨机传递；真实模型响应、标签权威和人工签收仍需操作者按原流程记录，
不能用工具本身证明真实课程泛化。下一步：另一台机导出真实未曝光课程材料，导入后按 0.2.0 标注并跑
`evaluate_feature_recognition.py`，形成真实跨课程分母。
