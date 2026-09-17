import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
import requests
from dotenv import load_dotenv

from dataspot_facade_api.app_config import Configuration

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class UserInfo:
    user_id: str
    email: str
    person_id: str


class DataspotAuthClient:
    def __init__(self):
        exposed_client_id = os.getenv("DATASPOT_EXPOSED_CLIENT_ID")
        self.scope = f"api://{exposed_client_id}/.default"
        self.tenant_id = os.getenv("DATASPOT_TENANT_ID")
        self.client_id = os.getenv("DATASPOT_CLIENT_ID")
        self.client_secret = os.getenv("DATASPOT_CLIENT_SECRET")
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.dataspot_access_key = os.getenv("DATASPOT_SERVICE_USER_ACCESS_KEY")
        self.token = None
        self.token_expires_at = None

    def get_bearer_access_token(self) -> str:
        if self._is_token_valid():
            return self.token

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": self.scope,
        }
        response = requests.post(self.token_url, data=data, timeout=30)
        response.raise_for_status()
        token_data = response.json()
        self.token = token_data["access_token"]
        expires_in = int(token_data.get("expires_in", 3600))
        self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return self.token

    def _is_token_valid(self) -> bool:
        if not self.token or not self.token_expires_at:
            return False
        return datetime.now(timezone.utc) < self.token_expires_at - timedelta(minutes=5)

    def get_service_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.get_bearer_access_token()}",
            "dataspot-access-key": self.dataspot_access_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }


class AuthService:
    def __init__(self, config: Configuration, dataspot_auth: DataspotAuthClient):
        self._config = config
        self._dataspot_auth = dataspot_auth

    def _base_url(self) -> str:
        return f"{self._config.base_url}/rest/{self._config.database_name}"

    def _probe_headers(self, access_key: str) -> dict:
        return {
            "Authorization": f"Bearer {self._dataspot_auth.get_bearer_access_token()}",
            "dataspot-access-key": access_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def validate_and_identify(self, access_key: str) -> UserInfo | None:
        email = self._validate_access_key(access_key)
        if email is None:
            return None

        user = self._lookup_user(email)
        if user is None:
            return None

        user_id = user.get("id")
        person_id = user.get("isPerson")
        if not user_id or not person_id:
            logger.error("User record for %s is missing id or isPerson", email)
            return None

        return UserInfo(user_id=user_id, email=email, person_id=person_id)

    def _validate_access_key(self, access_key: str) -> str | None:
        probe_headers = self._probe_headers(access_key)
        response = requests.get(
            f"{self._base_url()}/tenants/Mandant",
            headers=probe_headers,
            timeout=30,
        )

        if response.status_code == 401:
            logger.info("Access key validation failed (401)")
            return None

        if response.status_code == 500 and "Last unit does not have enough valid bits" in response.text:
            logger.info("Access key is malformed")
            return None

        if response.status_code != 200:
            logger.error("Unexpected validation status %s", response.status_code)
            return None

        tag_name = f"TMP_ACCESS_KEY_OWNER_PROBE_{secrets.token_urlsafe(32)}"
        create_response = requests.post(
            f"{self._base_url()}/tags",
            headers=probe_headers,
            json={"_type": "Tag", "name": tag_name},
            timeout=30,
        )

        if create_response.status_code not in (200, 201):
            logger.error("Failed to create temporary tag (%s)", create_response.status_code)
            return None

        created = create_response.json()
        email = created.get("createdBy")
        tag_id = created.get("id")

        if tag_id:
            requests.delete(
                f"{self._base_url()}/tags/{tag_id}",
                headers=self._dataspot_auth.get_service_headers(),
                timeout=30,
            )

        if not email:
            logger.error("Temporary tag created but createdBy was missing")
            return None

        return email

    def _lookup_user(self, email: str) -> dict | None:
        headers = self._dataspot_auth.get_service_headers()
        response = requests.get(
            f"{self._base_url()}/users",
            headers=headers,
            params={"loginId": email},
            timeout=30,
        )

        if response.status_code != 200:
            logger.error("Failed to look up user for %s (status %s)", email, response.status_code)
            return None

        data = response.json()
        embedded = data.get("_embedded", {})
        users = None
        for _key, val in embedded.items():
            if isinstance(val, list):
                users = val
                break

        if not users:
            logger.error("No users found in response for email %s", email)
            return None

        for user in users:
            if user.get("loginId") == email:
                return user

        return users[0]

    @staticmethod
    def create_jwt(
        user_id: str,
        email: str,
        person_id: str,
        secret: str,
        algorithm: str = "HS256",
        expires_in_seconds: int = 3600,
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "email": email,
            "person_id": person_id,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in_seconds),
        }
        return jwt.encode(payload, secret, algorithm=algorithm)
