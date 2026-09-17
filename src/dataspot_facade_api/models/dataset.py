from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UpdateLastUpdateRequest(BaseModel):
    """Request to update a dataset's customProperties.lastUpdate field."""

    last_update: datetime = Field(description="New last-update timestamp (ISO 8601)")


class UpdateLastUpdateResponse(BaseModel):
    """Updated last-update value returned by the API."""

    id: UUID = Field(description="Dataset identifier")
    last_update: datetime = Field(description="Updated last-update timestamp")
