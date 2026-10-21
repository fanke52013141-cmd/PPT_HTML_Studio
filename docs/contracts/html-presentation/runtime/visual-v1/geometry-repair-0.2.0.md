# 几何修复 0.2.0：关系附着点确定性路由

契约包 0.9.114；HPS-007/009/010/013/015–018/023–025。替代 0.1.x 的“只移动被穿文字/端点卡片”路径，
新增**不移动作者文字、不改关系对象**的确定性路由能力。

## 适用范围

- 仅用于**显式 `from`/`to` 且两端都是 `point`** 的关系箭头；图片 `anchorId` 端点固定，不参与路由。
- 作用域：箭头本身或其被穿文字在修复 `scope` 内；不会触碰 scope 外的对象。
- 不改文字、不改样式、不改关系对象身份与语义；只调整声明端点在目标对象边界上的归一化附着点。
- 原编译器、容量/几何检查与 30fps/registered 动态检查仍是唯一验收者；候选必须显式保存，不自动批准。

## 求解与边界

1. 边界候选：目标对象四边 × 归一化分位（含角点去重）。
2. 先枚举单端移动，全部有交叉时才枚举两端组合；采样帧上限 24，每个冲突最多产出 6 个候选。
3. 判定复用原 `vector-overlap` 线段/文字矩形谓词，并要求对**所有可见文字**无穿越（不只被穿的那一个），
   避免把缺陷转移到相邻标签。
4. 排序：先按命中数，再按附着点位移；同分按操作字典序稳定。
5. **无解必须是确定结论**：找不到候选时返回空提案，不返回 unknown、不请求模型、不改场景。
   由上层 `geometry_first` 记录 `fallback_reason` 后才可进入原模型路径。

## 操作契约

`set_endpoint_point`（仅确定性几何路径产出；模型修复 Prompt 不提供该 kind）：

```json
{"targetId": "<relation-id>", "kind": "set_endpoint_point",
 "values": {"from": {"x": 1, "y": 0.2}, "to": {"x": 0, "y": 0.2}}}
```

- 允许字段仅 `from`/`to`，每端必须是 `{x,y}` 且为 0–1 有限数；
- 端点必须是既有 `{objectId, point}`，不允许 `anchorId` 端点；
- 修改后两端不得重合（`ENDPOINT_ZERO_LENGTH`）；
- 非关系节点、字段越界、未知字段分别返回 `ENDPOINT_POINT_REQUIRED` / `REPAIR_FIELDS`；
- 人工保护路径仍由 `assert_manual_fields_unmodified` 拦截，AI 候选不能覆盖人工端点。

## Agent 同步

- `html_repair.preview` / `html_repair.save` → 1.8；`html_repair.generate` → 1.6；
- `AGENT_API_VERSION` → 1.61.0；capability matrix 已重新生成；
- 无数据库迁移、无新 HTTP 路由；`RepairOperation.kind` 扩为六种，旧客户端请求不受影响。

## 验证

- 冻结帧基准 `checks/fixtures/geometry-endpoint-routing/dataset.json`
  （hash `4e027ec3da0189927f1f0516663e327ff2f7610a48735519786448d91d89061f`）：
  2 个可路由穿字用例 0/2 → **2/2** 求解；3 个非路由用例（无解、anchor、隐式槽位箭头）**3/3** 正确跳过；
  误生成候选 0；模型调用 0；基准耗时约 0.03 秒。
- `checks/test_geometry_endpoint_routing.py` 11 passed：操作安全、身份保持、全文字避让、无解跳过、基准快照。

## 未决

真实第 4 页 540 时点 3 组穿字的原始 scene/binding 仍在另一台机，需按 hash 封存移交后复验；本契约只证明
确定性求解与无解结论，不证明真实页已修复或视觉验收。
