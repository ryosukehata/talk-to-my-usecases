import logging
import sys
import asyncio

import streamlit as st

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_assistant_message_param import (
    ChatCompletionAssistantMessageParam,
)


from helpers import clear_data_callback, state_init, get_telemetry_data

sys.path.append("..")

from utils.api import process_uploaded_file, fetch_dx_tool_suggestions
from utils.schema import PromptType


logger = logging.getLogger("TalkToMyUseCase")


# --- Streamlit アプリケーション ---
st.set_page_config(page_title="DXテーマ定義支援アプリ", layout="wide")


async def handel_first_question(combined_input) -> None:
    # 新しい会話セッションの初期状態を辞書で定義
    session_first_question = {
        "chat_history": [
            ChatCompletionUserMessageParam(role="user",
                                        content=combined_input)
            ],
        "conversation_stage": "PROCESSING_INITIAL",
        "questions_asked_flag": False,
        "ai_questions": [],
        "user_answers": {},
        "dx_solution": None,
        "question_counter": 1  # 初期質問としてカウント
    }
    # セッションステートを一括更新
    for key, value in session_first_question.items():
        st.session_state[key] = value
    logger.info("Session state has been updated by first question.")


async def handle_single_step_ai_response(ai_response: dict) -> None:
    """
    AIからの応答を処理し、適切なセッション状態を設定します。
    Args:
        ai_response: AIからの応答辞書
    """
    if not ai_response or ai_response.get("type") == "error":
        st.warning("AIとの通信に問題が発生しました。APIキーや入力内容を確認し、もう一度お試しください。")
        st.session_state.conversation_stage = "INITIAL_INPUT"
        st.rerun()
        return

    # AIの応答をチャット履歴に追加
    st.session_state.chat_history.append(
        ChatCompletionAssistantMessageParam(
            role="assistant",
            content=ai_response["message"]
        )
    )
    
    response_type = ai_response["type"]
    
    if response_type == "questions":
        _handle_questions_response(ai_response)
    elif response_type == "solution":
        _handle_solution_response(ai_response)
    else:
        st.error(f"予期しないレスポンスタイプ: {response_type}")
        st.session_state.conversation_stage = "INITIAL_INPUT"
        st.rerun()

def _handle_questions_response(ai_response: dict) -> None:
    """質問タイプの応答を処理します。"""
    # 追加の質問が必要な場合（質問回数が上限未満）
    if st.session_state.question_counter >= 5:
        # 質問回数が上限に達した場合は強制的に解決策を表示
        st.warning("質問回数が上限に達しました。現時点での最善の提案を表示します。")
        st.session_state.dx_solution = {
            "tools": ai_response.get("tools", [ai_response.get("tool", "利用可能な最適なDXツール")]),
            "primary_tool": ai_response.get("primary_tool", ai_response.get("tool", "利用可能な最適なDXツール")),
            "tool_combinations": ai_response.get("tool_combinations", [{
                "tool": ai_response.get("tool", "利用可能な最適なDXツール"),
                "purpose": "主要な解決手段",
                "todos": ai_response.get("todos", ["現時点で考えられる最適なToDo"])
                }]),
            "todos": ai_response.get("todos", ["現時点で考えられる最適なToDo"]),
            "message": "質問回数の制限に達したため、限られた情報に基づく提案となっています: " + ai_response["message"]
            }
        st.session_state.conversation_stage = "SHOWING_SOLUTION"
    else:
        st.session_state.ai_questions = ai_response["questions"]
    
        # AIからの質問も個別に履歴に追加
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
    """解決策タイプの応答を処理します。"""
    st.session_state.dx_solution = ai_response
    st.session_state.conversation_stage = "SHOWING_SOLUTION"
    st.rerun()

async def handle_user_answers_form() -> None:
    """
    AIからの質問に対するユーザーの回答フォームを処理します。
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
    ユーザーの回答を検証し、セッション状態を更新します。
    
    Args:
        temp_answers: 質問と回答のペアを含む辞書
    """
    all_answered = True
    user_responses_for_history = []
    
    # 回答の検証とチャット履歴用の応答作成
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
    
    # すべての質問に回答されている場合のみ処理を進める
    if all_answered:
        _update_session_with_answers(temp_answers, user_responses_for_history)

def _update_session_with_answers(temp_answers: dict, user_responses_for_history: list) -> None:
    """
    ユーザーの回答でセッション状態を更新します。
    
    Args:
        temp_answers: 質問と回答のペアを含む辞書
        user_responses_for_history: チャット履歴に追加する応答のリスト
    """
    st.session_state.user_answers = temp_answers
    st.session_state.chat_history.extend(user_responses_for_history)
    st.session_state.conversation_stage = "PROCESSING_INITIAL"
    st.session_state.question_counter += 1  # 質問カウンターをインクリメント
    st.rerun()

def update_checkbox_state():
    st.session_state.use_tools_and_descriptions = st.session_state.use_tools_and_descriptions_key



