from uuid import UUID

import httpx
from dcc_backend_common.logger import get_logger

from dataspot_facade_api.app_config import Configuration
from dataspot_facade_api.services.auth_service import DataspotAuthClient
from dataspot_facade_api.services.utils.jwt_utils import JwtPayload

logger = get_logger("authorization_service")

FACADE_API_PERMISSION_UPDATE_LAST_UPDATE_DS = "UPDATE_LAST_UPDATE_DS"
"""Permission code for 'Feld eines Assets als Data Steward aktualisieren' under Facade-API Berechtigungen."""

FACADE_API_PERMISSION_EXECUTE_QUERY = "QUERY"
"""Permission code for 'Query-Befehle' under Facade-API Berechtigungen."""

DATA_STEWARD_QUERY_TEMPLATE = """
SELECT DISTINCT
    u.login_id AS email
FROM
    role_view r
JOIN
    attributedasset_view a ON a.attributed_as = r.id
JOIN
    post_view p ON p.id = a.attributed_to
JOIN
    holdspost_view hp ON hp.holds_post = p.id
JOIN
    person_view pe ON pe.id = hp.resource_id
JOIN
    user_view u ON u.is_person = pe.id
WHERE
    r.label = 'Data Steward'
    AND a.id = '{asset_id}'
    AND u.login_id IS NOT NULL

UNION

SELECT DISTINCT
    u.login_id AS email
FROM
    role_view r
JOIN
    attributedasset_view a ON a.attributed_as = r.id
JOIN
    user_view u ON u.is_person = a.attributed_to
WHERE
    r.label = 'Data Steward'
    AND a.id = '{asset_id}'
    AND u.login_id IS NOT NULL
"""
"""Data Stewards can be attributed to an asset either via a Post they hold, or
directly as a person (attributed_to = the person's own id). Both paths must be
checked, otherwise direct attributions are silently missed."""


class NotAuthorizedError(Exception):
    """Raised when the authenticated user is not allowed to perform the requested action."""


class DatasetAuthorizationService:
    """Authorizes facade-API dataset write operations against Dataspot permissions."""

    def __init__(self, config: Configuration, dataspot_auth: DataspotAuthClient):
        self._config = config
        self._dataspot_auth = dataspot_auth

    def _rest_base_url(self) -> str:
        return f"{self._config.dataspot_base_url}/rest/{self._config.database_name}"

    def _query_url(self) -> str:
        return f"{self._config.dataspot_base_url}/api/{self._config.database_name}/queries/download?format=JSON"

    async def ensure_can_update_last_update(self, dataset_id: UUID, payload: JwtPayload) -> None:
        """Raise NotAuthorizedError unless the user holds the facade-API permission
        and is a Data Steward of the given dataset."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            await _ensure_has_facade_api_permission(
                client,
                self._rest_base_url(),
                self._dataspot_auth,
                payload,
                FACADE_API_PERMISSION_UPDATE_LAST_UPDATE_DS,
                "Feld eines Assets als Data Steward aktualisieren",
            )
            await self._ensure_is_data_steward(client, dataset_id, payload.email)

    async def _ensure_is_data_steward(self, client: httpx.AsyncClient, dataset_id: UUID, email: str) -> None:
        headers = self._dataspot_auth.get_service_headers()
        sql = DATA_STEWARD_QUERY_TEMPLATE.format(asset_id=dataset_id)

        response = await client.put(self._query_url(), headers=headers, json={"sql": sql})
        if response.status_code != 200:
            logger.error(
                "Data Steward query failed",
                dataset_id=str(dataset_id),
                status_code=response.status_code,
            )
            raise NotAuthorizedError("Could not verify Data Steward assignment")

        stewards = _extract_emails(response.json())
        if email.strip().lower() not in stewards:
            logger.info("User is not a Data Steward of dataset", email=email, dataset_id=str(dataset_id))
            raise NotAuthorizedError("User is not a Data Steward of this dataset")


class QueryAuthorizationService:
    """Authorizes facade-API SQL query execution against Dataspot permissions."""

    def __init__(self, config: Configuration, dataspot_auth: DataspotAuthClient):
        self._config = config
        self._dataspot_auth = dataspot_auth

    def _rest_base_url(self) -> str:
        return f"{self._config.dataspot_base_url}/rest/{self._config.database_name}"

    async def ensure_can_execute_query(self, payload: JwtPayload) -> None:
        """Raise NotAuthorizedError unless the user holds the 'Query-Befehle' facade-API permission."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            await _ensure_has_facade_api_permission(
                client,
                self._rest_base_url(),
                self._dataspot_auth,
                payload,
                FACADE_API_PERMISSION_EXECUTE_QUERY,
                "Query-Befehle",
            )


async def _ensure_has_facade_api_permission(
    client: httpx.AsyncClient,
    rest_base_url: str,
    dataspot_auth: DataspotAuthClient,
    payload: JwtPayload,
    permission_code: str,
    permission_label: str,
) -> None:
    """Raise NotAuthorizedError unless the person holds `permission_code` under Facade-API Berechtigungen."""
    headers = dataspot_auth.get_service_headers()
    response = await client.get(f"{rest_base_url}/persons/{payload.person_id}", headers=headers)

    if response.status_code != 200:
        logger.error(
            "Failed to fetch person for permission check",
            person_id=payload.person_id,
            status_code=response.status_code,
        )
        raise NotAuthorizedError("Could not verify facade-API permissions")

    person = response.json()
    custom_properties = person.get("customProperties") or {}
    permissions = _as_permission_set(custom_properties.get("facade_api_permissions"))

    if permission_code not in permissions:
        logger.info("User lacks facade-API permission", email=payload.email, permission=permission_code)
        raise NotAuthorizedError(f"Missing '{permission_label}' permission")


def _as_permission_set(value: object) -> set[str]:
    if isinstance(value, str):
        return {token.strip() for token in value.split(",") if token.strip()}
    if isinstance(value, list):
        return {str(token).strip() for token in value if str(token).strip()}
    return set()


def _extract_emails(result: object) -> set[str]:
    rows: list = []
    if isinstance(result, list):
        rows = result
    elif isinstance(result, dict):
        rows = result.get("rows") or result.get("data") or []

    emails: set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            value = row.get("email") or row.get("EMAIL")
        elif isinstance(row, list) and row:
            value = row[0]
        else:
            value = None
        if value:
            emails.add(str(value).strip().lower())
    return emails
