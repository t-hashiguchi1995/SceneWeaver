from __future__ import annotations

from typing import Any

import httpx

from creator_studio.adapters.eagle.errors import EagleError, EagleErrorCode


class EagleClient:
    def __init__(
        self, base_url: str, timeout: float = 10.0, client: httpx.Client | None = None
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = client

    def _request(self, method: str, route: str, **kwargs: Any) -> Any:
        try:
            if self._client is not None:
                response = self._client.request(
                    method, self._base_url + route, timeout=self._timeout, **kwargs
                )
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.request(method, self._base_url + route, **kwargs)
        except httpx.RequestError as exc:
            raise EagleError(EagleErrorCode.EAGLE_UNREACHABLE, str(exc)) from exc
        if not response.is_success:
            raise EagleError(EagleErrorCode.EAGLE_API_ERROR, f"HTTP {response.status_code}")
        try:
            payload = response.json()
            if not isinstance(payload, dict) or payload.get("status") != "success":
                message = (
                    payload.get("message", str(payload)) if isinstance(payload, dict) else payload
                )
                raise EagleError(EagleErrorCode.EAGLE_API_ERROR, str(message))
            return payload["data"]
        except (ValueError, KeyError) as exc:
            raise EagleError(EagleErrorCode.EAGLE_API_ERROR, "Invalid API response") from exc

    def application_info(self) -> dict:
        return self._request("GET", "/api/application/info")

    def list_folders(self) -> list[dict]:
        return self._request("GET", "/api/folder/list")

    def create_folder(self, name: str, parent_id: str | None = None) -> dict:
        payload = {"folderName": name}
        if parent_id is not None:
            payload["parent"] = parent_id
        return self._request("POST", "/api/folder/create", json=payload)

    def list_items(self, *, limit: int = 200, offset: int = 0) -> list[dict]:
        return self._request("GET", "/api/item/list", params={"limit": limit, "offset": offset})

    def add_from_path(
        self, *, path: str, name: str, tags: list[str], annotation: str, folder_id: str
    ) -> dict:
        return self._request(
            "POST",
            "/api/item/addFromPath",
            json={
                "path": path,
                "name": name,
                "tags": tags,
                "annotation": annotation,
                "folderId": folder_id,
            },
        )
