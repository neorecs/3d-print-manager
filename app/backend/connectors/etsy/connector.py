from connectors.base import ConnectorResult, PlatformConnector


class EtsyConnector(PlatformConnector):
    platform_type = "etsy"
    required_credentials = ["api_key", "access_token", "shop_id"]

    def publish_product(self, payload: dict) -> ConnectorResult:
        if not self.live_mode:
            return self._mock_result("publish", payload)
        return ConnectorResult(False, "Etsy live-publicatie is nog niet geimplementeerd.")

    def sync_product(self, payload: dict) -> ConnectorResult:
        if not self.live_mode:
            return self._mock_result("sync", payload)
        return ConnectorResult(False, "Etsy live-synchronisatie is nog niet geimplementeerd.")
