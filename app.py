import streamlit as st
import pandas as pd
import os
from datetime import datetime
from openai import OpenAI
import PyPDF2

# --- 配置 ---
# 请在实际部署时将 API Key 放入 st.secrets 或环境变量中
# 这里为了演示，假设用户已经配置好客户端
# client = OpenAI(api_key="ms-f0118ead-bbf5-4b69-b4a4-6045902b499f") 

# 模拟数据库 (在实际生产中应连接 SQL 数据库)
if 'candidates' not in st.session_state:
    st.session_state.candidates = {} # 存储候选人信息 {name: {resume: str, history: list, score: str}}
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# --- UI 样式自定义 (广东移动风格) ---
def set_css():
    st.markdown("""
        <style>
        .main {
            background-color: #f0f2f6;
        }
        .stButton>button {
            background-color: #0085D0; /* 中国移动蓝 */
            color: white;
            border-radius: 5px;
        }
        .header-bar {
            padding: 20px;
            background-color: #0085D0;
            color: white;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="header-bar">湛江移动公司 AI 面试系统</div>', unsafe_allow_html=True)

# --- 辅助函数 ---
def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def get_ai_response(messages):
    # 这里需要替换为你真实的 API 调用逻辑
    # 为了演示代码可运行，我们模拟一个简单的回复，或者你需要填入真实的 client
    try:
        # 实际代码:
        # response = client.chat.completions.create(model="gpt-4", messages=messages)
        # return response.choices[0].message.content
        return "（AI模拟回复）：收到，这是针对您简历中提到的项目经验的进一步提问..."
    except Exception as e:
        return f"AI服务连接错误: {e}"

def generate_evaluation(history, resume_text):
    # 让 AI 扮演面试官进行打分
    prompt = f"""
    请根据以下简历内容和面试对话记录，对候选人进行综合评价。
    
    简历内容摘要: {resume_text[:500]}...
    对话记录: {str(history)}
    
    请输出JSON格式评价：
    1. 沟通能力 (1-10分)
    2. 技术匹配度 (1-10分)
    3. 综合得分 (1-10分)
    4. 简短评语 (100字以内)
    """
    # 模拟返回
    return """
    **综合评价报告**
    - 沟通能力: 8.5/10
    - 技术匹配度: 7.0/10
    - **综合得分: 7.8/10**
    - 评语: 该候选人基础扎实，对移动业务有一定了解，但实战经验稍显欠缺。建议进入下一轮复试。
    """

# --- 页面逻辑 ---

def login_page():
    st.sidebar.title("系统登录")
    role = st.sidebar.radio("选择角色", ["面试者 (Candidate)", "面试官 (Interviewer)"])
    
    username = st.sidebar.text_input("用户名")
    if st.sidebar.button("进入系统"):
        if username:
            st.session_state.current_user = username
            st.session_state.role = role
            st.rerun()

def candidate_interface():
    st.subheader(f"欢迎参加面试, {st.session_state.current_user}")
    
    # 1. 上传简历
    uploaded_file = st.file_uploader("请上传您的简历 (PDF)", type="pdf")
    
    if uploaded_file is not None:
        resume_text = extract_text_from_pdf(uploaded_file)
        
        # 初始化用户数据
        if st.session_state.current_user not in st.session_state.candidates:
            st.session_state.candidates[st.session_state.current_user] = {
                "resume": resume_text,
                "history": [],
                "evaluation": None,
                "timestamp": datetime.now()
            }
        
        st.success("简历上传成功！AI面试官正在阅读...")
        
        # 2. AI 面试对话区
        st.markdown("---")
        st.write("### 🤖 AI 面试官")
        
        # 显示历史消息
        user_data = st.session_state.candidates[st.session_state.current_user]
        for msg in user_data['history']:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # 输入框
        if prompt := st.chat_input("请输入您的回答..."):
            # 添加用户消息
            user_data['history'].append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            # AI 回复
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                # 构建 context
                context = [{"role": "system", "content": "你湛江移动公司的AI面试官。请基于用户的简历进行专业提问，态度专业、亲切。每次只问一个问题。"}] + user_data['history']
                full_response = get_ai_response(context)
                message_placeholder.markdown(full_response)
            
            # 添加 AI 消息
            user_data['history'].append({"role": "assistant", "content": full_response})

def interviewer_interface():
    st.subheader("👨‍💼 面试官管理后台")
    
    if not st.session_state.candidates:
        st.info("暂无面试记录")
        return

    # 左侧：候选人列表
    candidate_list = list(st.session_state.candidates.keys())
    selected_candidate = st.selectbox("选择候选人查看详情", candidate_list)
    
    if selected_candidate:
        data = st.session_state.candidates[selected_candidate]
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.write("### 📄 简历预览")
            st.text_area("简历内容", data['resume'], height=300)
            
        with col2:
            st.write("### 💬 面试记录")
            for msg in data['history']:
                role_icon = "👤" if msg['role'] == "user" else "🤖"
                st.text(f"{role_icon}: {msg['content']}")
        
        st.markdown("---")
        st.write("### 📊 AI 综合评价")
        
        if st.button("生成/更新 评价报告"):
            evaluation = generate_evaluation(data['history'], data['resume'])
            data['evaluation'] = evaluation
            st.session_state.candidates[selected_candidate] = data # Update
            
        if data['evaluation']:
            st.info(data['evaluation'])
        else:
            st.warning("暂未生成评价")

# --- 主程序入口 ---
def main():
    st.set_page_config(page_title="湛江移动面试系统", page_icon="📱", layout="wide")
    set_css()
    
    if st.session_state.current_user is None:
        login_page()
    else:
        # 登出按钮
        if st.sidebar.button("退出登录"):
            st.session_state.current_user = None
            st.session_state.role = None
            st.rerun()
            
        if st.session_state.role == "面试者 (Candidate)":
            candidate_interface()
        else:
            interviewer_interface()

if __name__ == "__main__":
    main()
