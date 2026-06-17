from backend.main import api_response, health, serialize
from core.stream_worker import StreamWorkerStatus


def test_api_response_shape():
    response = api_response(True, "OK", {"value": 1})

    assert response == {
        "success": True,
        "message": "OK",
        "data": {"value": 1},
    }


def test_serialize_dataclass_status():
    status = StreamWorkerStatus(
        camera_id="cam_1",
        camera_name="Kamera 1",
        running=True,
        connected=True,
        frame_count=10,
        processed_frame_count=2,
    )

    data = serialize(status)

    assert data["camera_id"] == "cam_1"
    assert data["running"] is True
    assert data["processed_frame_count"] == 2


def test_health_includes_sources():
    response = health()

    assert response["success"] is True
    assert "sources" in response["data"]
    assert "cam_1" in response["data"]["sources"]
