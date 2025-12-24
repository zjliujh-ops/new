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
client = OpenAI(
    api_key="ms-f0118ead-bbf5-4b69-b4a4-6045902b499f", 
    base_url="https://api-inference.modelscope.cn" # 或者 api.openai.com
)
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
    """
    调用大模型获取回复
    """
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen3-Coder-480B-A35B-Instruct",  # 或者 "gpt-3.5-turbo", "qwen-turbo"
            messages=messages,
            temperature=0.7,
            stream=False # 简单起见先不流式输出
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"系统连接繁忙，请重试。错误信息: {e}"

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
    
    # --- 1. 信息采集区 ---
    col1, col2 = st.columns([1, 1])
    with col1:
        # 新增：岗位输入
        target_job = st.text_input("请输入您应聘的岗位", placeholder="例如：客户经理 / Python开发工程师")
    with col2:
        uploaded_file = st.file_uploader("请上传您的简历 (PDF)", type="pdf")

    # 初始化当前用户的 Session 数据结构
    if st.session_state.current_user not in st.session_state.candidates:
        st.session_state.candidates[st.session_state.current_user] = {
            "resume_text": "",
            "history": [],
            "job": "",
            "status": "ready" # ready -> interviewing -> finished
        }
    
    user_data = st.session_state.candidates[st.session_state.current_user]

    # --- 2. 控制逻辑：开始面试 ---
    # 只有当岗位填了、简历传了，且还没开始面试时，显示“开始面试”按钮
    if target_job and uploaded_file and user_data['status'] == 'ready':
        if st.button("开始面试", type="primary"):
            with st.spinner("AI 面试官正在阅读您的简历，请稍候..."):
                # A. 解析简历
                resume_text = extract_text_from_pdf(uploaded_file)
                user_data['resume_text'] = resume_text
                user_data['job'] = target_job
                user_data['status'] = 'interviewing'
                
                # B. 构建初始 Prompt (让 AI 根据简历生成第一个问题)
                system_prompt = f"""
                你现在是广东湛江移动公司的专业AI面试官。
                候选人应聘的岗位是：【{target_job}】。
                
                请遵循以下规则：
                1. 语气专业、亲切，体现中国移动的企业形象。
                2. 必须基于下方的简历内容进行针对性提问。
                3. 每次只问一个问题，不要一次性抛出所有问题。
                4. 首先进行简短的欢迎，然后针对简历中的项目经验或技能提出第一个问题。
                """
                
                # 初始化对话历史
                user_data['history'] = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"这是我的简历内容：\n{resume_text}\n\n请开始面试。"}
                ]
                
                # C. 获取 AI 的开场白
                first_response = get_ai_response(user_data['history'])
                user_data['history'].append({"role": "assistant", "content": first_response})
                
                st.rerun() # 刷新页面进入聊天模式

    # --- 3. 面试进行区 ---
    if user_data['status'] == 'interviewing':
        st.info(f"正在进行【{user_data['job']}】岗位的面试...")
        
        # 显示聊天记录 (跳过 system prompt 和简历原文，只显示对话)
        for msg in user_data['history']:
            if msg['role'] == "user" and "这是我的简历内容" in msg['content']:
                continue # 隐藏巨大的简历 prompt
            if msg['role'] == "system":
                continue
                
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # 用户输入回答
        if prompt := st.chat_input("请输入您的回答..."):
            # 1. 显示并保存用户回答
            with st.chat_message("user"):
                st.write(prompt)
            user_data['history'].append({"role": "user", "content": prompt})
            
            # 2. AI 思考并回复
            with st.chat_message("assistant"):
                with st.spinner("面试官正在记录并思考..."):
                    # 将完整的上下文发给 AI
                    ai_reply = get_ai_response(user_data['history'])
                    st.write(ai_reply)
            
            # 3. 保存 AI 回复
            user_data['history'].append({"role": "assistant", "content": ai_reply})

    # --- 4. 结束面试选项 ---
    if user_data['status'] == 'interviewing':
        if st.button("结束面试并提交"):
            user_data['status'] = 'finished'
            st.success("面试已结束，感谢您的参与！结果将由人工复核。")
            st.rerun()
            
    if user_data['status'] == 'finished':
        st.result = "面试已归档"
        st.info("您已完成本次面试。")

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
