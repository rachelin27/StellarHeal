import streamlit as st
import os
from openai import OpenAI
import datetime
import json
import time
from typing import List, Dict, Optional

# 设置页面的配置项
st.set_page_config(
    page_title="星愈-您的智能心理服务助手",
    page_icon="🌌",
    # 布局
    layout="wide",
    # 控制的是侧边栏的状态
    initial_sidebar_state="expanded",
    menu_items={}
)


# 生成会话记录的函数
def generate_session_record():
    return datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")


# 生成会话标题的函数
def generate_session_title(messages: List[Dict], client: OpenAI) -> str:
    """基于对话内容生成有意义的标题"""
    try:
        if not messages:
            return "新的对话"

        # 提取对话的前几条消息作为标题生成的依据
        user_messages = [msg["content"] for msg in messages if msg["role"] == "user"][:3]

        if not user_messages:
            return "新的对话"

        # 构建标题生成提示
        title_prompt = f"""请根据以下对话内容生成一个简洁的标题（不超过10个字）：

对话内容：
{chr(10).join([f"用户: {msg}" for msg in user_messages])}

请生成一个能概括对话主题的简短标题，格式为：主题摘要。例如：
- 工作压力大感到焦虑 → 工作压力疏导
- 睡眠不好经常失眠 → 睡眠质量改善
- 和同事关系紧张 → 人际关系调节
- 对未来感到迷茫 → 未来规划咨询

标题："""

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个标题生成助手，能根据对话内容生成简洁准确的标题。"},
                {"role": "user", "content": title_prompt}
            ],
            max_tokens=20,
            temperature=0.3
        )

        title = response.choices[0].message.content.strip()
        # 清理标题，移除可能的标点
        title = title.replace("标题：", "").replace("标题:", "").strip()
        title = title.replace("。", "").replace(".", "").replace("！", "").replace("!", "")

        # 如果标题太长，截断
        if len(title) > 12:
            title = title[:10] + "..."

        return title or "心理咨询对话"

    except Exception as e:
        print(f"生成标题失败: {e}")
        # 如果生成失败，使用第一条消息的前几个字
        for msg in messages:
            if msg["role"] == "user" and msg["content"]:
                content = msg["content"].strip()
                if len(content) > 15:
                    return content[:12] + "..."
                return content[:15]
        return "新的对话"


# 美化会话名称显示
def format_session_display(session_data: Dict) -> str:
    """美化会话显示，包含时间和标题"""
    try:
        session_name = session_data.get("session_name", "")
        title = session_data.get("title", "")

        # 尝试解析时间格式
        dt = datetime.datetime.strptime(session_name, "%Y-%m-%d %H-%M-%S")
        time_str = dt.strftime("%m/%d %H:%M")

        if title and title != "新的对话":
            return f"{time_str} | {title}"
        else:
            return time_str
    except:
        return session_name[:15] + "..."


# 添加上下文摘要功能
def generate_context_summary(messages: List[Dict], max_length: int = 3) -> str:
    """生成简短的对话上下文摘要"""
    if not messages or len(messages) <= 1:
        return "这是对话的开始"

    summary = []
    # 只取最近的消息
    recent_msgs = messages[-max_length:] if len(messages) > max_length else messages

    for msg in recent_msgs:
        role = "用户" if msg["role"] == "user" else "助手"
        # 截取前30个字符作为摘要
        content_preview = msg["content"][:30] + "..." if len(msg["content"]) > 30 else msg["content"]
        summary.append(f"{role}: {content_preview}")

    return " | ".join(summary)


