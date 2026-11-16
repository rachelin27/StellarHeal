import streamlit as st
import os
from openai import OpenAI
import datetime
import json
import tempfile
from pathlib import Path
from typing import List, Dict

APP_DIR = Path(__file__).resolve().parent
SESSION_DIR = APP_DIR / "sessions"

# 按钮提前 rerun 时仍保留设置，避免未渲染的控件状态被 Streamlit 清理。
for setting in ("auto_title", "auto_save", "nick_name", "nature"):
    if setting in st.session_state:
        st.session_state[setting] = st.session_state[setting]

# 设置页面的配置项
st.set_page_config(
    page_title="星愈-您的智能心理服务助手",
    page_icon=str(APP_DIR / "resources" / "logo.png"),
    # 布局
    layout="wide",
    # 控制的是侧边栏的状态
    initial_sidebar_state="auto",
    menu_items={}
)


# 生成会话记录的函数
def generate_session_record():
    name = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    while name == st.session_state.get("current_session") or (SESSION_DIR / f"{name}.json").exists():
        name = (datetime.datetime.strptime(name, "%Y-%m-%d %H-%M-%S") +
                datetime.timedelta(seconds=1)).strftime("%Y-%m-%d %H-%M-%S")
    return name


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


def maybe_generate_session_title() -> None:
    """自动标题只受标题开关控制，与是否保存到磁盘无关。"""
    messages = st.session_state.messages
    if (not st.session_state.auto_title or
            st.session_state.session_title not in ("", "新的对话") or
            not messages or messages[-1]["role"] != "assistant" or
            sum(m["role"] == "user" for m in messages) < 2 or
            sum(m["role"] == "assistant" for m in messages) < 2 or
            not os.environ.get("DEEPSEEK_API_KEY")):
        return
    try:
        client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"),
                        base_url="https://api.deepseek.com")
        st.session_state.session_title = generate_session_title(messages, client)
    except Exception as e:
        print(f"生成标题时出错: {e}")


def write_session_data(session_name: str, session_data: Dict) -> None:
    """先完整写入临时文件，避免写入失败时破坏已有记录。"""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=SESSION_DIR,
                                         suffix=".tmp", delete=False) as f:
            temp_path = Path(f.name)
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, SESSION_DIR / f"{session_name}.json")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def save_session_record(auto: bool = True) -> bool:
    """保存记录；自动保存不会触发标题生成。"""
    if auto and not st.session_state.auto_save:
        return False
    if not st.session_state.current_session or not st.session_state.messages:
        return False
    session_data = {
        "nick_name": st.session_state.nick_name,
        "nature": st.session_state.nature,
        "current_session": st.session_state.current_session,
        "messages": st.session_state.messages,
        "title": st.session_state.session_title,
        "session_name": st.session_state.current_session,
        "message_count": len(st.session_state.messages),
        "user_msg_count": sum(m["role"] == "user" for m in st.session_state.messages)
    }
    snapshot = json.dumps(session_data, ensure_ascii=False, sort_keys=True)
    if auto and snapshot == st.session_state.get("_last_saved_snapshot"):
        return True
    session_data["save_time"] = datetime.datetime.now().isoformat()
    try:
        write_session_data(st.session_state.current_session, session_data)
        st.session_state._last_saved_snapshot = snapshot
        return True
    except Exception as e:
        st.error(f"保存会话失败: {str(e)}")
        return False


