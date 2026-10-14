# 用户指定图片默认值 0.1.0

2026-10-14 用户指定增量：新连接gpt-image-2.5-sunburst-official使用2K/low；凭据保存在本地引用库，API地址须由用户明确提供。connection public_config中的resolution/quality（兼容toapis_resolution/toapis_quality）冻结进入图片模型参数和summary；实际调用使用冻结值，不能登记2K却硬编码1K。旧连接省略时继续1K/low，旧作品和请求不重发。原下述1K选择保留为历史/旧连接规则。请求尺寸、参考图接口与实际返回尺寸依提供方合同核验，不从模型名称猜网关。

2026-10-12；HPS-015/017/026—030。用户指定gpt-image-2.5-flare-vip、low、1K。

应用HTML设计图沿用共享1K比例映射1280×720（16:9，约0.92MP），独立透明主体默认1024×1024。
1024×576的实际请求被供应商HTTP400拒绝；不将未经验证的长边1024理解为支持的1K横屏尺寸。
ToAPIs 2.5 VIP传实际像素size、quality=low、不传resolution；旧比例协议默认1k/low。
兼容端2.5的resolution提示同步1K。请求参数、实际返回宽高分别记录；提示不代表实际尺寸通过。
旧任务保留原配置/图片，不自动重发。新配置使候选输入身份变化；视觉批准与正式交付另验。
验证必须读取当前创作配置的模型绑定，不能用旧全局连接代替；凭据只在私有调用边界读取。

2026-10-14 ToAPIs Official生产协议核验（HPS-015/017/026—030）：用户明确接口https://api.toapis.com/v1/images/generations，连接可保存根地址或/v1，适配器只追加一次/v1。官方生产文档https://docs.toapis.com/docs/cn/api-reference/images/gpt-image-2.5-official/generation.md规定official使用像素size、quality和image_urls，不沿用普通版reference_images或playground metadata比例提示。HTML按冻结分辨率长边映射且16像素对齐，2K横屏2048x1152、方形2048x2048；旧VIP/普通版参数保持。上传真实参考后仅提交一次，持久上游ID并查原任务，实际输出尺寸另验。无作者Schema/Agent/DB变更。

2026-10-14 用户明确选择：整页设计2K/low，独立透明主体保持1024x1024/low，素材400万像素门禁保持。Official的连接分辨率默认只映射整页设计，不覆盖透明主体的显式像素size；独立素材请求日志记录实际1K。已返回2048方形原图作为失败证据保留，不裁改账本、不自动缩放或伪称复用成功。

传输策略修复后的设计复用仅限一个明确有返回回执的已验证候选：文章/修订/模型/计划/参考包/设计图散列均不变，原生成快照完整且差异恰好为已审计html_image_provider.py尺寸分工修复时，可经专用维护脚本创建新定义身份候选并保留from_key及快照证据。旧候选和任务不改写；未知结果、其他源/定义变化或资源损坏拒绝。不是原任务恢复，不转移最终批准；新生产仍经原produce及全部门禁。HPS-015/017/028/030。
