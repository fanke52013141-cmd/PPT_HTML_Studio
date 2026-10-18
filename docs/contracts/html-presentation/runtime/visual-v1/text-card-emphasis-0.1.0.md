# 描边文本卡片的局部强调 0.1.0

契约0.9.94，HPS-015/017/023/025/037。现有text-card-outline不变；新text-card-outline-emphasis仅text节点、scene0.7，复用原卡片22/18内边距、72图标、20间距和主题色；emphasis=true的run字重700，其余400；非首run的强调片段前加0.25em视觉间距，保留原字符不插空格。不改文字、节点、动作或关系。通过原set_variant显式选择，已有typography.text控制字号、行高、对齐。

变体注册是唯一造型来源，Schema、catalog、browser bundle同步生成。源闭包使旧候选失效，不迁移批准。验证需检查卡片外观/图标保持、run文字不变及400/700真实渲染；不能用离线候选通过宣称原模型任务成功或HTML获批。
