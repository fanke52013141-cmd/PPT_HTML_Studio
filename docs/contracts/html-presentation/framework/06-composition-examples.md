# 组合与扩展的具体推演

契约 0.5.0。本文件是组合设计示意，不是已注册的场景 Schema。以下名字以分类候选
为依据；P01 的 scene.example.json 仍按原 0.1.0 字段解释。

## 1. 无标题的对比页

内容层：概念 A、概念 B；关系层：contrast；讲解层：介绍 A→介绍 B→比较。
组件：两个 Concept；风格：消费相同概念变体；动作：绑定两实例的公开 self/body/figure。

```text
page
  main (required)
    split (horizontal, weights=[1,1])
      left -> conceptA
      right -> conceptB
```

不创建 title region，没有“空标题节点”。位置来自 main 分区；标题空间和间隔不会残留。
反例：删掉 P01 旧实例的 title slot 然后宣称兼容；正确处理是新区域/配方定义及新版本实例。
若标题仍为 required 内容，规划先修改其展示/讲述要求，不能仅在布局层藏起来。

## 2. 有标题、左解释、右侧上流程下结论

```text
page
  heading -> textTitle
  main
    split (horizontal, weights=[2,3])
      explanation -> conceptA
      right
        split (vertical, weights=[3,1])
          process -> steps
          conclusion -> textConclusion
```

weights 在每个父区独立归一化，先扣 gap 再按比例分剩余空间，不跨父级共享百分比。
若结论最小高度超过 1/4，布局返回约束冲突或选择有登记的自适应策略，不直接缩小字体。
流程自己排列步骤和连线；外层 split 不知道“第二步必须在第三步之前”的语义。
动作可绑定 stepId；节点换到右侧下方后仍用同一个步骤身份。

新增能力：通用 region/split/nesting、steps 的具体卡；复用 Text/Image/Vector/Group、
公开目标、字体/资源就绪和时间规则。不能只因为画面看起来像 P01 两列就声称全部已有定义。

## 3. 跨页总分总

```text
narrative
  stage.overview   -> slide.overview / beat.overview
  stage.part-a     -> slide.detail-a / beat.detail-a
  stage.part-b     -> slide.detail-b / beat.detail-b
  stage.summary   -> slide.summary / beat.summary
```

各阶段引用同一内容图；overview 中的简述和 detail 中的展开使用不同节点实例，关联同一
知识点及来源。重排页面不改变 stageId/contentId；实际音频/字幕/动作的文档偏移重编。
若将两个分项合为一页，保留阶段和语块身份、创建新槽位映射，再测量容量与局部时间。
反例：通过重复 nodeId 表示“同一概念”；正确方式是多个 nodeId 共享 contentRef。

## 4. 科普风中的机制流程

关系先描述机制及证据；流程组件保存节点和关系边；科普风选择颜色、图标、连接线
样式、说明密度及插图语言。缺少流程组件时先补公共定义；不能专写“科普流程 HTML”。
单个步骤可用图标或图片表现，步骤的文字标签保持可编辑；结构复杂的插画可以作为
独立资源，但图片中必须分别出现的对象需要分别生成/提供资源。

科普插画的透视、相对位置若承载事实，就归素材语义验收；单纯装饰只归风格。
示意比例或非真实颜色须明确标识，风格不能为了好看制造不实的数量和因果关系。

## 5. 选择与错误的可追溯记录

每次组装记录所选能力 ID/版本、选用理由、内容/关系/阶段映射、风格支持、布局约束、
动作目标与输出策略。诊断指到具体区域/节点/阶段，不返回笼统“该模板不支持”。
无定义→提出扩展；有定义未实现→能力未上线；已实现但不兼容当前风格→风格缺项；
超过容量→实例/布局处理；输出不支持→允许降级或阻断。修复路径分别明确。
