import json
from datetime import datetime
from typing import Any, cast

import datarobot as dr
import httpx
import pandas as pd
from datarobot.client import RESTClientObject
from pydantic import ValidationError

from utils.logging_helper import get_logger
from utils.resources import AICatalogDataset, LLMDeployment

logger = get_logger()


def initialize_deployment() -> tuple[RESTClientObject, str]:
    try:
        dr_client = dr.Client()
        chat_agent_deployment_id = LLMDeployment().id
        deployment_chat_base_url = (
            dr_client.endpoint + f"/deployments/{chat_agent_deployment_id}/"
        )
        return dr_client, deployment_chat_base_url
    except ValidationError as e:
        raise ValueError(
            "Unable to load Deployment ID."
            "If running locally, verify you have selected the correct "
            "stack and that it is active using `pulumi stack output`. "
            "If running in DataRobot, verify your runtime parameters have been set correctly."
        ) from e


def get_aicatalog_id() -> str:
    try:
        dr.Client()
        ai_catalog_id = AICatalogDataset().id
        return ai_catalog_id
    except ValidationError as e:
        raise ValueError(
            "Unable to load AIcatalog ID."
            "If running locally, verify you have selected the correct "
            "stack and that it is active using `pulumi stack output`. "
            "If running in DataRobot, verify your runtime parameters have been set correctly."
        ) from e


MAX_REGISTRY_DATASET_SIZE = 10e6


async def download_registry_dataset(dataset_id: str) -> pd.DataFrame:
    """Load selected datasets as pandas DataFrames

    Args:
        *args: list of dataset IDs to download

    Returns:
        list[pd.DataFrame]: list of data
    """

    dr.Client()
    dataset = dr.Dataset.get(dataset_id)
    if (
        sum([ds.size for ds in [dataset] if ds.size is not None])
        > MAX_REGISTRY_DATASET_SIZE
    ):
        raise ValueError(
            f"The requested Data Registry datasets must total <= {int(MAX_REGISTRY_DATASET_SIZE)} bytes"
        )

    try:
        df_records = cast(
            pd.DataFrame,
            dataset.get_as_dataframe(),
        )
        logger.info(f"Successfully downloaded {dataset.name}")
        return df_records
    except Exception as e:
        print(e)
        logger.error(f"Failed to read dataset {dataset.name}: {str(e)}")
        return None


async def fetch_aicatalog_dataset() -> pd.DataFrame:
    ai_catalog_dataset_id = get_aicatalog_id()
    return await download_registry_dataset(ai_catalog_dataset_id)


async def async_submit_actuals_to_datarobot(
    association_id: str, telemetry_json: dict[str, Any] | None = None
) -> None:
    dr_client, deployment_chat_base_url = initialize_deployment()
    deployment_chat_actuals_url = deployment_chat_base_url + "actuals/fromJSON/"
    telemetry_json["endTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "data": [
            {
                "associationId": association_id,
                "actualValue": json.dumps(telemetry_json, ensure_ascii=False),
            }
        ]
    }
    headers = dr_client.headers
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                deployment_chat_actuals_url, json=payload, headers=headers, timeout=5
            )
            logger.info("Actuals posted (async).")
        except Exception as e:
            logger.error(f"Failed posting actuals: {e}")
