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

# 系统提示词
system_prompt = "你作为一名专业的心理辅导老师，负责给用户的心理咨询提供建议和帮助，请用贴心温柔专业的语言回复。"

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
            {"role": "system", "content": system_prompt},
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