# 加载所有的会话列表信息
def load_sessions() -> List[Dict]:
    """加载所有会话的信息"""
    session_list = []
    # 加载sessions目录下的文件
    if SESSION_DIR.exists():
        file_list = os.listdir(SESSION_DIR)
        for filename in file_list:
            # 截取符合条件的文件名
            if filename.endswith(".json"):
                try:
                    with open(SESSION_DIR / filename, "r", encoding="utf-8") as f:
                        session_data = json.load(f)
                        # 确保包含必要字段
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
        if (SESSION_DIR / f"{session_name}.json").exists():
            # 读取会话数据
            with open(SESSION_DIR / f"{session_name}.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)
                st.session_state.messages = session_data.get("messages", [])
                st.session_state.nick_name = session_data.get("nick_name", "心理医生")
                st.session_state.nature = session_data.get("nature", "专业，耐心，和善")
                st.session_state.current_session = session_name
                st.session_state.session_title = session_data.get("title", "新的对话")
    except Exception as e:
        st.error(f"加载会话失败: {str(e)}")


# 删除会话
def delete_session(session_name: str) -> bool:
    """返回删除结果，将失败原因保留至页面刷新后显示。"""
    try:
        (SESSION_DIR / f"{session_name}.json").unlink()
        # 如果删除的是当前对话，则需要清空页面并创建新会话
        if st.session_state.current_session == session_name:
            st.session_state.messages = []
            st.session_state.current_session = generate_session_record()
            st.session_state.session_title = "新的对话"
        return True
    except Exception as e:
        st.session_state.setdefault("_delete_errors", []).append(f"删除会话 {session_name} 失败: {e}")
        return False


# 更新会话标题
def update_session_title(session_name: str, new_title: str) -> bool:
    """更新会话标题"""
    new_title = new_title.strip()
    if not new_title:
        st.warning("标题不能为空")
        return False
    try:
        if st.session_state.current_session == session_name:
            previous_title = st.session_state.session_title
            st.session_state.session_title = new_title
            if not save_session_record(auto=False):
                st.session_state.session_title = previous_title
                return False
            return True
        if (SESSION_DIR / f"{session_name}.json").exists():
            with open(SESSION_DIR / f"{session_name}.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)

            session_data["title"] = new_title

            write_session_data(session_name, session_data)
            return True
        st.error("未找到会话，标题未保存")
    except Exception as e:
        st.error(f"更新标题失败: {str(e)}")
    return False


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

if "auto_title" not in st.session_state:
    st.session_state.auto_title = True

if "context_length" not in st.session_state:
    st.session_state.context_length = 10

if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7

st.markdown("""
<style>
.stMainBlockContainer { max-width: 960px; padding-top: 4.5rem; padding-bottom: 2rem; }
.st-key-welcome { background: linear-gradient(125deg, #eaf4ef, #f5f0e6);
    border: 1px solid #dce7df; border-radius: 22px; padding: 1.5rem 1.75rem; margin: 1rem 0; }
.st-key-welcome h3 { color: #284e45; font-weight: 600; }
[data-testid="stChatMessage"] { border: 1px solid var(--secondary-background-color);
    border-radius: 18px; padding: 1.1rem; margin-bottom: .75rem; }
[data-testid="stChatMessage"] p { line-height: 1.85; }
[data-testid="stSidebar"] button { border-radius: 10px; }
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button { padding-inline: .3rem; }
@media (max-width: 640px) {
    .stMainBlockContainer { padding-top: 4rem; }
    .st-key-welcome { padding: 1rem; }
}
</style>
""", unsafe_allow_html=True)

st.caption("STELLARHEAL · 星愈")
st.title("给心情，一个停靠的地方")
st.write("慢慢说，我在这里听。一起梳理此刻的感受，找到适合自己的小步伐。")

# Logo
st.logo(str(APP_DIR / "resources" / "logo.png"))

# 状态栏在窄屏上自然换行，避免四列堆叠占满首屏。
user_msg_count = sum(m["role"] == "user" for m in st.session_state.messages)
display_title = st.session_state.session_title if st.session_state.session_title != "新的对话" else "新对话"
st.caption(f"👤 {st.session_state.nick_name} · 💬 {user_msg_count} 条对话 · 🏷️ {display_title}")

# 会话标题编辑（在对话区域上方）
if st.session_state.messages and len(st.session_state.messages) >= 2:
    col_title1, col_title2, col_title3 = st.columns([3, 1, 1])
    with col_title1:
        current_title = st.text_input(
            "会话标题",
            value=st.session_state.session_title,
            key=f"title_editor_{st.session_state.current_session}_{st.session_state.session_title}",
            placeholder="输入会话标题..."
        )
    with col_title2:
        if st.button("💾 更新", key="update_title_btn", use_container_width=True):
            if current_title and current_title != st.session_state.session_title:
                if update_session_title(st.session_state.current_session, current_title):
                    st.rerun()
    with col_title3:
        if st.button("生成一次", key="auto_title_btn", use_container_width=True,
                     help="立即生成并保存标题，不受自动生成开关影响"):
            with st.spinner("正在生成标题..."):
                try:
                    client = OpenAI(
                        api_key=os.environ.get('DEEPSEEK_API_KEY'),
                        base_url="https://api.deepseek.com"
                    )
                    new_title = generate_session_title(st.session_state.messages, client)
                    if update_session_title(st.session_state.current_session, new_title):
                        st.rerun()
                except Exception as e:
                    st.error(f"生成标题失败: {e}")

# 展示聊天记录
if not st.session_state.messages:
    with st.container(key="welcome"):
        st.subheader("今天，想从哪里聊起？")
        st.write("可以是一件让你挂心的小事，也可以是暂时说不清的心情。这里不需要标准答案。")
        st.caption("比如：最近总是睡不好 · 今天有点累 · 想聊聊人际关系")

for message in st.session_state.messages:
    st.chat_message(message["role"]).write(message["content"])

# 左侧的侧边栏
with st.sidebar:
    st.subheader("🌿 你的陪伴空间")

    st.toggle("💾 自动保存会话", key="auto_save")
    st.toggle("🏷️ 自动生成标题", key="auto_title",
              help="完成两轮对话后，为尚未命名的会话生成一次标题；与自动保存开关独立。关闭后仍可点击「生成一次」。")
    if not st.session_state.auto_save:
        st.caption("自动保存已关闭。新建或切换前，请手动保存或导出当前会话。")
    if st.button("保存当前会话", key="save_session_btn", use_container_width=True,
                 disabled=not st.session_state.messages):
        if save_session_record(auto=False):
            st.rerun()

    with st.expander("🎭 选择陪伴角色", expanded=False):
        preset_roles = {
            "🤗 温暖倾听者": {"name": "倾听伙伴", "nature": "温暖、耐心、善于倾听"},
            "🎯 专业咨询师": {"name": "心理咨询师", "nature": "专业、理性、引导式"},
            "🌱 成长导师": {"name": "成长导师", "nature": "鼓励、启发、赋能"},
            "😊 正能量朋友": {"name": "好朋友", "nature": "开朗、乐观、支持性"}
        }
        for label, role_info in preset_roles.items():
            if st.button(label, key=f"preset_{role_info['name']}", use_container_width=True):
                st.session_state.nick_name = role_info["name"]
                st.session_state.nature = role_info["nature"]
                st.rerun()

    st.divider()

    # 会话管理
    st.markdown("#### 📁 历史会话")

    # 新建会话按钮
    if st.button("新建会话", use_container_width=True, icon="✏️", type="primary"):
        if st.session_state.auto_save and st.session_state.messages and not save_session_record():
            st.stop()
        if st.session_state.messages:
            st.session_state.current_session = generate_session_record()
            st.session_state.messages = []
            st.session_state.session_title = "新的对话"
            st.success("已创建新会话")
            st.rerun()

    deleted_count = st.session_state.pop("_deleted_count", 0)
    if deleted_count:
        st.success(f"已删除 {deleted_count} 个会话")
    for error in st.session_state.pop("_delete_errors", []):
        st.error(error)

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
                col1, col2, col3 = st.columns([4, 1, 1])

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
                        if st.session_state.auto_save and st.session_state.messages and not save_session_record():
                            st.stop()
                        load_session(session_name)
                        st.rerun()

                with col2:
                    # 编辑标题按钮
                    if st.button(
                            "✏️",
                            key=f"edit_{session_name}",
                            help="编辑标题", use_container_width=True
                    ):
                        st.session_state[f"editing_{session_name}"] = True

                with col3:
                    # 删除按钮
                    if st.button(
                            "🗑️",
                            key=f"delete_{session_name}",
                            help="删除此会话", use_container_width=True
                    ):
                        st.session_state._deleted_count = 1 if delete_session(session_name) else 0
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
                                if update_session_title(session_name, new_title):
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
            session_options = {sd["session_name"]: sd for sd in session_data_list}

            selected_sessions = st.multiselect(
                "选择要删除的会话",
                list(session_options),
                format_func=lambda name: format_session_display(session_options[name])
            )

            if selected_sessions:
                if st.button("🗑️ 批量删除选中会话",
                             type="secondary",
                             use_container_width=True):
                    st.session_state._deleted_count = sum(delete_session(name) for name in selected_sessions)
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
                file_name=f"星愈会话_{st.session_state.current_session}.json",
                mime="application/json",
                use_container_width=True
            )

    st.divider()

    # 自定义设置
    with st.expander("🎛️ 自定义与对话参数", expanded=False):
        st.text_input("身份名称", placeholder="请输入身份（如：心理辅导员、倾听者等）", key="nick_name")
        st.text_area("性格描述", placeholder="请输入性格特点（如：温暖、耐心、专业等）",
                     key="nature", height=100)
        context_length = st.slider("📊 上下文记忆长度", 5, 20, st.session_state.context_length,
                                   help="控制AI记忆的对话轮数")
        st.session_state.context_length = context_length
        temperature = st.slider("✨ 回复创造性", 0.1, 1.0, st.session_state.temperature, 0.1,
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
response_received = False

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
            if not os.environ.get("DEEPSEEK_API_KEY"):
                raise ValueError("请先设置 DEEPSEEK_API_KEY 环境变量，再重新启动应用")
            client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"),
                            base_url="https://api.deepseek.com")
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
                    if chunk.choices and chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        # 添加打字机效果
                        message_placeholder.markdown(full_response + "▌")

                # 完成时移除光标
                message_placeholder.markdown(full_response)

            # 保存助手回复
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            response_received = True

        except Exception as e:
            st.error(f"请求失败: {str(e)}")
            st.info("请检查网络连接或稍后重试")

# 页面底部信息
st.divider()
st.caption("💡 提示：您可以随时在侧边栏切换AI角色、管理会话或调整对话设置")
st.caption("🔒 对话会发送至 DeepSeek 以生成回复和标题；保存的记录以未加密文件存储在运行应用的电脑上。")

previous_title = st.session_state.session_title
maybe_generate_session_title()
saved = save_session_record()
if (response_received or previous_title != st.session_state.session_title) and (saved or not st.session_state.auto_save):
    st.rerun()
