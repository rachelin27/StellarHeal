# Please install OpenAI SDK first: `pip3 install openai`
import os
from openai import OpenAI

#创建与AI大模型交互的客户端对象
client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

#与AI大模型交互
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一名专业的心理辅导老师，负责给用户的心理咨询提供建议和帮助，请用贴心温柔专业的语言回复。"},
        {"role": "user", "content": "你是谁？"},
    ],
    stream=False
)

#打印AI大模型的回复
print(response.choices[0].message.content)