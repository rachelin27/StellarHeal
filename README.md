<p align="center">
  <img src="StellarHeal/resources/logo.png" width="104" alt="星愈：青绿色双臂环抱金色星光" />
</p>

<h1 align="center">星愈 · StellarHeal</h1>

<p align="center">给心情，一个停靠的地方。</p>

基于 **Streamlit + DeepSeek** 的情绪陪伴应用。支持流式对话、角色定制、历史会话管理和本地保存，帮助用户梳理感受、记录交流。它是情绪支持工具，不能替代专业诊疗。

## 当前功能

<table>
<thead>
<tr><th width="160">功能</th><th>说明</th></tr>
</thead>
<tbody>
<tr><td>流式对话</td><td>逐步显示模型回复，可调整上下文记忆长度和回复创造性</td></tr>
<tr><td>陪伴角色</td><td>提供温暖倾听者、专业咨询师、成长导师、正能量朋友，也可自定义身份与性格</td></tr>
<tr><td>会话管理</td><td>新建、切换、重命名、单条删除、批量删除和 JSON 导出</td></tr>
<tr><td>标题生成</td><td>完成两轮对话后自动为未命名会话生成标题，也可手动命名或点击「生成一次」</td></tr>
<tr><td>本地保存</td><td>自动保存与自动标题独立控制，支持手动保存</td></tr>
<tr><td>操作反馈</td><td>删除只统计实际成功数量，刷新后仍可看到失败原因</td></tr>
<tr><td>界面</td><td>暖白与浅绿配色、欢迎引导、折叠设置和窄屏布局；标签页与左上角统一使用透明底「星光拥抱」图标</td></tr>
</tbody>
</table>

## 快速开始

需要 **Python 3.10 或以上**，以及可用的 DeepSeek API Key。以下命令适用于 Windows PowerShell：

~~~powershell
git clone https://github.com/rachelin27/StellarHeal.git
cd StellarHeal

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

$env:DEEPSEEK_API_KEY = "你的 DeepSeek API Key"
.\.venv\Scripts\python.exe -m streamlit run StellarHeal/04_system_upgrade.py
~~~

如果已经下载项目，进入本 README 所在目录后，从创建虚拟环境那一步开始即可。

浏览器访问 [http://localhost:8501](http://localhost:8501)，终端按 Ctrl+C 停止。环境变量仅对当前 PowerShell 窗口及其启动的进程生效；打开新窗口时需要重新设置。请勿把真实 API Key 写进代码或提交到仓库。

## 标题与保存规则

- **自动生成标题开启**：完成两轮对话后，为仍未命名的会话生成一次标题；已有名称不会被自动替换。
- **自动生成标题关闭**：保存和切换会话不会触发标题生成，仍可主动点击「生成一次」。
- **生成一次 / 更新标题**：主动生成或修改当前标题，并保存该会话，即使自动保存已关闭。
- **自动保存开启**：会话内容或相关信息发生变化时保存到磁盘。
- **自动保存关闭**：自动标题仍可生成，但不会因此自动落盘；新建、切换或关闭页面前，请手动保存或导出。

会话存放在 StellarHeal/sessions/，以未加密的 JSON 文件保存，目录位置不随启动路径改变。保存时先写临时文件，再替换目标文件，降低写入失败时破坏旧记录的风险。

## 数据与使用边界

- 对话会发送到 **DeepSeek** 生成回复；自动或手动生成标题时，也会发送相关用户消息。
- 「本地保存」指记录存放在**运行 Streamlit 服务的电脑**上，不代表模型请求完全离线。
- 当前面向个人本地使用，尚无账号和用户存储隔离，不适合直接作为多人共享服务部署。
- 删除记录暂不支持撤销或回收站，重要内容请先导出。
- 聊天记录、API Key 配置和测试日志不应提交到 GitHub，相关路径已加入 .gitignore。

已知问题与后续改进见 [项目检查记录](PROJECT_REVIEW.md)，包括双标签页会话冲突、异常历史文件校验和网络中断恢复等边界。

## 测试

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
~~~

目前包含 **13 项回归测试**，使用模拟模型接口和独立临时目录，不产生模型调用费用，也不修改已有会话。覆盖标题开关、生成门槛、保存、手动命名、会话切换、角色同步，以及单条和批量删除的成功、部分失败、全部失败等场景。

最近一次验证环境：Python 3.14.2、Streamlit 1.54.0、OpenAI SDK 2.17.0。测试通过不代表真实模型响应质量、网络故障或多人并发已经全部验证。

## 项目结构与开发阶段

~~~text
StellarHeal/
├── .streamlit/config.toml                   # 页面主题
├── StellarHeal/
│   ├── 01_page_setup_and_interaction.py     # 阶段 1：基础页面与对话
│   ├── 02_sidebar_function_extension.py     # 阶段 2：角色与侧栏
│   ├── 03_conversation_history_extension.py # 阶段 3：历史会话
│   ├── 04_system_upgrade.py                 # 当前完整应用入口
│   ├── deepseek_api_test.py                 # 真实 API 连通性示例
│   └── resources/logo.png                  # 透明底应用图标
├── tests/test_sessions.py                   # 隔离回归测试
├── requirements.txt
└── PROJECT_REVIEW.md
~~~

01–03 保留为开发阶段示例；日常使用和本次修复均以 04_system_upgrade.py 为准。deepseek_api_test.py 会调用真实服务，请仅在需要检查 API 连通性时单独运行。
