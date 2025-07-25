# Copyright 2024 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import traceback
import uuid
from datetime import datetime
from typing import (
    Any,
)

import streamlit as st

logger = logging.getLogger("TalkToMyUseCase")


# Add enhanced error logging function
def log_error_details(error: BaseException, context: dict[str, Any]) -> None:
    """Log detailed error information with context

    Args:
        error: The exception that occurred
        context: Dictionary containing error context
    """
    error_details = {
        "timestamp": datetime.now().isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "stack_trace": traceback.format_exc(),
        **context,
    }

    logger.error(
        f"\nERROR DETAILS\n=============\n{json.dumps(error_details, indent=2, default=str)}"
    )


empty_session_state = {
    "conversation_stage": "INITIAL_INPUT",
    "user_request": "",
    "ai_questions": [],
    "user_answers": {},
    "dx_solution": None,
    "chat_history": [],
    "questions_asked_flag": False,
    "question_counter": 0,
    "uploaded_files": {},
    "file_summaries": {},
    "file_uploader_key": 0,
    "user_request_buffer": "",
    "use_tools_and_descriptions": True,
}


def state_empty() -> None:
    for key, value in empty_session_state.items():
        st.session_state[key] = value
    logger.info("Session state has been reset to its initial empty state.")


def clear_data_callback() -> None:
    """Callback function to clear all data from session state and cache"""
    # Clear session state
    state_empty()

    st.session_state.file_uploader_key += 1  # Used to clear file_uploader


def generate_user_id() -> str | None:
    email_header = st.context.headers.get("x-user-email")
    if email_header:
        new_user_id = str(uuid.uuid5(uuid.NAMESPACE_OID, email_header))[:36]
        return new_user_id
    else:
        logger.warning("datarobot-connect not initialised")
        return None


async def state_init() -> None:
    if "conversation_stage" not in st.session_state:
        state_empty()
    user_id = None
    if "datarobot_uid" not in st.session_state:
        user_id = generate_user_id()
    else:
        user_id = st.session_state.datarobot_uid

    logger.info(f"User ID: {user_id}")
    if "user_email" not in st.session_state:
        st.session_state.user_email = st.context.headers.get("x-user-email")
        logger.info(f"User email: {st.session_state.user_email}")


async def get_telemetry_data() -> dict[str, str | None]:
    """Get telemetry data from session state
    Returns:
        dict: Dictionary containing user email
    """
    if not st.session_state.get("user_email"):
        logger.warning("User email not found in session state.")
    return {
        "user_email": st.session_state.user_email
        if "user_email" in st.session_state
        else None,
        "first_question": st.session_state.user_request,
        "filename": list(st.session_state.uploaded_files.keys())
        if "uploaded_files" in st.session_state
        else [],
    }
