from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Liveness of the API process only."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
