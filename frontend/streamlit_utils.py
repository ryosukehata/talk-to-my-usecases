import logging
import streamlit as st
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_assistant_message_param import (
    ChatCompletionAssistantMessageParam,
)

from utils.api import fetch_dx_tool_suggestions
from utils.schema import PromptType

logger = logging.getLogger("TalkToMyUseCase")

MAX_QUESTION_ROUNDS = 5

async def handel_first_question(combined_input: str) -> None:
    # New conversation session initial state defined as a dictionary
    session_first_question = {
        "chat_history": [
            ChatCompletionUserMessageParam(role="user",
                                        content=combined_input)
            ],
        "conversation_stage": PromptType.DECISION,
        "questions_asked_flag": False,
        "ai_questions": [],
        "user_answers": {},
        "dx_solution": None,
        "question_counter": 1
    }
    # Update session state in bulk
    for key, value in session_first_question.items():
        st.session_state[key] = value
    logger.info("Session state has been updated by first question.")

async def handle_ai_response(ai_response: dict) -> str:
    """
    Processes the AI response and sets the appropriate session state.
    Args:
        ai_response: AI response dictionary
    """
    if not ai_response or ai_response.get("type") == "error":
        st.warning("AIとの通信に問題が発生しました。APIキーや入力内容を確認し、もう一度お試しください。")
        st.session_state.conversation_stage = "INITIAL_INPUT"
        st.rerun()
        return "INITIAL_INPUT"

    # Add AI response to chat history
    st.session_state.chat_history.append(
        ChatCompletionAssistantMessageParam(
            role="assistant",
            content=ai_response["message"]
        )
    )

    response_type = ai_response["type"]

    if response_type == PromptType.QUESTION or response_type == PromptType.SOLUTION:
        return response_type
    else:
        st.error(f"予期しないレスポンスタイプ: {response_type}")
        st.session_state.conversation_stage = "INITIAL_INPUT"
        st.rerun()
        return "INITIAL_INPUT"

def _handle_questions_response(ai_response: dict) -> None:
    """Handles question type responses."""
    st.session_state.ai_questions = ai_response["questions"]

    # Add AI questions to history individually
    for q_text in st.session_state.ai_questions:
        st.session_state.chat_history.append(
            ChatCompletionAssistantMessageParam(
                role="assistant",
                content=f"質問: {q_text}"
            )
        )

    st.session_state.conversation_stage = "AWAITING_ANSWERS"
    st.session_state.questions_asked_flag = True
    st.rerun()

def _handle_solution_response(ai_response: dict) -> None:
    """Handles solution type responses."""
    st.session_state.dx_solution = ai_response
    st.session_state.conversation_stage = "SHOWING_SOLUTION"
    st.rerun()

async def handle_user_answers_form() -> None:
    """
    Processes the user's answer form for AI questions.
    """
    temp_answers = {}
    for i, question_text in enumerate(st.session_state.ai_questions):
        temp_answers[question_text] = st.text_area(
            question_text,
            key=f"answer_q_openai_{i}",
            height=100
        )

    submitted = st.form_submit_button("回答を送信する")
    if submitted:
        _process_user_answers(temp_answers)

def _process_user_answers(temp_answers: dict) -> None:
    """
    Validates user answers and updates session state.

    Args:
        temp_answers: Dictionary containing question-answer pairs
    """
    all_answered = True
    user_responses_for_history = []

    # Validate answers and create responses for chat history
    for q_text, ans_text in temp_answers.items():
        if not ans_text:
            all_answered = False
            st.warning(f"質問「{q_text}」に回答してください。")
            break
        user_responses_for_history.append(
            ChatCompletionUserMessageParam(
                role="user",
                content=f"(質問「{q_text}」への回答) {ans_text}"
            )
        )

    # Proceed only if all questions are answered
    if all_answered:
        _update_session_with_answers(temp_answers, user_responses_for_history)

def _update_session_with_answers(temp_answers: dict, user_responses_for_history: list) -> None:
    """
    Updates session state with user answers.

    Args:
        temp_answers: Dictionary containing question-answer pairs
        user_responses_for_history: List of responses to add to chat history
    """
    st.session_state.user_answers = temp_answers
    st.session_state.chat_history.extend(user_responses_for_history)
    st.session_state.conversation_stage = PromptType.DECISION
    st.session_state.question_counter += 1
    st.rerun()

def update_checkbox_state_descrptions():
    st.session_state.use_tools_and_descriptions = st.session_state.use_tools_and_descriptions_key

def update_checkbox_state_llms():
    st.session_state.use_multiple_system_prompts = st.session_state.use_multiple_system_prompts_key

def display_dx_solution():
    """
    Displays the DX solution and ToDo list.
    """
    solution = st.session_state.dx_solution

    # Error check
    if "tools" in solution and solution["tools"] and solution["tools"][0] != "エラー":
        st.success("DXテーマの定義が完了しました！")
    else:
        st.error("DXテーマの定義中に問題が発生しました。")

    # Display suggestion message
    st.markdown(f"*{solution.get('message', '')}*")

    # Display primary DX tool
    primary_tool = solution.get('primary_tool', solution.get('tools', ['N/A'])[0] if solution.get('tools') else 'N/A')
    st.subheader(f"提案する主要DXツール: **{primary_tool}**")

    # If combining multiple DX tools
    if 'tool_combinations' in solution and solution['tool_combinations']:
        st.subheader("DXツールの組み合わせ:")

        for i, tool_combo in enumerate(solution['tool_combinations']):
            with st.expander(f"{i+1}. {tool_combo.get('tool', 'N/A')} - {tool_combo.get('purpose', '')}"):
                st.markdown(f"**役割**: {tool_combo.get('purpose', 'N/A')}")
                st.markdown("**関連するToDoリスト**:")
                tool_todos = tool_combo.get('todos', [])
                if tool_todos:
                    for j, todo_text in enumerate(tool_todos):
                        st.checkbox(f"{todo_text}", key=f"todo_combo_{i}_{j}")
                else:
                    st.write("このツールに関連するToDoリストはありません。")

    # Display overall ToDo list
    st.subheader("全体的な推奨ToDoリスト:")
    todos = solution.get('todos', [])
    if todos:
        for i, todo_text in enumerate(todos):
            st.checkbox(f"{todo_text}", key=f"todo_overall_{i}")
    else:
        st.write("ToDoリストは提供されませんでした。")

    # Display list of used DX tools
    if 'tools' in solution and len(solution['tools']) > 1:
        st.subheader("使用するDXツールの一覧:")
        tool_list_html = ""
        for tool in solution['tools']:
                if tool == primary_tool:
                    tool_list_html += f"- **{tool}** (主要ツール)\n"
                else:
                    tool_list_html += f"- {tool}\n"
            st.markdown(tool_list_html)

    st.markdown("---")

def display_chat_history_sidebar():
    """
    Displays the chat history in the sidebar.
    """
    if st.sidebar.checkbox("チャット履歴を表示する", key="show_chat_history_openai", value=True):
        st.sidebar.subheader("会話の履歴")
        if not st.session_state.get('chat_history', []):
            st.sidebar.write("まだ会話がありません。")
        for entry in st.session_state.get('chat_history', []):
            with st.sidebar.chat_message(entry["role"]):
                st.markdown(entry["content"])

    st.sidebar.markdown("---")
    st.sidebar.header("アプリ構想について")
    st.sidebar.markdown("""
    このアプリはAIアシスタントを利用してAIとの対話を行なっています。
    実現したいことに対してDXのどんな技術で解決できそうか判断してくれます。
    """)
