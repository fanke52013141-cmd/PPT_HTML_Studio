# 勾画标注模块适配器选型决策(W0)

决策日期:2026-09-27。代码基线:`5670f0e`。测试机器:Windows 10 x64
(10.0.26200),Python 3.13.5,httpx(仓库既有依赖),Pillow 10.4.0。

本文按《勾画标注模块开发与验收交接》第 6.1 节要求,冻结首个 OCR 适配器的
选型、版本、实测指标与降级行为。**音频对齐适配器尚未选型**,属于 W4,
本文不覆盖;在此之前不得宣称"字词准确同步"能力。

## 1. 选定方案

| 项 | 冻结值 |
| --- | --- |
| 服务 | 百度智能云 通用文字识别(标准版) |
| 端点 | `POST https://aip.baidubce.com/rest/2.0/ocr/v1/general` |
| 鉴权 | 新版统一 API Key(`bce-v3/{AK}/{SK}` 格式,授权范围含"AI 开放能力")直接放 `Authorization: Bearer <API Key>` 请求头 |
| 默认参数 | `language_type=CHN_ENG`,`recognize_granularity=small`,`detect_direction=true`,`probability=true` |
| 引擎版本常量 | `baidu_ocr_general_v1`(`annotation_ocr_baidu.py`,参与缓存键;默认参数变更时递增) |
| 生产模块 | `annotation_ocr_baidu.py`(纯模块:无 server/FastAPI/数据库依赖,密钥注入,不落日志) |
| 测试 | `checks/test_annotation_ocr_baidu.py`(离线 stub 25 例 + 真实引擎 opt-in 1 例) |
| 传输 | httpx 同步 Client,默认超时 20s,单次调用不内建重试(重试/退避由任务层按 governor 语义统一控制) |

密钥不进入仓库:真实引擎验收通过环境变量 `PPT_ANNOTATION_BAIDU_OCR_KEY`
注入。生产侧密钥落位(全局设置字段、配置包导入导出与掩码)排入 W3,
与既有 provider 凭据同一套规范,不新增独立配置面。

## 2. 鉴权方式实测记录(为什么是 Bearer)

| 尝试 | 结果 |
| --- | --- |
| 旧版 `oauth/2.0/token` client_credentials(AK/SK 拆分) | HTTP 401 `unknown client id`——bce-v3 密钥不是旧版应用 API Key |
| 密钥直接作 `access_token` 查询参数 | `error_code=110` Access token invalid |
| `bce-auth-v3` 签名直连 | `error_code=14` IAM Certification failed(v3 面向 BCE 云产品 API,aip 不走) |
| `bce-auth-v1` 签名(对照 bce-sdk-python 实现逐字节复刻) | 仍 `error_code=14`(该路径要求旧版 32 位 hex IAM AK,`ALTAK-` 新格式不在其列) |
| **`Authorization: Bearer <bce-v3 密钥>`** | **HTTP 200,正常返回识别结果** |
| 错误密钥 Bearer | HTTP 200 + `error_code=23` IAM API-KEY authentication failed(注意:错误也是 200,不能按状态码判错) |

同一密钥在千帆 v2 面(`qianfan.baidubce.com/v2`)同样以 Bearer 鉴权通过
(仅模型名报错),证明密钥本身有效且适用 Bearer 机制。

## 3. 实测指标(冻结样本)

样本:`checks/fixtures/annotations/sample_slide.png`(1920×1080 合成 PPT 页,
中英混排 + 日期 + 百分比 + 描边标签;生成脚本与真值见第 5 节)。

| 指标 | 实测(2026-09-27) |
| --- | --- |
| 行识别 | 7/7 行全部正确,行置信度 average 0.992–1.0 |
| 字级框 | `recognize_granularity=small` 返回**引擎真实检测的单字框**(非均分),坐标准确 |
| 朝向 | `detect_direction=true` 返回 `direction=0`(正向) |
| 时延(冷,首次) | 0.63s |
| 时延(热,×3) | 0.50s / 0.51s / 0.53s |
| 图片体积 | 1920×1080 PNG ≈ 100KB,base64 后 ≈ 136KB |

质量门对照(交接文档 11.2):字级输出来源为引擎真实检测,满足"0 个行框
均分冒充字框";引擎无字级结果时适配器诚实标记 `granularity="line"`,
上层必须按"空间状态进入待确认"处理,不得伪造字级。

## 4. 已知引擎行为与降级

- **标点归一化**:半角冒号等会被引擎归一化为全角(实测绘制
  `18:00`、识别返回 `18:00`)。适配器原样保留识别文本;纠正与重定位
  属于 `annotation_text_layout` 层(人工纠正保留原识别文本,字符边界
  变化时重定位局部范围)。
- **错误映射**(`BaiduOcrError.category` / `retryable`):
  - `auth`(23/110/111/15):不可重试,需用户修配置;
  - `quota`(17/19):每日/总量配额耗尽,按 governor 语义暂停而非内容错误;
  - `rate_limit`(4/18):QPS 超限,可短退避重试;
  - `image`(216200–216203/空图/超限):不可重试,调用方决定重编码并记录反变换;
  - `engine`(其余 int code,如 282200):可重试;
  - `network`(httpx 异常):可重试;
  - `protocol`(结构损坏/非 JSON):不可重试,不得伪装成空成功。
