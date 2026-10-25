"""The service exposes primitives rather than a boot-test composite."""

from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status

from dutchmate_service import schemas
from dutchmate_service.app import RuntimeProvider, create_app


def test_boot_test_endpoint_and_schema_are_absent() -> None:
    client = TestClient(create_app(FakeRuntime(connected_status())), raise_server_exceptions=False)

    assert client.post("/dut/boot-test", json={"duration_s": 1}).status_code == 404
    schema = client.get("/openapi.json").json()
    assert "/dut/boot-test" not in schema["paths"]
    assert "BootTestRequest" not in schema["components"]["schemas"]
    assert not hasattr(schemas, "BootTestRequest")
    assert not hasattr(RuntimeProvider, "run_boot_test")
