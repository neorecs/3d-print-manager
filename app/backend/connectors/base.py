from dataclasses import dataclass, field


@dataclass
class ConnectorResult:
    success: bool
    message: str
    external_product_id: str | None = None
    external_listing_id: str | None = None
    external_variant_ids: dict[str, str] = field(default_factory=dict)
    raw_response: dict | None = None


@dataclass
class ConnectorStatus:
    platform_type: str
    mode: str
    required_credentials: list[str]
    configured_credentials: list[str]
    missing_credentials: list[str]
    ready_for_live: bool


class PlatformConnector:
    platform_type = "generic"
    required_credentials: list[str] = []

    def __init__(self, credentials: dict[str, str], live_mode: bool = False):
        self.credentials = credentials
        self.live_mode = live_mode

    def status(self) -> ConnectorStatus:
        configured = sorted(key for key, value in self.credentials.items() if value)
        missing = [key for key in self.required_credentials if not self.credentials.get(key)]
        return ConnectorStatus(
            platform_type=self.platform_type,
            mode="live" if self.live_mode else "mock",
            required_credentials=self.required_credentials,
            configured_credentials=configured,
            missing_credentials=missing,
            ready_for_live=not missing,
        )

    def publish_product(self, payload: dict) -> ConnectorResult:
        return self._mock_result("publish", payload)

    def sync_product(self, payload: dict) -> ConnectorResult:
        return self._mock_result("sync", payload)

    def import_orders(self, limit: int = 25) -> dict:
        return {
            "success": False,
            "message": f"{self.platform_type} orderimport is nog niet geimplementeerd.",
            "orders": [],
        }

    def _mock_result(self, action: str, payload: dict) -> ConnectorResult:
        sku = payload.get("variants", [{}])[0].get("sku", "product")
        safe_sku = str(sku).lower().replace(" ", "-")
        return ConnectorResult(
            success=True,
            message=f"{self.platform_type} {action} uitgevoerd in mockmodus.",
            external_product_id=f"mock-{self.platform_type}-product-{payload['product_id']}",
            external_listing_id=f"mock-{self.platform_type}-listing-{safe_sku}",
            raw_response={"mode": "mock", "action": action},
        )
