"""Identify access-key owner via tag create (works for EDITOR/ADMINISTRATOR; not READ_ONLY)."""

import logging
import secrets
import sys

import requests

from tools.dataspot_auth import DataspotAuth

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class config:
    base_url = "https://datenkatalog.bs.ch"
    database_name = "wonderfull"


def _headers_for_access_key(auth: DataspotAuth, access_key: str) -> dict:
    return {
        "Authorization": f"Bearer {auth.get_bearer_access_token()}",
        "dataspot-access-key": access_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def identify_access_key_owner(access_key: str) -> dict:
    """Return whether the access key is valid and the owning user's login email."""
    auth = DataspotAuth()
    probe_headers = _headers_for_access_key(auth, access_key)
    service_headers = auth.get_headers()
    base = f"{config.base_url}/rest/{config.database_name}"

    validate_response = requests.get(f"{base}/tenants/Mandant", headers=probe_headers, timeout=30)
    logging.info(
        "Validated access key against %s (status %s)",
        config.database_name,
        validate_response.status_code,
    )

    if validate_response.status_code == 401:
        return {"valid": False, "email": None}

    if validate_response.status_code == 500 and ("Last unit does not have enough valid bits" in validate_response.text):
        logging.info("Access key is malformed (Dataspot Base64 decode failure)")
        return {"valid": False, "email": None}

    if validate_response.status_code != 200:
        raise RuntimeError(
            f"Unexpected validation status {validate_response.status_code}: {validate_response.text[:500]}"
        )

    tag_name = f"TMP_ACCESS_KEY_OWNER_PROBE_{secrets.token_urlsafe(32)}"
    create_response = requests.post(
        f"{base}/tags",
        headers=probe_headers,
        json={"_type": "Tag", "name": tag_name},
        timeout=30,
    )
    logging.info("Created temporary tag (status %s)", create_response.status_code)
    if create_response.status_code not in (200, 201):
        raise RuntimeError(
            f"Failed to create temporary tag ({create_response.status_code}): {create_response.text[:500]}"
        )

    created = create_response.json()
    email = created.get("createdBy")
    tag_id = created.get("id")

    if not tag_id:
        raise RuntimeError("Temporary tag was created but id was missing")

    delete_response = requests.delete(f"{base}/tags/{tag_id}", headers=service_headers, timeout=30)
    logging.info(
        "Deleted temporary tag %s as service user (status %s)",
        tag_id,
        delete_response.status_code,
    )
    if delete_response.status_code not in (200, 204):
        raise RuntimeError(
            f"Failed to delete temporary tag {tag_id} ({delete_response.status_code}): {delete_response.text[:500]}"
        )

    if not email:
        raise RuntimeError("Temporary tag was created but createdBy was missing")

    return {"valid": True, "email": email}


def main() -> int:
    ACCESS_KEY = "some-access-key-to-check-ownership-of"
    result = identify_access_key_owner(ACCESS_KEY)
    print(f"valid: {result['valid']}")
    print(f"email: {result['email']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
