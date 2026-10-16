# 第一阶段：本机运行基线 · 2026-10-16

## 已完成

当前开发目录为 `D:/software/PPT_HTML_Studio`，启动前8010无监听，旧开发进程已退出。发现另一便携版进程，本轮未修改、停止或使用它；没有新建运行副本。历史文档所写 `D:/Program Files (x86)/PPT_HTML_Studio` 在本机不存在，本轮使用会话指定且含实际源码/数据的工作目录。

先以只读SQLite核实无queued/running/pending/submitted任务，备份数据库、记录运行文件SHA，再通过当前虚拟环境隐藏启动 `start_server.py`，显式绑定127.0.0.1:8010、当前data/projects.db与runs。未执行模型、配音、导出或项目修改。

## 发现并修正

HTTP逐文件校验发现 `api_client.js` 未携带禁缓存头：中间件使用startsWith('/api')，误把此静态文件当成API。已改为精确 `/api` 或 `/api/` 命名空间，9项缓存/组合根回归通过。确认任务为空后再次替换开发服务，未停止其他应用。

## 验收证据

- 当前HTTP meta：Agent API1.37.0、合同hash5422019d6913801a；源码合同包0.9.57。
- index.html、html_review_panel.js、storyboard.js、api_client.js、stitch.css：HTTP字节与磁盘一致，全部no-store。
- 四个阶段Skill加载器校验正文/引用hash：容量修复0.1.0，设计理解/还原/保真审核0.3.0。本轮没有生产请求，因此不是四次模型实际执行证明。
- static_html预检ready=true，使用本机Edge，字体检查通过；未测试供应商连接。
- 真实浏览器首页加载49个外部脚本，pageErrors=0，非读取请求=0，并保存首页截图。
- 启动前后2个项目、1959个运行文件内容未变，数据库10张表记录未变，active_jobs=0。

本地证据在ignored `outputs/local-baseline-20261016/`：数据库备份、before.json、source-baseline.json、preflight.json、HTTP/Skill核对、browser.json、home.png、data-integrity.json及启动日志。数据库和运行证据不得提交。最终源码清单另存source-baseline-final.json；当前工作树未提交，不冒充远程发布版本。

## 下一阶段

第一阶段完成。下一步开发“讲稿待核对候选保留 → 原句对照 → 课程等待用户 → 修正保存 → 正确阶段继续”的闭环。原未知请求继续保留，不能因本机启动成功重发；真实模型质量和全链路仍未验证。
