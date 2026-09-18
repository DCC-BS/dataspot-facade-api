import logging
from time import perf_counter

import requests

from dataspot_facade_api.app_config import Configuration
from dataspot_facade_api.services.auth_service import DataspotAuthClient

logger = logging.getLogger("dataspot_facade_api.query_service")


class QueryService:
    def __init__(self, config: Configuration, dataspot_auth: DataspotAuthClient):
        self._config = config
        self._dataspot_auth = dataspot_auth

    def execute_query(self, sql: str):
        url = f"{self._config.dataspot_base_url}/api/{self._config.database_name}/queries/download?format=JSON"
        logger.debug("Executing query against Dataspot Query API url=%s", url)

        start = perf_counter()
        try:
            response = requests.put(
                url,
                json={"sql": sql},
                headers=self._dataspot_auth.get_service_headers(),
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error("Dataspot query request failed url=%s error=%s", url, e)
            raise
        elapsed_ms = round((perf_counter() - start) * 1000, 2)

        logger.debug(
            "Dataspot query response received url=%s status_code=%s duration_ms=%s",
            url,
            response.status_code,
            elapsed_ms,
        )
        return data
