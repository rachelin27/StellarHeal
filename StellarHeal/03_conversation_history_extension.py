import streamlit as st
import os
from openai import OpenAI
import datetime
import json

from requests import delete

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

# 保存会话记录的函数
def save_session_record():
    # 1. 保存当前会话信息
    if st.session_state.current_session:
        # 构建新的会话对象
        session_data = {
            "nick_name": st.session_state.nick_name,
            "nature": st.session_state.nature,
            "current_session": st.session_state.current_session,
            "messages": st.session_state.messages
        }

        # 如果 sessions 目录不存在，则创建
        if not os.path.exists("sessions"):
            # 创建目录
            os.mkdir("sessions")

        # 保存会话数据
        with open(f"sessions/{st.session_state.current_session}.json", "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

# 加载所有的会话列表信息
def load_sessions():
    session_list = []
    # 加载sessions目录下的文件
    if os.path.exists("sessions"):
        file_list = os.listdir("sessions")
        for filename in file_list:
            # 截取符合条件的文件名
            if filename.endswith(".json"):
                session_list.append(filename[:-5])
    #倒序排序
    session_list.sort(reverse=True)
    return session_list

# 加载指定的会话信息
def load_session(session_name):
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            # 读取会话数据
            with open(f"sessions/{session_name}.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)
                st.session_state.messages = session_data["messages"]
                st.session_state.nick_name = session_data["nick_name"]
                st.session_state.nature = session_data["nature"]
                st.session_state.current_session = session_name
    except Exception :
        st.error("加载会话失败!")

# 删除会话
def delete_session(session_name):
    try:
        if os.path.exists(f"sessions/{session_name}.json"):
            os.remove(f"sessions/{session_name}.json")
            # 如果删除的是当前对话，则需要清空页面并创建新会话
            if st.session_state.current_session == session_name:
                st.session_state.messages =  []
                st.session_state.current_session = generate_session_record()
    except Exception:
        st.error("删除会话失败!")

# 大标题
st.title("星愈")

# Logo
st.logo("resources/logo.png")

# 系统提示词
system_prompt = '''
          
你是一位性格 %s 的 %s，请灵活介绍身份，不要按照固定格式，不要强调“心理”这个词语让对方感到负担，轻松自然地交流。
你具备一定的心理学专业背景和心理咨询实践经验，擅长在简短对话中提供有效的情绪安抚与认知引导，帮助对方建立心理韧性。请为有轻度焦虑情绪的人，提供一次简短、结构化、温暖的心理安抚与认知调节引导（一次对话内完成）。
按步骤拆解复杂任务:
1. 共情与接纳：先确认并接纳用户的情绪，表达理解  
2. 情绪探索：引导用户简单描述当前感受与触发点  
3. 认知调节：提供一个简易的认知调整方法或视角转换  
4. 行动建议：给予一个具体可操作的放松技巧或小练习  
5. 赋能结束：用温暖的语言收尾，强调积极资源

请按照如下结构输出,不需要分点列出，保持语言连贯自然：
• 共情回应（1-2句话，表达理解）  
• 引导提问（1个开放性问题，帮助表达感受）  
• 方法建议（使用比喻或日常场景说明一个简单方法）  
• 可操作练习（一个具体、简单可立即尝试的技巧）  
• 结尾鼓励（温暖赋能的一句话）

                '''

#初始化聊天记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# 默认人物身份和性格
if "nick_name" not in st.session_state:
    st.session_state.nick_name = "心理医生"

if "nature" not in st.session_state:
    st.session_state.nature = "专业，耐心，和善"

if "current_session" not in st.session_state:
    st.session_state.current_session = generate_session_record()

#展示聊天记录
st.text(f"当前会话：{st.session_state.current_session}")
for message in st.session_state.messages:

    # if message["role"] == "user":
    #     st.chat_message("user").write(message["content"])
    # else:
    #     st.chat_message("assistant").write(message["content"])

    # 简化
    st.chat_message(message["role"]).write(message["content"])

# 左侧的侧边栏 - with: streamlit中上下文管理器
with st.sidebar:

    st.subheader("AI控制面板")

    # 保存会话记录
    if st.button("新建会话", width="stretch", icon="✏️"):
        save_session_record()

        # 创建新的会话,先判断会话是否为空：
        if st.session_state.messages:
            st.session_state.current_session = generate_session_record()
            st.session_state.messages = []
            save_session_record()
            st.rerun()

    # 会话历史
    st.text("会话历史")
    session_list = load_sessions()
    for session in session_list:
        col1, col2 = st.columns([4, 1])
        #用key作为唯一标识避免重复报错
        with col1:
            # 加载会话信息，如果是当前会话，则设置为高亮
            if st.button(session, width="stretch", icon="📂", key=f"load_{session}", type = "primary" if session==st.session_state.current_session else "secondary"):
                load_session(session)
                #赋值之后重新运行一次展示消息
                st.rerun()

        with col2:
            # 删除会话信息
            if st.button("", width="stretch", icon="❌", key=f"delete_{session}"):
                delete_session(session)
                st.rerun()

    # 分割线
    st.divider()

    st.subheader("自定义心理辅导员")

    # 自定义信息输入框
    nick_name = st.text_input("身份", placeholder="请输入身份")
    if nick_name:
        st.session_state.nick_name = nick_name

    nature = st.text_area("性格", placeholder="请输入性格")
    if nature:
        st.session_state.nature = nature

#创建与AI大模型交互的客户端对象
client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

# 消息输入框
prompt = st.chat_input("请输入你要咨询的问题")
if prompt:
    st.chat_message("user").write(prompt)
    print("------->调用AI大模型，输入提示词：", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 与AI大模型交互
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {# 系统提示词+自定义补充
                "role": "system", "content": system_prompt % (st.session_state.nature, st.session_state.nick_name)},
            # 解包，传入历史聊天记录，确保会话记忆
            *st.session_state.messages
        ],
        #更改为流式输出，提升用户体验
        stream=True
    )

    # 打印AI大模型的回复,print用于终端调试提示（非流式输出的解析方式）
    # print("大模型返回的结果：", response.choices[0].message.content)
    # st.chat_message("assistant").write(response.choices[0].message.content)

    # 输出大模型返回的结果（流式输出的解析方式）
    response_message = st.empty()  # 创建一个空的组件，用于展示大模型返回的结果

    full_response = ""
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content
            response_message.chat_message("assistant").write(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    #保存最新一次的会话记录
    save_session_record()