async def main():
    """
    メインのアプリケーションロジックを実行します。
    """
    st.title("DXテーマ定義支援アプリ 💡")
    st.caption("ふわっとした「やりたいこと」から、DXのテーマとToDoを具体化します。(OpenAI API連携版)")
    await state_init()


    st.sidebar.checkbox("説明の付与を有効化する",
                        key="use_tools_and_descriptions_key",
                        on_change=update_checkbox_state_descrptions,
                        value=True)
    if st.session_state.use_tools_and_descriptions:
        st.sidebar.checkbox("複数のシステムプロンプトを利用して追加の質問が必要か判断させる",
                            key="use_multiple_system_prompts_key",
                            on_change=update_checkbox_state_llms,
                            value=True)


    # --- ステップ1: やりたいことの入力とファイルアップロード ---
    st.header("「やりたいこと」を教えてください")
    initial_user_request = st.text_area(
        "例: 営業部門の報告書作成業務を効率化したい、顧客の解約率を予測したい、新しいアイデアをたくさん出したい...",
        key="initial_request_input_openai",
        height=100,
        value=st.session_state.user_request_buffer
        )

    # ファイルアップロード機能
    st.subheader("参考資料のアップロード (オプション)")
    st.caption("現状の業務やデータの詳細を理解するために、関連ファイルをアップロードできます。")

    with st.expander("ファイルをアップロードする", expanded=True):
        uploaded_file = st.file_uploader(
            "Excel、CSV、PowerPoint、Word文書をアップロードできます",
            type=["xlsx", "xls", "csv", "pptx", "docx"],
            key=st.session_state.file_uploader_key,
        )

        if uploaded_file:
            # ファイル処理
            with st.spinner(f"ファイル「{uploaded_file.name}」を処理中..."):
                file_info = process_uploaded_file(uploaded_file)
                st.session_state.uploaded_files[uploaded_file.name] = file_info
                st.success(f"ファイル「{uploaded_file.name}」が正常にアップロードされました。")
                st.info(file_info["summary"])

        # アップロード済みファイル一覧
        if st.session_state.uploaded_files:
            st.subheader("アップロード済みファイル:")
            for filename, file_info in st.session_state.uploaded_files.items():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📄 {filename}")
                    st.caption(file_info["summary"])
                with col2:
                    if st.button("削除", key=f"delete_{filename}"):
                        del st.session_state.uploaded_files[filename]
                        st.rerun()

    # 送信ボタン
    if st.button("AIに相談する", 
                 key="submit_initial_request_openai"):
        if initial_user_request:
            # ファイル情報を追加した内容を作成
            file_context = ""
            if st.session_state.uploaded_files:
                file_context = "\n\nアップロードされたファイル情報:\n"
                for filename, file_info in st.session_state.uploaded_files.items():
                    file_context += f"- {filename}: {file_info['summary']}\n"

            combined_input = initial_user_request + file_context

            st.session_state.user_request = combined_input
            st.session_state.user_request_ = initial_user_request  # 元のユーザー入力だけを保持
            st.session_state.telemetry_json = await get_telemetry_data()
            print(st.session_state.telemetry_json)
            
            await handel_first_question(combined_input)
            st.rerun()
        else:
            st.warning("「やりたいこと」を入力してください。")

    # --- AIによる分析と応答処理 ---
    if st.session_state.conversation_stage == PromptType.DECISION:
        with st.spinner("AIが分析中です...しばらくお待ちください。"):
            print(st.session_state.chat_history)
            print(st.session_state.conversation_stage)
            if st.session_state.use_multiple_system_prompts:
                prompt_type=PromptType.DECISION
            else:
                prompt_type=None
            ai_response = await fetch_dx_tool_suggestions(st.session_state.chat_history,
                                                          st.session_state.use_tools_and_descriptions,
                                                          telemetry_json=st.session_state.telemetry_json,
                                                          prompt_type=prompt_type)
            print(st.session_state.conversation_stage)
            # AIからの応答を処理
            response_type = await handle_single_step_ai_response(ai_response)
            st.session_state.conversation_stage = response_type

    # --- ステップ1.5: AIからの追加質問とユーザーの回答 ---
    if st.session_state.conversation_stage == PromptType.QUESTION and st.session_state.question_counter <= MAX_QUESTION_ROUNDS:
        # 残りの質問回数を表示
        ai_response = await fetch_dx_tool_suggestions(st.session_state.chat_history,
                                                          st.session_state.use_tools_and_descriptions,
                                                          telemetry_json=st.session_state.telemetry_json,
                                                          prompt_type=st.session_state.conversation_stage)
        st.info(f"AIによる質問回数: {st.session_state.question_counter}回 / 最大{MAX_QUESTION_ROUNDS}回中")

        # AIの質問を促すメッセージを表示
        _handle_questions_response(ai_response) # This function now sets ai_questions and updates conversation_stage
        st.info(st.session_state.chat_history[-1-len(st.session_state.ai_questions)]["content"])

        with st.form(key="answers_form_genai"):
            await handle_user_answers_form()


    # --- ステップ2: DXツールとToDoリストの表示 ---
    if st.session_state.conversation_stage == PromptType.SOLUTION or st.session_state.question_counter > MAX_QUESTION_ROUNDS:
        ai_response = await fetch_dx_tool_suggestions(st.session_state.chat_history,
                                                      st.session_state.use_tools_and_descriptions,
                                                      telemetry_json=st.session_state.telemetry_json,
                                                      prompt_type=st.session_state.conversation_stage)
        st.session_state.dx_solution = ai_response # Set dx_solution here
        st.session_state.conversation_stage = "SHOWING_SOLUTION" # Update stage

    if st.session_state.conversation_stage == "SHOWING_SOLUTION" and st.session_state.dx_solution:
        display_dx_solution() # Call the utility function
        # リセットボタン
        if st.button("もう一度、最初からやり直す", 
                     key="restart_process_openai",
                     on_click=clear_data_callback):
            st.rerun()


    # --- チャット履歴の表示 (サイドバー) ---
    display_chat_history_sidebar() # Call the utility function


asyncio.run(main())

