import requests
from dcc_backend_common.logger import get_logger

from dataspot_facade_api.app_config import Configuration
from dataspot_facade_api.services.auth_service import DataspotAuthClient

logger = get_logger("query_service")


class QueryService:
    def __init__(self, config: Configuration, dataspot_auth: DataspotAuthClient):
        self._config = config
        self._dataspot_auth = dataspot_auth

    def execute_query(self, sql: str):
        url = f"{self._config.base_url}/api/{self._config.database_name}/queries/download?format=JSON"
        logger.debug("Executing query against Dataspot Query API: %s", url)

        response = requests.put(
            url,
            json={"sql": sql},
            headers=self._dataspot_auth.get_service_headers(),
            timeout=120,
        )
        response.raise_for_status()
        return response.json()
