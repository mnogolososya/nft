from pydantic import BaseModel


class HealthStatusResponse(BaseModel):
    healthy: bool
