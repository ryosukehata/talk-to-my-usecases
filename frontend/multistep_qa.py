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


from helpers import clear_data_callback, state_init,get_telemetry_data
from streamlit_utils import (
    handle_first_question,
    _handle_questions_response,
    _handle_solution_response,
    handle_user_answers_form,
    handle_ai_response,
)

sys.path.append("..")

from utils.api import (
    fetch_dx_tool_suggestions,
    process_uploaded_file,
)
from utils.schema import PromptType
# --- OpenAI APIの設定 ---


logger = logging.getLogger("TalkToMyUseCase")
MAX_QUESTION_ROUNDS = 5



# --- Streamlit アプリケーション ---
st.set_page_config(page_title="DXテーマ定義支援アプリ", layout="wide")

async def main():
    """
    メインのアプリケーションロジックを実行します。
    """
    st.title("DXテーマ定義支援アプリ 💡")
    st.caption("ふわっとした「やりたいこと」から、DXのテーマとToDoを具体化します。(OpenAI API連携版)")
    await state_init()

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
            
            await handle_first_question(combined_input)
            st.rerun()
        else:
            st.warning("「やりたいこと」を入力してください。")

    # --- AIによる分析と応答処理 ---
    if st.session_state.conversation_stage == PromptType.DECISION:
        with st.spinner("AIが分析中です...しばらくお待ちください。"):
            # chat_history には既にユーザーの最初の入力が含まれている
            print(st.session_state.chat_history)
            print(st.session_state.conversation_stage)
            ai_response = await fetch_dx_tool_suggestions(st.session_state.chat_history,
                                                          st.session_state.use_tools_and_descriptions,
                                                          telemetry_json=st.session_state.telemetry_json,
                                                          prompt_type=st.session_state.conversation_stage,
                                                          result_validation=False)
            # AIからの応答を処理
            response_type = await handle_ai_response(ai_response)
            print("Decision result is "+str(response_type))
            st.session_state.conversation_stage = response_type

    # --- AIからの追加質問作成 ---
    if st.session_state.conversation_stage == PromptType.QUESTION and st.session_state.question_counter <= MAX_QUESTION_ROUNDS:
        # 残りの質問回数を表示

        ai_response = await fetch_dx_tool_suggestions(st.session_state.chat_history,
                                                      st.session_state.use_tools_and_descriptions,
                                                      telemetry_json=st.session_state.telemetry_json,
                                                      prompt_type=st.session_state.conversation_stage,
                                                      result_validation=False)
        st.info(f"AIによる質問回数: {st.session_state.question_counter}回 / 最大5回中")
        _handle_questions_response(ai_response)


    # -- AIからの質問からユーザーの回答を待つ --
    if st.session_state.conversation_stage == "AWAITING_ANSWERS":
        # AIの質問を促すメッセージを表示
        st.info(st.session_state.chat_history[-1-len(st.session_state.ai_questions)]["content"])

        with st.form(key="answers_form_genai"):
            await handle_user_answers_form()


    # --- DXツールとToDoリストの生成 ---
    if st.session_state.conversation_stage == PromptType.SOLUTION or st.session_state.question_counter > MAX_QUESTION_ROUNDS:
        ai_response = await fetch_dx_tool_suggestions(st.session_state.chat_history,
                                                      st.session_state.use_tools_and_descriptions,
                                                      telemetry_json=st.session_state.telemetry_json,
                                                      prompt_type=st.session_state.conversation_stage,
                                                      result_validation=False)
        _handle_solution_response(ai_response)
                                                
    # --- DXツールとToDoリストの表示 ---
    if st.session_state.conversation_stage == "SHOWING_SOLUTION" and st.session_state.dx_solution:
        solution = st.session_state.dx_solution
    
        # エラーチェック
        if "tools" in solution and solution["tools"] and solution["tools"][0] != "エラー":
            st.success("DXテーマの定義が完了しました！")
        else:
            st.error("DXテーマの定義中に問題が発生しました。")
        
        # 提案メッセージの表示
        st.markdown(f"*{solution.get('message', '')}*")
    
        # 主要なDXツールの表示
        primary_tool = solution.get('primary_tool', solution.get('tools', ['N/A'])[0] if solution.get('tools') else 'N/A')
        st.subheader(f"提案する主要DXツール: **{primary_tool}**")
    
        # 複数のDXツールを組み合わせる場合
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
    
        # 全体的なToDoリストの表示
        st.subheader("全体的な推奨ToDoリスト:")
        todos = solution.get('todos', [])
        if todos:
            for i, todo_text in enumerate(todos):
                st.checkbox(f"{todo_text}", key=f"todo_overall_{i}")
        else:
            st.write("ToDoリストは提供されませんでした。")

        # 使用されるDXツール一覧の表示
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

        # リセットボタン
        if st.button("もう一度、最初からやり直す", 
                     key="restart_process_openai",
                     on_click=clear_data_callback):
            st.rerun()


    # --- チャット履歴の表示 (サイドバー) ---
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


asyncio.run(main())