- **体积限制**:通用文字识别 `image` 参数要求 base64+urlencode 后不超过
  8M(接口文档),部分文档页写 4M,适配器按 8M 校验;超限在传输前快速
  失败。生产图 1920×1080 PNG 实测 ≈ 100–500KB,远低于限制;上层如做
  ROI 裁剪/重编码,必须记录完整反变换(交接 6.2)。
- **坐标语义**:location/chars 均为提交图像原始像素坐标(原点左上);
  适配器不做任何换算,ROI 逆变换由统一文字布局层负责。
- **缓存键**:`build_ocr_cache_key` = 图像字节哈希 + 引擎/配置快照 + ROI;
  密钥不参与(同配置换账号命中同键,避免凭据派生信息落盘);只换音频
  不重 OCR。
- **传输细节坑**(已固化并有防回归测试):httpx `data=` 中出现 bytes 值会
  触发 multipart 编码,aip 收到后报 216201 image format error——image
  字段必须传 str;base64 字符串在 urlencoded body 中由 httpx 正确转义。

## 5. 冻结样本与真值

| 文件 | SHA-256 |
| --- | --- |
| `checks/fixtures/annotations/sample_slide.png` | `60f6f95f9d826cb7c563ee8d1200bfaf5a8d0f6110a30ddf5aaf8d7a452c0bea` |
| `checks/fixtures/annotations/sample_numbers.png` | `f9d1a69969af6640a34cd012e933e9432cb4e014c8ea97faf6c8a6dad860de5b` |
| `checks/fixtures/annotations/samples_truth.json` | `0bfeaf66b5c0e9202f95b65283485f5381198e8a7a5ae677658037983334ce88` |

- 生成脚本 `checks/fixtures/annotations/make_annotation_samples.py`
  确定性重绘(固定文本/字体/坐标);字体依赖 Windows msyh.ttc 与
  arial.ttf,产物已提交,测试无需重新生成。
- `samples_truth.json` 记录每行精确绘制包围盒,供后续自动选点/空间正确性
  评测(≥90% 门)使用;评测输入端不得读取真值。
- 真实评测样本集(≥20 页、≥40 目标、≥8 页盲测)按交接 11.1 在 W3 扩充,
  本批 2 张为起点,覆盖中英混排/日期/百分比/金额/版本号。

## 6. 复跑命令

离线单测(默认,无网络、无配额):

```powershell
python -m pytest checks/test_annotation_ocr_baidu.py -q
```

真实引擎验收(opt-in):

```powershell
$env:PPT_ANNOTATION_BAIDU_OCR_KEY = "<bce-v3 密钥>"
python -m pytest checks/test_annotation_ocr_baidu.py::test_real_engine_recognizes_frozen_fixture -q
```

直接手测(等价 curl):

```bash
curl -s -X POST "https://aip.baidubce.com/rest/2.0/ocr/v1/general" \
  -H "Authorization: Bearer <bce-v3 密钥>" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "image=<base64>&language_type=CHN_ENG&recognize_granularity=small"
```

## 7. 遗留与后续

- W1:OCR 结果并入 `annotation_text_layout.py` 统一接口(候选 ID 稳定化、
  阅读顺序、缓存落盘、纠正重定位),本适配器为其引擎实现。
- W3:密钥进入全局设置/配置包(含掩码、连接检查、Agent parity);
  真实评测样本集扩充;AI 规划 Prompt(按 optimize-prompts 流程)。
- W4:音频对齐适配器选型(候选 WhisperX 等,另行评测决策),本文不含。
- 并发/配额:OCR 请求接入 `generation_governor` 时按网关全局键计量,
  具体资源分类(image/text)在任务层接线时定案。

## 8. W4 音频对齐适配器决策(2026-09-27 补记)

| 项 | 冻结值 |
| --- | --- |
| 首期选定 | **句级时间适配器**(`annotation_alignment.py`,engine_version=`sentence_timeline_v1`):读取既有 TTS 产物 `slides/<id>/audio_timeline.json` 的 `segments`(beat_id→start/end,`timing_source=provider_sentence_timestamps`) |
| 精度诚实 | 全部锚定条目标 `temporal=sentence_fallback`;无对应音频的语块标记 `unavailable`;严禁标 word_aligned |
| 时间语义 | 以音频文件起点为 0;区间必须有限/非负/start<end/不超内容时长,非法段跳过 |
| 缓存键 | 音频字节哈希 + 发音文本哈希 + 引擎版本(`word_alignment_cache_key`) |
| 支持范围(首期) | sentence_fallback + manual;字级对齐未交付,不发布"字词准确同步"声明 |
| 字级引擎 preflight | whisperx 3.8.6 在 PyPI 可达;本机 Python 3.13.5 无 torch/whisperx。按交接 6.1,不自动安装大型模型依赖——字级引擎列入可选 worker 子进程环境(独立解释器+模型路径)的后续评测项;评测命令与真实指标待该项执行后补记 |
| 交接门对照 | 11.2 时间同步门:word_aligned 组不存在即无门槛违规;句级降级路径走"明确收窄支持范围"条款 |

句级对齐已由 `checks/test_annotation_alignment.py`(6 例)覆盖:区间提取、
非法段跳过、缺失区间如实标记、缓存键敏感性。
