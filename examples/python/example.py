"""Simple example: call the API, and if the JWT is expired, get a new one and retry.

Uses httpx.Client with the base URL (host and the ``/v1`` prefix) baked in, so the
client only deals with endpoint paths. The client lazily authenticates on the first
call and, if the API rejects the request with a 401 (e.g. an expired JWT), fetches a
fresh token and retries the same request once.

Point it at a running Dataspot Facade API:

    python simple_retry.py --base-url http://127.0.0.1:8000 --access-key YOUR_KEY
"""

import argparse
import json

import httpx


class FacadeClient:
    """Talk to the facade API, authenticating and auto-refreshing the JWT on a 401."""

    def __init__(self, base_url, access_key):
        self.access_key = access_key
        self.token = None
        self._client = httpx.Client(base_url=f"{base_url.rstrip('/')}/v1")

    def _refresh_token(self):
        """Exchange the access key for a fresh facade JWT via POST /v1/auth."""
        response = self._client.post("/v1/auth", json={"access_key": self.access_key})
        response.raise_for_status()
        self.token = response.json()["access_token"]
        print("   (got fresh JWT)")

    def execute_query(self, sql):
        """Run a query via POST /v1/queries/execute, refreshing the JWT on a 401."""
        if self.token is None:
            self._refresh_token()

        def run_request():
            return self._client.post("/queries/execute", json={"sql": sql},
                                                headers={"Authorization": f"Bearer {self.token}"})

        response = run_request()

        if response.status_code == 401:  # JWT expired or invalid -> refresh and retry once
            print("   JWT rejected, refreshing...")
            self._refresh_token()
            response = run_request()

        response.raise_for_status()
        return response.json()


def main():
    parser = argparse.ArgumentParser(description="Call the facade API, refreshing the JWT on a 401")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base host of the facade API, e.g. http://127.0.0.1:8000")
    parser.add_argument("--access-key", required=True, help="Dataspot access key used to obtain a JWT")
    args = parser.parse_args()

    client = FacadeClient(args.base_url, args.access_key)
    result = client.execute_query("SELECT * FROM example_table LIMIT 5")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