# 保存会话记录的函数
def save_session_record(auto: bool = True, force_title_generation: bool = False) -> None:
    """保存会话记录，支持自动生成标题"""
    if not auto or (auto and st.session_state.get('auto_save', True)):
        # 1. 保存当前会话信息
        if st.session_state.current_session and st.session_state.messages:

            # 检查是否需要生成标题
            if ('session_title' not in st.session_state or
                    not st.session_state.session_title or
                    st.session_state.session_title == "新的对话" or
                    force_title_generation):

                # 创建OpenAI客户端用于生成标题
                try:
                    client = OpenAI(
                        api_key=os.environ.get('DEEPSEEK_API_KEY'),
                        base_url="https://api.deepseek.com"
                    )

                    # 只有在有足够内容时才生成标题
                    if len(st.session_state.messages) >= 2:
                        title = generate_session_title(st.session_state.messages, client)
                        st.session_state.session_title = title
                    else:
                        st.session_state.session_title = "新的对话"

                except Exception as e:
                    print(f"生成标题时出错: {e}")
                    st.session_state.session_title = "新的对话"

            # 构建新的会话对象
            session_data = {
                "nick_name": st.session_state.nick_name,
                "nature": st.session_state.nature,
                "current_session": st.session_state.current_session,
                "messages": st.session_state.messages,
                "title": st.session_state.get('session_title', '新的对话'),
                "session_name": st.session_state.current_session,  # 保存原始会话名
                "save_time": datetime.datetime.now().isoformat(),
                "message_count": len(st.session_state.messages),
                "user_msg_count": len([m for m in st.session_state.messages if m["role"] == "user"])
            }

            # 如果 sessions 目录不存在，则创建
            if not os.path.exists("sessions"):
                os.makedirs("sessions", exist_ok=True)

            # 保存会话数据
            try:
                session_file = f"sessions/{st.session_state.current_session}.json"
                with open(session_file, "w", encoding="utf-8") as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2)
                print(f"会话已保存: {session_file}")
            except Exception as e:
                st.error(f"保存会话失败: {str(e)}")


# 加载所有的会话列表信息
def load_sessions() -> List[Dict]:
    """加载所有会话的信息"""
    session_list = []
    # 加载sessions目录下的文件
    if os.path.exists("sessions"):
        file_list = os.listdir("sessions")
        for filename in file_list:
            # 截取符合条件的文件名
            if filename.endswith(".json"):
                try:
                    with open(f"sessions/{filename}", "r", encoding="utf-8") as f:
                        session_data = json.load(f)
                        # 确保包含必要字段
                        if "session_name" not in session_data:
                            session_data["session_name"] = filename[:-5]
                        if "title" not in session_data:
                            session_data["title"] = "新的对话"
                        session_list.append(session_data)
                except Exception as e:
                    print(f"加载会话文件 {filename} 失败: {e}")

    # 按时间倒序排序
    session_list.sort(key=lambda x: x.get("session_name", ""), reverse=True)
    return session_list


