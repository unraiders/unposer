"""Modelos Pydantic para request/response de la API."""
from typing import List, Optional

from pydantic import BaseModel


class ComposeContent(BaseModel):
    content: str


class ValidateResponse(BaseModel):
    valid: bool
    message: str
    image: Optional[str] = None


class ParseResponse(BaseModel):
    valid: bool
    message: str
    image: Optional[str] = None
    ports: List[str] = []
    github_urls: Optional[dict] = None


class AppdataPathsResponse(BaseModel):
    compose_text: str


class RepoURL(BaseModel):
    repo_url: str


class LoadComposeResponse(BaseModel):
    success: bool
    compose_text: str = ""
    branch: str = ""
    directory: str = ""
    filename: str = ""
    project_url: str = ""
    support_url: str = ""
    repo_icon_url: str = ""
    description: str = ""
    message: str = ""


class ImagesResponse(BaseModel):
    images: List[str] = []
    message: str = ""


class IconURL(BaseModel):
    url: str


class IconPreviewResponse(BaseModel):
    valid: bool
    message: str


class AppFields(BaseModel):
    Icon: str = ""
    Overview: str = ""
    Support: str = ""
    Project: str = ""
    Category: str = ""


# --- Multiservicio ----------------------------------------------------------

class ServiceMeta(BaseModel):
    key: str
    container_name: str
    image: str = ""
    ports: List[str] = []


class ServicesResponse(BaseModel):
    valid: bool
    message: str
    services: List[ServiceMeta] = []
    github_urls: Optional[dict] = None


class ServiceGenerateConfig(BaseModel):
    key: str
    icon_url: str = ""
    description: str = ""
    web_port: str = ""
    app_fields: AppFields = AppFields()


class GenerateRequest(BaseModel):
    compose_content: str
    services: List[ServiceGenerateConfig] = []


class GeneratedTemplate(BaseModel):
    key: str
    container_name: str
    filename: str
    xml: str


class GenerateResponse(BaseModel):
    success: bool
    templates: List[GeneratedTemplate] = []
    message: str = ""


class SaveItem(BaseModel):
    filename: str = ""
    xml_content: str


class SaveRequest(BaseModel):
    items: List[SaveItem] = []


class SaveResponse(BaseModel):
    success: bool
    saved: List[dict] = []
    message: str = ""
