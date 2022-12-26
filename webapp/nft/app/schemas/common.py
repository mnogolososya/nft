from pydantic import BaseModel


class InternalServerErrorResponse(BaseModel):
    detail: str
