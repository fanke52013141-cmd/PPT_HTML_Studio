# E1：数据驱动的混合视觉场景内核

版本 0.1.0；单场景原型。读取同一 [Schema](scene.schema.json) 的两份作者输入，由同一编译器、渲染器和时间求值生成 HTML/Canvas 画面。
当前只是独立内核，不是应用的 HTML 后端；原图片服务、数据库和桌面启动入口没有变化。

## 查看和编辑

直接打开 [预览页](preview/index.html)，切换纸飞机/云朵实例。可播放、暂停、倒放和拖动，查看关键帧。
展开“查看或修改场景输入”后，可编辑 JSON 或打开外部 JSON，再应用、保存源输入、查看编译快照和当前目标几何。应用失败保留之前就绪画面。
源文件：[纸飞机](examples/paper-plane.scene.json)、[云朵](examples/cloud-drift.scene.json)。修改后需构建，预览页才加载最新源文件；页面中应用的修改可保存为 JSON，本轮不自动写回磁盘或应用数据库。

## 已实现范围

- format=hps.e1.scene，schemaVersion=0.1.0，contractVersion=0.7.1；与 P01 scene 0.1.0 是不同格式，未知版本/能力明确拒绝。
- text/image/path/ring；纯文本 HTML、独立 PNG、代码曲线/终点。背景由风格参数控制。
- opacity、move-path、rotate、path-progress；每次从给定毫秒 t 求值，支持零时长、结束保持及通道冲突检查。
- 资源版本/字节 SHA-256/解码/尺寸/alphaBounds；资源锚点与 contain；所有摘要文字容量检查。
- whole-node self 几何：图片仿射四角、真实文字行、曲线保守包围和采样路径。透明状态仍保留几何；不推断图片内部语义对象或跨对象遮挡。
- 浏览器直接打开 file 页面，所有资源从构建产物读取，无运行网络请求、模型调用或自由代码执行。

限制：设计探索模式、固定镜头、人工时间、显式布局框、系统 Microsoft YaHei 字体。模板批准、自动排版、Group/Concept、句内锚点、生产编辑/任务、音频/数字人、多场景和 PPTX 未实现。
资产沿用 motion-02 的 conditional-experiment 状态，原留边与边缘问题未升级为 approved。新页面的审美审阅待用户进行。

## 构建与验证

需要 Node.js 20+；版本锁见 package-lock.json。Windows 测试环境使用 Chromium 155.0.8059.12；换机器需设置 CHROME_PATH 为已验证的 Chromium 路径，并具备显式系统字体。

```powershell
npm ci --ignore-scripts
npm run build
npm test
node scripts/export-video.cjs examples/paper-plane.scene.json
```

导出另需 ffmpeg/ffprobe 在 PATH；1280×720、30fps 的两个 16:9 例已实测，无音频。其他画幅需要独立检查，不默默拉伸。
导出先写任务临时文件，完整验证后发布新修订文件，旧文件保留；MP4 放 outputs/e1，不提交 Git。实际路径与哈希见 evidence/video-*.json。

## 模块所有权

| 文件 | 职责 |
| --- | --- |
| scene.schema.json / src/generated | 唯一字段 Schema及生成校验器；生成文件不手改 |
| src/registry.cjs | E1 限定版本、组件/动作、资源与渲染能力范围 |
| src/compiler.cjs | 结构/引用/通道/连续性/预算检查，冻结源输入与编译快照 |
| src/timeline.cjs | 纯时间求值、曲线、图片适配与变换，不依赖 DOM |
| src/resources.cjs | 固定包内资源、哈希/解码/尺寸/alpha 检查及系统字体探测 |
| src/geometry.cjs | 设计单位目标几何，不把整个 Canvas 当成内部对象 |
| src/renderer.cjs | DOM/Canvas 分层、就绪、测量、渲染及原子切换 |
| preview/viewer.js | 播放器和 JSON 编辑展示，不包含纸飞机业务逻辑 |
| scripts/build.cjs | 从 Schema/实例/资产生成校验器、离线包、浏览器代码和审计记录 |
| scripts/export-video.cjs | 同一渲染器按有理帧时刻取帧、编码、验证与版本发布 |

preview/engine.js、fixtures.js 和 src/generated 是可重建发布产物，不是第二份手工配置。禁止仅改生成包而不改源文件。
输入 JSON 与图片字节是数据；不接收任意 HTML、CSS、JS、远程资源或模型输出脚本。
资源总像素与 Canvas 层像素有明确预算，模型不能靠增加图层绕过能力范围。

## 定义与证据

[E1 定义卡](../docs/contracts/html-presentation/runtime/e1/README.md)、[交付记录](../docs/plans/e1-data-driven-engine-completion.md)、[检查](evidence/checks.json)、[编译快照](evidence/compiled-snapshots.json)、[构建审计](evidence/build.json)、[代码审查](evidence/code-review.md)。
跨浏览器、全字形覆盖和字体文件打包未验证，不能把本机 probe 和 fonts.ready 视为完整字体兼容。

## E2 扩展

[受约束配方](recipes/README.md) 已实现两个配方、三份新输入；运行 `npm run build:e2` 更新全部预览，`npm run test:e2` 验证。原 E1 运行格式不变。见 [E2 记录](../docs/plans/e2-constrained-template-completion.md)，资产/视觉仍待确认。
