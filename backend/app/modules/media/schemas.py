"""Request and response shapes for media (Pydantic models)."""
from app.core.schemas import ApiModel


class UploadOut(ApiModel):
    file_id: str
    url: str
    download_url: str
    name: str
    size: int
