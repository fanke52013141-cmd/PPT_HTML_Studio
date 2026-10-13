"""A02 independent-subject requests; no generation or fabricated anchor coordinates."""
from __future__ import annotations

import json

PROMPT_VERSION = "html-independent-subject/0.2.0"


def asset_design_request(need: dict) -> dict:
    if need["sourceMode"] == "existing":
        return {"status": "reuse_only", "objectId": need["objectId"], "assetRef": need["assetRef"]}
    content = {key: need[key] for key in ("role", "need", "meaning", "initialState", "endState", "state_sequence", "requiredAnchors")}
    prompt = (
        f"PromptVersion:{PROMPT_VERSION}。只生成一份独立主体，不生成整页设计。"
        "保留已认可的柔和科普材质、光照和清晰轮廓，配色沿用设计参考；透明背景、完整边界。"
        "讲稿是用途真值，状态序列用于保证同一主体能配合逐句讲解；只画主体职责中的实物/形象。"
        "文字、数字、价格、单位、箭头、容量条、步骤和输入→处理→输出关系由代码另画，图片中不出现。"
        "不得把多个须分别控制的概念烘焙在一张图内；不画动作阶段拼图、不画分镜板。"
        "requiredAnchors 说明后续需要人工/实际定位的部位，不输出坐标或以中心 focus 代替；生图成功不等于锚点已验证。"
        "主体用途：" + json.dumps(content, ensure_ascii=False)
    )
    return {"status": "prepared_not_called", "prompt_version": PROMPT_VERSION,
            "id": need["id"], "role": need["role"], "need": need["need"],
            "prompt": prompt, "size": "1024x1024", "quality": "low", "transparent_background": True}
