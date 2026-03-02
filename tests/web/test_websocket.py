import pytest
from fastapi.testclient import TestClient
from homeauto.web.api import app


def test_websocket_connection():
    """Test WebSocket can connect"""
    client = TestClient(app)

    with client.websocket_connect("/ws") as websocket:
        # Should receive initial device update
        data = websocket.receive_json()
        assert "type" in data
        assert data["type"] == "device_update"
        assert "devices" in data
