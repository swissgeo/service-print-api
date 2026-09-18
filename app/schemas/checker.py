from pydantic import BaseModel, Field


class CheckerResponse(BaseModel):
    success: bool = Field(description="True when the service is healthy", examples=[True])
    message: str = Field(description="OK, or failure explanation", examples=["OK"])
    version: str = Field(description="Deployed version of the service", examples=["v1.0.0"])
