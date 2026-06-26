"""Endpoints REST de la API de unposerv2."""
import io
import os
import re
import zipfile
from typing import List

import requests
from fastapi import APIRouter
from fastapi.responses import Response

from app import config
from app.core import github
from app.core.compose_tools import convert_host_paths_to_appdata
from app.core.converter import UnraidTemplateConverter
from app.schemas import (
    AppdataPathsResponse,
    ComposeContent,
    GeneratedTemplate,
    GenerateRequest,
    GenerateResponse,
    IconPreviewResponse,
    IconURL,
    ImagesResponse,
    LoadComposeResponse,
    ParseResponse,
    RepoURL,
    SaveItem,
    SaveRequest,
    SaveResponse,
    ServiceMeta,
    ServicesResponse,
    ValidateResponse,
)

router = APIRouter(prefix="/api")
converter = UnraidTemplateConverter()


def _build_filename(xml: str) -> str:
    """Genera el nombre my-<container>.xml a partir de la etiqueta <Name>."""
    name = "unraid-template"
    if xml:
        match = re.search(r"<Name>([^<]+)</Name>", xml)
        if match:
            clean = re.sub(r"[^\w\-\.]", "_", match.group(1))
            name = f"my-{clean}"
    return f"{name}.xml"


def build_templates_zip(items: List[SaveItem]) -> bytes:
    """Empaqueta los XML en un zip en memoria. Evita nombres duplicados."""
    buffer = io.BytesIO()
    used = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in items:
            filename = item.filename or _build_filename(item.xml_content)
            base, ext = os.path.splitext(filename)
            candidate = filename
            i = 2
            while candidate in used:
                candidate = f"{base}-{i}{ext}"
                i += 1
            used.add(candidate)
            zf.writestr(candidate, item.xml_content)
    return buffer.getvalue()


@router.post("/compose/validate", response_model=ValidateResponse)
def validate_compose(payload: ComposeContent) -> ValidateResponse:
    data = converter.parse_docker_compose(payload.content)
    if not data:
        return ValidateResponse(valid=False, message="El Docker Compose no es válido.")
    if "image" not in data:
        return ValidateResponse(
            valid=False,
            message="El Docker Compose no contiene el campo 'image' necesario.",
        )
    return ValidateResponse(valid=True, message="Docker Compose válido.", image=data["image"])


@router.post("/compose/parse", response_model=ParseResponse)
def parse_compose(payload: ComposeContent) -> ParseResponse:
    data = converter.parse_docker_compose(payload.content)
    if not data:
        return ParseResponse(valid=False, message="El Docker Compose no es válido.")
    if "image" not in data:
        return ParseResponse(
            valid=False,
            message="El Docker Compose no contiene el campo 'image' necesario.",
        )
    ports = converter.extract_ports(data)
    urls = github.configure_github_urls_from_compose(payload.content)
    return ParseResponse(
        valid=True,
        message="Docker Compose procesado correctamente.",
        image=data["image"],
        ports=ports,
        github_urls=urls,
    )


@router.post("/compose/services", response_model=ServicesResponse)
def compose_services(payload: ComposeContent) -> ServicesResponse:
    services = converter.parse_all_services(payload.content)
    if not services:
        return ServicesResponse(valid=False, message="El Docker Compose no es válido.")

    metas = []
    for key, svc in services:
        if "image" not in svc:
            # Saltamos servicios sin imagen (no se pueden convertir a plantilla)
            continue
        metas.append(
            ServiceMeta(
                key=key,
                container_name=svc.get("container_name", key),
                image=svc.get("image", ""),
                ports=converter.extract_ports(svc),
            )
        )

    if not metas:
        return ServicesResponse(
            valid=False,
            message="Ningún servicio del Docker Compose tiene el campo 'image'.",
        )

    urls = github.configure_github_urls_from_compose(payload.content)
    return ServicesResponse(
        valid=True,
        message="Docker Compose procesado correctamente.",
        services=metas,
        github_urls=urls,
    )


