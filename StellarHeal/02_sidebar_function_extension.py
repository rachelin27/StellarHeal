import streamlit as st
import os
from openai import OpenAI

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

# 大标题
st.title("星愈")

# Logo
st.logo("resources/logo.png")

# 默认人物身份和性格
if "nick_name" not in st.session_state:
    st.session_state.nick_name = "心理医生"

if "nature" not in st.session_state:
    st.session_state.nature = "专业，耐心，和善"

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

#展示聊天记录
for message in st.session_state.messages:

    # if message["role"] == "user":
    #     st.chat_message("user").write(message["content"])
    # else:
    #     st.chat_message("assistant").write(message["content"])

    # 简化
    st.chat_message(message["role"]).write(message["content"])

# 左侧的侧边栏 - with: streamlit中上下文管理器
with st.sidebar:
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

