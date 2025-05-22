import streamlit as st
from rag_models.rag_zigbang import unified_chatbot

# streamlit 템플릿 지정
def main():
    st.set_page_config(
        page_title="동톡이",
        page_icon="🏠",
        layout="centered"
    )

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard&display=swap');
    
    html, body, [class*="css"] {
    font-family: 'Pretendard', sans-serif;
    background: radial-gradient(ellipse at top left, #1f2335, #151826 70%);
    color: #fff;
    }
    
    h1 {
    text-align: center;
    font-size: 3rem;
    color: #9bafff;
    margin-bottom: 0.2rem;
    text-shadow: 0 0 12px rgba(155, 175, 255, 0.4);
    }
    
    .description {
    text-align: center;
    font-size: 1.1rem;
    color: #aaa;
    margin-bottom: 2rem;
    }
    
    .chat-box {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    max-height: 500px;
    overflow-y: auto;
    padding-bottom: 1rem;
    }
    
    /* 공통 말풍선 */
    .chat-message {
    display: flex;
    align-items: flex-start;
    margin-bottom: 1rem;
    }
    
    .chat-bubble {
    padding: 0.8rem 1rem;
    border-radius: 20px;
    max-width: 70%;
    line-height: 1.5;
    word-break: break-word;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    
    /* 사용자 */
    .chat-user {
    justify-content: flex-end;
    }
    
    .user-bubble {
    background: linear-gradient(135deg, #6b73ff, #000dff);
    color: #fff;
    margin-right: 0.5rem;
    border-bottom-right-radius: 2px;
    }
    
    /* 봇 */
    .chat-bot {
    justify-content: flex-start;
    }
    
    .bot-bubble {
    background: rgba(255,255,255,0.08);
    color: black;
    margin-left: 0.5rem;
    border-bottom-left-radius: 2px;
    }
    
    /* 이모지 아바타 */
    .emoji-icon {
    width: 36px;
    height: 36px;
    background-color: #ffffff33;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
    box-shadow: 0 0 5px rgba(0,0,0,0.2);
    color: white;
    }
    </style>

    """, unsafe_allow_html=True)

# 화면 상단 설정
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.markdown("<h1>🤖🏠</h1>", unsafe_allow_html=True)
    st.markdown('<p class="description">매물 관련 질문이나 자취 관련 법률 문의를 해보세요!</p>', unsafe_allow_html=True)

# 히스토리 저장
    if 'history' not in st.session_state:
        st.session_state.history = []

# query 지정
    def send_query():
        user_question = st.session_state.user_input.strip()
        if user_question:
            st.session_state.history.append({"role": "user", "content": user_question})
            output = unified_chatbot(user_question)
            st.session_state.history.append({"role": "bot", "content": output})
        st.session_state.user_input = ""

    st.markdown('<div class="chat-box">', unsafe_allow_html=True)

# 채팅 설정
    for chat in st.session_state.history:
        if chat["role"] == "user":
            st.markdown(f'''
            <div class="chat-message chat-user">
                <div class="chat-bubble user-bubble">{chat["content"]}</div>
                <div class="emoji-icon">🧑‍💻</div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
            <div class="chat-message chat-bot">
                <div class="emoji-icon">🤖</div>
                <div class="chat-bubble bot-bubble">{chat["content"]}</div>
            </div>
            ''', unsafe_allow_html=True)

# 입력창 설정
    input_col, button_col = st.columns([9, 1])
    with input_col:
        st.text_input(
            label="질문을 입력하세요:",
            key="user_input",
            placeholder="Enter 또는 전송 버튼 클릭",
            on_change=send_query
        )
    with button_col:
        if st.button("전송"):
            send_query()

    st.markdown("""
        <script>
        const chatBox = window.parent.document.querySelector('.chat-box');
        if(chatBox) {
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        </script>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()