# 加载指定的会话信息
def load_session(session_name: str) -> None:
    """加载指定会话"""
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            # 读取会话数据
            with open(f"sessions/{session_name}.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)
                st.session_state.messages = session_data.get("messages", [])
                st.session_state.nick_name = session_data.get("nick_name", "心理医生")
                st.session_state.nature = session_data.get("nature", "专业，耐心，和善")
                st.session_state.current_session = session_name
                st.session_state.session_title = session_data.get("title", "新的对话")
    except Exception as e:
        st.error(f"加载会话失败: {str(e)}")


# 删除会话
def delete_session(session_name: str) -> None:
    """删除指定会话"""
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            os.remove(f"sessions/{session_name}.json")
            # 如果删除的是当前对话，则需要清空页面并创建新会话
            if st.session_state.current_session == session_name:
                st.session_state.messages = []
                st.session_state.current_session = generate_session_record()
                st.session_state.session_title = "新的对话"
                st.success("已删除当前会话，创建了新会话")
    except Exception as e:
        st.error(f"删除会话失败: {str(e)}")


# 更新会话标题
def update_session_title(session_name: str, new_title: str) -> None:
    """更新会话标题"""
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            with open(f"sessions/{session_name}.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)

            session_data["title"] = new_title

            with open(f"sessions/{session_name}.json", "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            # 如果是当前会话，更新session state
            if st.session_state.current_session == session_name:
                st.session_state.session_title = new_title

    except Exception as e:
        st.error(f"更新标题失败: {str(e)}")


# 系统提示词模板
system_prompt_template = '''你是一位性格 {nature} 的 {role}，请保持自然轻松的交流风格。

**角色设定：**
- 身份：{role}
- 性格：{nature}
- 专业背景：具备心理学专业知识
- 交流风格：温暖、共情、不评价

**咨询框架（请自然融入对话中）：**
1. 共情回应：先确认并接纳用户的情绪
2. 开放提问：引导用户表达感受
3. 方法建议：提供简易的认知调整方法
4. 实践练习：给予具体可操作的放松技巧
5. 赋能鼓励：用温暖的语言收尾

**注意事项：**
- 避免使用专业术语让人感到压力
- 保持对话流畅自然
- 一次对话聚焦一个核心问题
- 根据用户情绪状态调整回应强度

**当前对话上下文：{context_summary}**

请基于以上设定与用户进行交流。'''

# 初始化session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# 默认人物身份和性格
if "nick_name" not in st.session_state:
    st.session_state.nick_name = "心理辅导员"

if "nature" not in st.session_state:
    st.session_state.nature = "专业，耐心，和善"

if "current_session" not in st.session_state:
    st.session_state.current_session = generate_session_record()

if "session_title" not in st.session_state:
    st.session_state.session_title = "新的对话"

if "auto_save" not in st.session_state:
    st.session_state.auto_save = True

if "context_length" not in st.session_state:
    st.session_state.context_length = 10

if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7

# 大标题
st.title("🌌 星愈 - 您的智能心理服务助手")

# Logo
st.logo("resources/logo.png")

# 状态栏
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.caption(f"👤 {st.session_state.nick_name}")
with col2:
    st.caption(f"🎭 {st.session_state.nature[:10]}...")
with col3:
    user_msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.caption(f"💬 对话: {user_msg_count} 条")
with col4:
    display_title = st.session_state.session_title if st.session_state.session_title != "新的对话" else "新对话"
    st.caption(f"🏷️ {display_title}")

# 会话标题编辑（在对话区域上方）
if st.session_state.messages and len(st.session_state.messages) >= 2:
    col_title1, col_title2, col_title3 = st.columns([3, 1, 1])
    with col_title1:
        current_title = st.text_input(
            "会话标题",
            value=st.session_state.session_title,
            key="title_editor",
            placeholder="输入会话标题..."
        )
    with col_title2:
        if st.button("💾 更新", key="update_title_btn", use_container_width=True):
            if current_title and current_title != st.session_state.session_title:
                update_session_title(st.session_state.current_session, current_title)
                st.session_state.session_title = current_title
                st.success("标题已更新")
                st.rerun()
    with col_title3:
        if st.button("🤖 自动生成", key="auto_title_btn", use_container_width=True):
            with st.spinner("正在生成标题..."):
                try:
                    client = OpenAI(
                        api_key=os.environ.get('DEEPSEEK_API_KEY'),
                        base_url="https://api.deepseek.com"
                    )
                    new_title = generate_session_title(st.session_state.messages, client)
                    update_session_title(st.session_state.current_session, new_title)
                    st.session_state.session_title = new_title
                    st.success(f"标题已更新为: {new_title}")
                    st.rerun()
                except Exception as e:
                    st.error(f"生成标题失败: {e}")

# 展示聊天记录
for message in st.session_state.messages:
    st.chat_message(message["role"]).write(message["content"])

# 左侧的侧边栏
with st.sidebar:
    st.subheader("🧠 AI控制面板")

    # 预设角色
    st.markdown("#### 🎭 预设角色")
    preset_roles = {
        "🤗 温暖倾听者": {"name": "倾听伙伴", "nature": "温暖、耐心、善于倾听"},
        "🎯 专业咨询师": {"name": "心理咨询师", "nature": "专业、理性、引导式"},
        "🌱 成长导师": {"name": "成长导师", "nature": "鼓励、启发、赋能"},
        "😊 正能量朋友": {"name": "好朋友", "nature": "开朗、乐观、支持性"}
    }

    for emoji, role_info in preset_roles.items():
        if st.button(f"{emoji} {role_info['name']}",
                     key=f"preset_{role_info['name']}",
                     use_container_width=True):
            st.session_state.nick_name = role_info["name"]
            st.session_state.nature = role_info["nature"]
            st.success(f"已切换为 {role_info['name']} 角色")
            st.rerun()

    st.divider()

    # 会话管理
    st.markdown("#### 📁 历史会话")

    # 新建会话按钮
    if st.button("🆕 新建会话", use_container_width=True, icon="✏️"):
        save_session_record()
        if st.session_state.messages:
            st.session_state.current_session = generate_session_record()
            st.session_state.messages = []
            st.session_state.session_title = "新的对话"
            save_session_record()
            st.success("已创建新会话")
            st.rerun()

    # 会话列表
    session_data_list = load_sessions()

    if not session_data_list:
        st.info("暂无历史会话")
    else:
        for session_data in session_data_list:
            display_text = format_session_display(session_data)
            session_name = session_data.get("session_name", "")
            title = session_data.get("title", "")

            # 使用卡片式布局
            with st.container():
                col1, col2, col3 = st.columns([6, 1, 1])

                with col1:
                    # 显示带标题的会话
                    is_current = session_name == st.session_state.current_session
                    btn_type = "primary" if is_current else "secondary"

                    if st.button(
                            f"💬 {display_text}",
                            key=f"load_{session_name}",
                            use_container_width=True,
                            type=btn_type
                    ):
                        load_session(session_name)
                        st.rerun()

                with col2:
                    # 编辑标题按钮
                    if st.button(
                            "✏️",
                            key=f"edit_{session_name}",
                            help="编辑标题"
                    ):
                        st.session_state[f"editing_{session_name}"] = True

                with col3:
                    # 删除按钮
                    if st.button(
                            "🗑️",
                            key=f"delete_{session_name}",
                            help="删除此会话"
                    ):
                        delete_session(session_name)
                        st.rerun()

                # 编辑标题的输入框
                if st.session_state.get(f"editing_{session_name}"):
                    edit_col1, edit_col2 = st.columns([3, 1])
                    with edit_col1:
                        new_title = st.text_input(
                            "新标题",
                            value=title,
                            key=f"edit_input_{session_name}",
                            placeholder="输入新标题..."
                        )
                    with edit_col2:
                        if st.button("💾", key=f"save_edit_{session_name}"):
                            if new_title and new_title != title:
                                update_session_title(session_name, new_title)
                                st.success("标题已更新")
                                st.session_state[f"editing_{session_name}"] = False
                                st.rerun()
                        if st.button("❌", key=f"cancel_edit_{session_name}"):
                            st.session_state[f"editing_{session_name}"] = False
                            st.rerun()

    st.divider()

    # 批量管理会话
    with st.expander("⚙️ 批量管理", expanded=False):
        if session_data_list:
            # 创建选项列表用于多选
            session_options = {
                format_session_display(sd): sd.get("session_name", "")
                for sd in session_data_list
            }

            selected_display = st.multiselect(
                "选择要删除的会话",
                list(session_options.keys())
            )

            if selected_display:
                selected_sessions = [session_options[display] for display in selected_display]

                if st.button("🗑️ 批量删除选中会话",
                             type="secondary",
                             use_container_width=True):
                    for session_name in selected_sessions:
                        delete_session(session_name)
                    st.success(f"已删除 {len(selected_sessions)} 个会话")
                    st.rerun()

        # 导出当前会话
        if st.session_state.messages:
            session_data = {
                "nick_name": st.session_state.nick_name,
                "nature": st.session_state.nature,
                "current_session": st.session_state.current_session,
                "messages": st.session_state.messages,
                "title": st.session_state.session_title,
                "session_name": st.session_state.current_session,
                "export_time": datetime.datetime.now().isoformat(),
                "message_count": len(st.session_state.messages)
            }

            st.download_button(
                label="📤 导出当前会话",
                data=json.dumps(session_data, ensure_ascii=False, indent=2),
                file_name=f"星愈会话_{st.session_state.current_session}_{st.session_state.session_title}.json",
                mime="application/json",
                use_container_width=True
            )

    st.divider()

    # 自定义设置
    st.markdown("#### 🎛️ 自定义设置")

    # 自定义身份和性格
    nick_name = st.text_input("身份名称",
                              value=st.session_state.nick_name,
                              placeholder="请输入身份（如：心理辅导员、倾听者等）",
                              key="nick_name_input")
    if nick_name and nick_name != st.session_state.nick_name:
        st.session_state.nick_name = nick_name

    nature = st.text_area("性格描述",
                          value=st.session_state.nature,
                          placeholder="请输入性格特点（如：温暖、耐心、专业等）",
                          key="nature_input",
                          height=100)
    if nature and nature != st.session_state.nature:
        st.session_state.nature = nature

    # 对话设置
    st.markdown("##### ⚙️ 对话设置")

    auto_save = st.toggle("💾 自动保存会话",
                          value=st.session_state.auto_save,
                          key="auto_save_toggle")
    st.session_state.auto_save = auto_save

    # 自动生成标题设置
    auto_title = st.toggle("🏷️ 自动生成标题",
                           value=st.session_state.get('auto_title', True),
                           key="auto_title_toggle",
                           help="对话达到一定长度后自动生成标题")
    st.session_state.auto_title = auto_title

    context_length = st.slider("📊 上下文记忆长度",
                               5, 20, st.session_state.context_length,
                               help="控制AI记忆的对话轮数")
    st.session_state.context_length = context_length

    temperature = st.slider("✨ 回复创造性",
                            0.1, 1.0, st.session_state.temperature, 0.1,
                            help="值越高回复越有创造性")
    st.session_state.temperature = temperature

    st.divider()

    # 对话统计
    if st.session_state.messages:
        with st.expander("📈 对话统计", expanded=False):
            user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
            assistant_msgs = [m for m in st.session_state.messages if m["role"] == "assistant"]

            col_stat1, col_stat2 = st.columns(2)
            with col_stat1:
                st.metric("👤 用户发言", len(user_msgs))
            with col_stat2:
                st.metric("🤖 助手回复", len(assistant_msgs))

            # 计算平均回复长度
            if assistant_msgs:
                avg_length = sum(len(m["content"]) for m in assistant_msgs) / len(assistant_msgs)
                st.metric("📏 平均回复长度", f"{avg_length:.0f} 字符")

            # 统计字符总数
            total_chars = sum(len(m["content"]) for m in st.session_state.messages)
            st.metric("🔤 总字符数", f"{total_chars:,}")

            # 会话开始时间
            if st.session_state.messages:
                try:
                    # 从会话名解析时间
                    dt = datetime.datetime.strptime(st.session_state.current_session, "%Y-%m-%d %H-%M-%S")
                    st.caption(f"⏰ 开始时间: {dt.strftime('%Y-%m-%d %H:%M')}")
                except:
                    pass

# 主界面
# 消息输入框
prompt = st.chat_input("💭 请告诉我您今天的感觉如何...")

if prompt:
    # 显示用户消息
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 生成上下文摘要
    context_summary = generate_context_summary(st.session_state.messages)

    # 准备系统提示词
    system_prompt = system_prompt_template.format(
        nature=st.session_state.nature,
        role=st.session_state.nick_name,
        context_summary=context_summary
    )

    # 创建与AI大模型交互的客户端对象
    client = OpenAI(
        api_key=os.environ.get('DEEPSEEK_API_KEY'),
        base_url="https://api.deepseek.com")

    # 控制上下文长度
    messages_for_api = []
    if len(st.session_state.messages) > st.session_state.context_length * 2:
        # 保留系统提示词和最近的消息
        messages_for_api = [
                               {"role": "system", "content": system_prompt}
                           ] + st.session_state.messages[-st.session_state.context_length * 2:]
    else:
        messages_for_api = [
                               {"role": "system", "content": system_prompt}
                           ] + st.session_state.messages

    # 显示加载状态
    with st.spinner(f"{st.session_state.nick_name} 正在思考中..."):
        try:
            # 与AI大模型交互
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages_for_api,
                temperature=st.session_state.temperature,
                stream=True
            )

            # 流式输出
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""

                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        # 添加打字机效果
                        message_placeholder.markdown(full_response + "▌")
                        time.sleep(0.01)  # 轻微延迟，让打字效果更自然

                # 完成时移除光标
                message_placeholder.markdown(full_response)

            # 保存助手回复
            st.session_state.messages.append({"role": "assistant", "content": full_response})

            # 检查是否需要自动生成标题
            should_generate_title = (
                    st.session_state.get('auto_title', True) and
                    st.session_state.session_title == "新的对话" and
                    len(st.session_state.messages) >= 4  # 至少有2轮对话
            )

            # 自动保存会话，如果需要则生成标题
            save_session_record(force_title_generation=should_generate_title)

        except Exception as e:
            st.error(f"请求失败: {str(e)}")
            st.info("请检查网络连接或稍后重试")

            # 添加错误消息到对话历史
            error_message = "抱歉，我遇到了一些技术问题暂时无法回应。这可能是网络连接问题，请稍后再试。"
            st.chat_message("assistant").write(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})

            # 仍然尝试保存会话
            save_session_record()

# 页面底部信息
st.divider()
st.caption("💡 提示：您可以随时在侧边栏切换AI角色、管理会话或调整对话设置")
st.caption("🔒 您的对话记录仅保存在本地，请放心分享您的感受")

# 页面加载时检查是否有未保存的更改
if st.session_state.get('_last_save_hash') != hash(json.dumps(st.session_state.messages, default=str)):
    st.session_state['_last_save_hash'] = hash(json.dumps(st.session_state.messages, default=str))
    if st.session_state.auto_save and st.session_state.messages:
        # 检查是否需要生成标题
        force_title = (
                st.session_state.get('auto_title', True) and
                st.session_state.session_title == "新的对话" and
                len(st.session_state.messages) >= 4
        )

        # 异步保存，避免阻塞
        import threading


        def async_save():
            save_session_record(force_title_generation=force_title)


        thread = threading.Thread(target=async_save)
        thread.daemon = True
        thread.start()