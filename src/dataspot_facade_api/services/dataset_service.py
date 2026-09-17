from datetime import datetime, timezone
from uuid import UUID

import httpx
from dcc_backend_common.logger import get_logger

from dataspot_facade_api.app_config import Configuration
from dataspot_facade_api.models.dataset import UpdateLastUpdateResponse
from dataspot_facade_api.services.auth_service import DataspotAuthClient

logger = get_logger("dataset_service")


class DatasetNotFoundError(Exception):
    """Raised when the requested dataset does not exist in Dataspot."""


class DatasetUpdateError(Exception):
    """Raised when Dataspot rejects or fails a dataset update."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class DatasetService:
    """Service for dataset operations proxied to Dataspot."""

    def __init__(self, config: Configuration, dataspot_auth: DataspotAuthClient):
        self._config = config
        self._dataspot_auth = dataspot_auth

    def _dataset_url(self, dataset_id: UUID) -> str:
        return f"{self._config.dataspot_base_url}/rest/{self._config.database_name}/datasets/{dataset_id}"

    @staticmethod
    def _to_epoch_ms(value: datetime) -> int:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp() * 1000)

    @staticmethod
    def _from_epoch_ms(value: int | float | str) -> datetime:
        return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc)

    async def update_last_update(self, dataset_id: UUID, last_update: datetime) -> UpdateLastUpdateResponse:
        """Update customProperties.lastUpdate on a Dataspot dataset via PATCH."""
        url = self._dataset_url(dataset_id)
        headers = self._dataspot_auth.get_service_headers()
        epoch_ms = self._to_epoch_ms(last_update)

        logger.info("Updating dataset lastUpdate", dataset_id=str(dataset_id), last_update_ms=epoch_ms)

        async with httpx.AsyncClient(timeout=30.0) as client:
            get_response = await client.get(url, headers=headers)
            if get_response.status_code == 404:
                raise DatasetNotFoundError(f"Dataset {dataset_id} was not found")
            if get_response.status_code != 200:
                logger.error(
                    "Failed to fetch dataset before update",
                    dataset_id=str(dataset_id),
                    status_code=get_response.status_code,
                )
                raise DatasetUpdateError(
                    "Failed to fetch dataset from Dataspot",
                    status_code=get_response.status_code,
                )

            dataset = get_response.json()
            custom_properties = dict(dataset.get("customProperties") or {})
            custom_properties["lastUpdate"] = epoch_ms

            patch_response = await client.patch(
                url,
                headers=headers,
                json={
                    "_type": "Dataset",
                    "customProperties": custom_properties,
                },
            )

            if patch_response.status_code == 404:
                raise DatasetNotFoundError(f"Dataset {dataset_id} was not found")
            if patch_response.status_code not in (200, 201):
                logger.error(
                    "Failed to update dataset lastUpdate",
                    dataset_id=str(dataset_id),
                    status_code=patch_response.status_code,
                )
                raise DatasetUpdateError(
                    "Failed to update dataset lastUpdate in Dataspot",
                    status_code=patch_response.status_code,
                )

            updated = patch_response.json()
            updated_value = (updated.get("customProperties") or {}).get("lastUpdate", epoch_ms)

        logger.info("Updated dataset lastUpdate", dataset_id=str(dataset_id))
        return UpdateLastUpdateResponse(
            id=dataset_id,
            last_update=self._from_epoch_ms(updated_value),
        )
