# motion-02：资产板与短过程动画验证

本轮依据契约 0.7.0，先填写对象/运动，再验证关键帧、资产板、提取与实际 HTML 合成。独立实验，不是生产内核或通用模板。

- [可交互动画](index.html)：播放、暂停、倒放、拖动；切换视觉参照和原始资产板。
- [对象与运动清单](design-record.md)、[当前实验定义](design-definition.json)、[初版输入](design-definition-v1.json)。
- [验证与借鉴结论](validation-report.md)、[工程检查](checks.json)、[资产追溯](asset-evidence.json)、[生成输入输出](prompt-io.json)、[视频记录](video-evidence.json)。

10 秒纸飞机动画，3 个生成图片资产，其余文字/背景/轨迹/终点由代码实现。临时轨迹在终态消失。无音频，本轮不替换语音、音频时间轴或数字人。
可以用浏览器直接打开 index.html。实际字体为测试机 Microsoft YaHei；字体文件未分发，跨环境排版尚未验证。

本地视频为 outputs/motion-02/paper-plane.mp4，按项目规则不提交 Git。视频参数与哈希保存在 video-evidence.json。
用户视觉审阅：pending。资产板严格留边与源分辨率边缘质量仍需改进；可运行不表示所有美术门槛通过。

复核脚本：extract-slots.py 重现固定矩形提取（需要 Pillow）；verify-local.cjs 重现 Chromium 帧/状态检查，依赖路径对应当前测试机，换机器须配置 Playwright 与浏览器路径。
