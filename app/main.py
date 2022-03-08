import logging

import httpx
import humanfriendly
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter
from pydantic import BaseSettings

# get logger
logging.basicConfig()
logger = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    plusnet_user: str = ""
    plusnet_password: str = ""
    plusnet_realm: str = "portal.plus.net"


settings = AppSettings()
app = FastAPI()
router = InferringRouter()


@cbv(router)
class MetricsCBV:
    def __init__(self):
        # Work around for bug in Docker
        httpx._config.DEFAULT_CIPHERS += ":ALL:@SECLEVEL=1"

        headers = dict(accept="application/json")
        self._client = httpx.Client(headers=headers)

    def _login(self):
        logger.debug("Session cookie not set logging in")
        self._client.post(
            "https://www.plus.net/apps/member-centre/api/session",
            data=dict(
                user=settings.plusnet_user,
                password=settings.plusnet_password,
                realm=settings.plusnet_realm,
            ),
        )

    def _get_bandwidth(self):
        r = self._client.get("https://www.plus.net/apps/member-centre/api/broadband")
        return r.json()

    @router.get("/metrics")
    def metrics(self):
        if "portalcommonsession" not in self._client.cookies:
            self._login()

        bandwidth = self._get_bandwidth()
        current_line_speed = humanfriendly.parse_size(bandwidth["currentLineSpeedDown"])
        logger.info(f"CurrentLineSpeed: {current_line_speed}")

        output = [
            f"# HELP plusnetportal_current_line_speed The current line rate.",
            f"# TYPE plusnetportal_current_line_speed gauge",
            f"""plusnetportal_current_line_speed {current_line_speed}""",
        ]

        html_response = "\n".join(output)
        return PlainTextResponse(content=html_response, status_code=200)


app.include_router(router)
