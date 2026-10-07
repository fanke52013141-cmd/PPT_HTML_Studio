# motion-02 实验定义卡

ID trial.paper-plane.01，版本 0.3.0-experiment；draft，契约 0.7.0；公共动作注册、模板登记与发布未实现。
输入、对象、坐标、运动窗口、锚点、图层、资源和初末状态详见 design-definition.json；原始版本保留为 design-definition-v1.json。
公开实验 API：window.objectMotion.evaluate(t)、curve(u)；window.motionTrial.seek(t)、renderAt(t)、play()、pause()；window.motionReady。
evaluate 拒绝非有限或范围外的毫秒值；t 范围 [0,10000]。renderAt 仅渲染，seek 更新播放时间并暂停；采样输出使用 renderAt。
同一画面 CPU Canvas 承担图片与轨迹/圆，HTML 承担标题、副标题与摘要。不会执行模型输出代码。
验收证据和未通过项见 validation-report.md。仅本例 HTML 与视频，无通用目标几何接口、音频/数字人、PPTX或跨浏览器支持承诺。