@router.post("/compose/appdata-paths", response_model=AppdataPathsResponse)
def appdata_paths(payload: ComposeContent) -> AppdataPathsResponse:
    return AppdataPathsResponse(
        compose_text=convert_host_paths_to_appdata(payload.content)
    )


@router.post("/github/load-compose", response_model=LoadComposeResponse)
def load_compose(payload: RepoURL) -> LoadComposeResponse:
    result = github.load_docker_compose_from_github(payload.repo_url)
    return LoadComposeResponse(**result)


@router.post("/github/images", response_model=ImagesResponse)
def github_images(payload: RepoURL) -> ImagesResponse:
    images = converter.get_github_repo_images(payload.repo_url)
    if images:
        return ImagesResponse(
            images=images, message=f"Se encontraron {len(images)} imágenes en el repositorio."
        )
    return ImagesResponse(images=[], message="No se encontraron imágenes en el repositorio.")


@router.post("/icon/preview", response_model=IconPreviewResponse)
def icon_preview(payload: IconURL) -> IconPreviewResponse:
    if not payload.url:
        return IconPreviewResponse(valid=False, message="Introduce una URL de icono válida.")
    try:
        response = requests.head(payload.url, allow_redirects=True, timeout=15)
        content_type = response.headers.get("content-type", "")
        if response.status_code != 200 or not content_type.startswith("image/"):
            return IconPreviewResponse(
                valid=False, message="No se encontró imagen en esa URL o no es válida."
            )
        return IconPreviewResponse(valid=True, message="Vista previa del icono cargada.")
    except Exception:
        return IconPreviewResponse(
            valid=False, message="No se encontró imagen en esa URL o no es válida."
        )


@router.post("/template/generate", response_model=GenerateResponse)
def generate_template(payload: GenerateRequest) -> GenerateResponse:
    services = dict(converter.parse_all_services(payload.compose_content))
    if not services:
        return GenerateResponse(success=False, message="Docker Compose inválido.")

    templates = []
    for cfg in payload.services:
        svc = services.get(cfg.key)
        if not svc or "image" not in svc:
            continue
        web_port = (
            cfg.web_port
            if cfg.web_port and cfg.web_port != "No seleccionar puerto"
            else ""
        )
        xml = converter.generate_unraid_template(
            svc,
            cfg.icon_url,
            cfg.description,
            web_port,
            cfg.app_fields.model_dump(),
        )
        if not xml:
            continue
        templates.append(
            GeneratedTemplate(
                key=cfg.key,
                container_name=svc.get("container_name", cfg.key),
                filename=_build_filename(xml),
                xml=xml,
            )
        )

    if not templates:
        return GenerateResponse(success=False, message="No se pudo generar ninguna plantilla.")
    return GenerateResponse(success=True, templates=templates)


@router.post("/template/save-local", response_model=SaveResponse)
def save_template(payload: SaveRequest) -> SaveResponse:
    if not payload.items:
        return SaveResponse(success=False, message="No hay plantillas para guardar.")
    try:
        os.makedirs(config.PLANTILLAS_DIR, exist_ok=True)
        saved = []
        for item in payload.items:
            filename = item.filename or _build_filename(item.xml_content)
            save_path = os.path.join(config.PLANTILLAS_DIR, filename)
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(item.xml_content)
            saved.append({"filename": filename, "path": save_path})
        n = len(saved)
        msg = (
            f"Plantilla guardada en: {saved[0]['path']}"
            if n == 1
            else f"{n} plantillas guardadas en: {config.PLANTILLAS_DIR}"
        )
        return SaveResponse(success=True, saved=saved, message=msg)
    except Exception as e:
        return SaveResponse(success=False, message=f"Error al guardar las plantillas: {str(e)}")


@router.post("/template/download-zip")
def download_zip(payload: SaveRequest) -> Response:
    if not payload.items:
        return Response(status_code=400, content="No hay plantillas para descargar.")
    data = build_templates_zip(payload.items)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="unraid-templates.zip"'},
    )
