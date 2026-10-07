# E1 运行定义卡包

版本 0.1.0；契约 0.7.1；单场景、设计探索用途。format=hps.e1.scene 与 P01 Scene 0.1.0 区分，P01 定义和夹具保留，不自动迁移。
按顺序阅读 [场景](01-scene.md)、[原子与风格](02-primitives-style.md)、[动作](03-motion.md)、[资源与几何](04-resources-geometry.md)。
精确字段类型、必填、范围、未知字段和联合类型以 [JSON Schema](../../../../../html_engine/scene.schema.json) 为字段事实来源；各卡负责语义。Schema 与编译器必须一起校验。
定义 specified；实现与验证状态见 [索引](definition-index.json)，交付证据见 [E1 记录](../../../../plans/e1-data-driven-engine-completion.md)。不得将单场景运行能力推断为完整 HTML 后端。
