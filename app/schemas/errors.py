from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: int | None = Field(description="HTTP status code", examples=[400])
    message: str | None = Field(
        description="Human-readable error description", examples=["Bad request"]
    )


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, examples=[False])
    error: ErrorDetail
