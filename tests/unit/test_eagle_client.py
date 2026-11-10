from __future__ import annotations

import json

import httpx
import pytest

from creator_studio.adapters.eagle import EagleClient
from creator_studio.adapters.eagle.errors import EagleError, EagleErrorCode


def test_requests() -> None:
    requests = []

    def handle(request):
        requests.append(request)
        data = [{"id": "folder", "name": "SceneWeaver"}]
        return httpx.Response(200, json={"status": "success", "data": data})

    client = EagleClient("http://eagle", client=httpx.Client(transport=httpx.MockTransport(handle)))
    assert client.list_folders() == [{"id": "folder", "name": "SceneWeaver"}]
    client.create_folder("adopted", "parent")
    assert json.loads(requests[-1].content) == {"folderName": "adopted", "parent": "parent"}
    client.create_folder("SceneWeaver")
    assert json.loads(requests[-1].content) == {"folderName": "SceneWeaver"}
    client.add_from_path(path=r"D:\x.png", name="x", tags=["a"], annotation="note", folder_id="f")
    assert requests[-1].url.path == "/api/item/addFromPath"
    assert json.loads(requests[-1].content) == {
        "path": r"D:\x.png",
        "name": "x",
        "tags": ["a"],
        "annotation": "note",
        "folderId": "f",
    }
    client.list_items(limit=5, offset=10)
    assert dict(requests[-1].url.params) == {"limit": "5", "offset": "10"}


@pytest.mark.parametrize(
    "http_status,payload",
    [
        (200, {"status": "error", "message": "bad request"}),
        (503, {}),
        (200, {}),
    ],
)
def test_api_error(http_status, payload) -> None:
    client = EagleClient(
        "http://eagle",
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(http_status, json=payload))
        ),
    )
    with pytest.raises(EagleError) as error:
        client.application_info()
    assert error.value.code == EagleErrorCode.EAGLE_API_ERROR


def test_connection_error() -> None:
    def handle(request):
        raise httpx.ConnectError("offline", request=request)

    client = EagleClient("http://eagle", client=httpx.Client(transport=httpx.MockTransport(handle)))
    with pytest.raises(EagleError) as error:
        client.application_info()
    assert error.value.code == EagleErrorCode.EAGLE_UNREACHABLE
