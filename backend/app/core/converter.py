"""Módulo para convertir un Docker Compose a plantilla Unraid.

Portado desde el proyecto Reflex original con una limpieza ligera:
- Los mapeos se importan desde ``mappings.py`` (sin ``eval`` de archivos .dic).
- La plantilla base se localiza relativa al paquete.
- Usa ``logging`` estándar en vez del logger de Reflex.

La lógica de conversión (parseo, generación del XML, registros) se mantiene
idéntica en comportamiento a la original.
"""
import os
import re
from datetime import datetime
from typing import Any, Dict, List

import requests
import yaml

from app.core.mappings import MAPEO_APP, MAPEO_COMPOSE
from app.logging_config import setup_logger

logger = setup_logger(__name__)

# La plantilla base vive junto al código, en app/config_data/
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config_data")
TEMPLATE_PATH = os.path.join(CONFIG_DIR, "template_unraid_xml.txt")


class UnraidTemplateConverter:
    """Convierte un docker-compose a una plantilla XML de Unraid."""

    def __init__(self) -> None:
        self.mapeo_compose: Dict[str, str] = dict(MAPEO_COMPOSE)
        self.mapeo_app: Dict[str, str] = dict(MAPEO_APP)
        self.template_base: str = self._cargar_template_base()

    def _cargar_template_base(self) -> str:
        """Carga la plantilla base desde el archivo de configuración."""
        logger.debug(f"Verificando archivo de plantilla en: {TEMPLATE_PATH}")
        if os.path.exists(TEMPLATE_PATH):
            with open(TEMPLATE_PATH, "r", encoding="utf-8") as file:
                return file.read()
        raise FileNotFoundError(
            f"El archivo de plantilla obligatorio {TEMPLATE_PATH} no existe"
        )

    @staticmethod
    def _normalize_service(service_name: str, service: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza un servicio: container_name por defecto, labels/devices a lista."""
        if "container_name" not in service:
            service["container_name"] = service_name

        # Normalizar environment: admite forma de mapa (KEY: value) y de lista
        # (- KEY=value). Lo dejamos siempre como lista de "clave=valor".
        if "environment" in service:
            if isinstance(service["environment"], dict):
                service["environment"] = [
                    f"{k}={'' if v is None else v}"
                    for k, v in service["environment"].items()
                ]
            elif not isinstance(service["environment"], list):
                service["environment"] = [service["environment"]]

        # Normalizar labels a lista de "clave=valor"
        if "labels" in service:
            if isinstance(service["labels"], dict):
                service["labels"] = [f"{k}={v}" for k, v in service["labels"].items()]
            elif not isinstance(service["labels"], list):
                service["labels"] = [service["labels"]]

        # Normalizar devices a lista
        if "devices" in service:
            if isinstance(service["devices"], dict):
                service["devices"] = [f"{k}:{v}" for k, v in service["devices"].items()]
            elif not isinstance(service["devices"], list):
                service["devices"] = [service["devices"]]
            logger.debug(f"Dispositivos normalizados: {service['devices']}")

        return service

    def parse_docker_compose(self, docker_compose_content: str) -> Dict[str, Any]:
        """Parsea el docker-compose y devuelve el primer servicio normalizado."""
        try:
            docker_compose = yaml.safe_load(docker_compose_content)

            if not docker_compose or "services" not in docker_compose:
                raise ValueError("El archivo Docker Compose no tiene la sección 'services'")

            service_name = list(docker_compose["services"].keys())[0]
            service = docker_compose["services"][service_name]
            return self._normalize_service(service_name, service)
        except Exception as e:
            logger.debug(f"Error al parsear el Docker Compose: {str(e)}")
            return {}

    def parse_all_services(self, docker_compose_content: str) -> List[tuple]:
        """Parsea TODOS los servicios y los devuelve como (service_key, servicio).

        Cada servicio se normaliza igual que ``parse_docker_compose``. El orden se
        respeta. Devuelve [] si el compose no es válido.
        """
        try:
            docker_compose = yaml.safe_load(docker_compose_content)
            if not docker_compose or "services" not in docker_compose:
                raise ValueError("El archivo Docker Compose no tiene la sección 'services'")

            services = docker_compose["services"]
            if not isinstance(services, dict):
                return []

            result = []
            for service_name, service in services.items():
                if isinstance(service, dict):
                    result.append((service_name, self._normalize_service(service_name, service)))
            return result
        except Exception as e:
            logger.debug(f"Error al parsear los servicios del Docker Compose: {str(e)}")
            return []

    def get_github_repo_images(self, repo_url: str) -> List[str]:
        """Obtiene los archivos de imagen de un repositorio de GitHub."""
        try:
            if not repo_url.startswith("https://github.com/"):
                return []

            parts = repo_url.strip("/").split("/")
            if len(parts) < 5:
                logger.debug(f"URL de GitHub inválida: {repo_url}")
                return []

            owner = parts[3]
            repo = parts[4]

            api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
            response = requests.get(api_url, timeout=15)
            if response.status_code == 404:
                api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
                response = requests.get(api_url, timeout=15)

            if response.status_code != 200:
                logger.debug(f"Error al acceder a la API de GitHub: {response.status_code}")
                return []

            data = response.json()
            branch = "main" if "main" in api_url else "master"
            images = []
            for item in data.get("tree", []):
                if item.get("type") == "blob":
                    path = item.get("path", "")
                    if any(
                        path.lower().endswith(ext)
                        for ext in [".jpg", ".jpeg", ".png", ".ico", ".gif", ".svg"]
                    ):
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
                        images.append(raw_url)
            return images
        except Exception as e:
            logger.debug(f"Error al obtener imágenes del repositorio: {str(e)}")
            return []

    def generate_unraid_template(
        self,
        docker_compose: Dict[str, Any],
        icon_url: str = "",
        description: str = "",
        web_port: str = "",
        app_fields: Dict[str, str] = None,
    ) -> str:
        """Genera la plantilla XML de Unraid a partir del docker-compose."""
        logger.debug(f"Generando plantilla Unraid con docker_compose: {docker_compose}")
        try:
            if not self.mapeo_compose or not self.mapeo_app:
                raise ValueError("Los mapeos de campos necesarios no están disponibles.")

            template = self.template_base

            # Registro de la imagen
            if docker_compose.get("image"):
                registry = self.extract_registry_from_image(docker_compose["image"])
                logger.debug(f"Extracción del usuario/repositorio: {registry}")
                template = re.sub(
                    "<Registry>(.*?)</Registry>",
                    f"<Registry>{registry}</Registry>",
                    template,
                )

            # Mapeo directo compose -> etiquetas XML
            for compose_key, unraid_tag in self.mapeo_compose.items():
                if compose_key in docker_compose and docker_compose[compose_key]:
                    if compose_key == "command":
                        command_value = docker_compose[compose_key]
                        if isinstance(command_value, list):
                            command_value = " ".join(command_value)
                        template = re.sub(
                            f"<{unraid_tag}>(.*?)</{unraid_tag}>",
                            f"<{unraid_tag}>{command_value}</{unraid_tag}>",
                            template,
                        )
                        continue

                    if compose_key == "privileged":
                        value = str(docker_compose[compose_key]).lower()
                        template = re.sub(
                            f"<{unraid_tag}>(.*?)</{unraid_tag}>",
                            f"<{unraid_tag}>{value}</{unraid_tag}>",
                            template,
                        )
                        continue

                    bool_flag_options = {
                        "tty": "--tty",
                        "init": "--init",
                        "read_only": "--read-only",
                        "stdin_open": "--interactive",
                    }
                    if compose_key in bool_flag_options and docker_compose[compose_key] is True:
                        tag_pattern = f"<{unraid_tag}>(.*?)</{unraid_tag}>"
                        match = re.search(tag_pattern, template)
                        current_content = match.group(1) if match else ""
                        new_content = f"{current_content} {bool_flag_options[compose_key]}".strip()
                        template = re.sub(
                            tag_pattern, f"<{unraid_tag}>{new_content}</{unraid_tag}>", template
                        )
                        continue

                    template = re.sub(
                        f"<{unraid_tag}>(.*?)</{unraid_tag}>",
                        f"<{unraid_tag}>{docker_compose[compose_key]}</{unraid_tag}>",
                        template,
                    )

            # Mapeo de campos de la aplicación
            if app_fields and self.mapeo_app:
                for app_key, value in app_fields.items():
                    if app_key in self.mapeo_app and value:
                        unraid_tag = self.mapeo_app[app_key]
                        if unraid_tag:
                            template = re.sub(
                                f"<{unraid_tag}>(.*?)</{unraid_tag}>",
                                f"<{unraid_tag}>{value}</{unraid_tag}>",
                                template,
                            )

            # Compatibilidad con icon_url / description sueltos
            if icon_url and not (app_fields and "Icon" in app_fields):
                template = re.sub("<Icon>(.*?)</Icon>", f"<Icon>{icon_url}</Icon>", template)
            if description and not (app_fields and "Overview" in app_fields):
                template = re.sub(
                    "<Overview>(.*?)</Overview>", f"<Overview>{description}</Overview>", template
                )

            # Fecha de instalación
            current_timestamp = str(int(datetime.now().timestamp()))
            template = re.sub(
                "<DateInstalled>(.*?)</DateInstalled>",
                f"<DateInstalled>{current_timestamp}</DateInstalled>",
                template,
            )

            # WebUI
            if web_port:
                try:
                    host_port, _container_port = web_port.split(":")
                    webui_url = f"http://[IP]:[PORT:{host_port}]/"
                    template = re.sub(
                        "<WebUI>(.*?)</WebUI>", f"<WebUI>{webui_url}</WebUI>", template
                    )
                except Exception as e:
                    logger.debug(f"Error al configurar WebUI con puerto {web_port}: {str(e)}")

            # Secciones <Config>
            config_sections: List[str] = []

            # Variables de entorno
            if docker_compose.get("environment"):
                for env in docker_compose["environment"]:
                    if isinstance(env, str) and "=" in env:
                        key, value = env.split("=", 1)
                        config_sections.append(
                            f'  <Config Name="{key}" Target="{key}" Default="" Mode="" '
                            f'Description="" Type="Variable" Display="always" Required="false" '
                            f'Mask="false">{value}</Config>'
                        )
                    elif isinstance(env, dict):
                        for k, v in env.items():
                            config_sections.append(
                                f'  <Config Name="{k}" Target="{k}" Default="" Mode="" '
                                f'Description="" Type="Variable" Display="always" Required="false" '
                                f'Mask="false">{v}</Config>'
                            )

            # Labels
            if docker_compose.get("labels"):
                for label in docker_compose["labels"]:
                    if isinstance(label, str) and "=" in label:
                        key, value = label.split("=", 1)
                        value = value.strip("'\"")
                        config_sections.append(
                            f'  <Config Name="{key}" Target="{key}" Default="" Mode="" '
                            f'Description="" Type="Label" Display="always" Required="false" '
                            f'Mask="false">{value}</Config>'
                        )
                    elif isinstance(label, dict):
                        for k, v in label.items():
                            v = str(v).strip("'\"")
                            config_sections.append(
                                f'  <Config Name="{k}" Target="{k}" Default="" Mode="" '
                                f'Description="" Type="Label" Display="always" Required="false" '
                                f'Mask="false">{v}</Config>'
                            )

            # Volúmenes
            if docker_compose.get("volumes"):
                for vol in docker_compose["volumes"]:
                    if isinstance(vol, str) and ":" in vol:
                        parts = vol.split(":")
                        host_path = parts[0]
                        container_path = parts[1]
                        mode = parts[2] if len(parts) > 2 else "rw"
                        name = os.path.basename(container_path)
                        config_sections.append(
                            f'  <Config Name="{name}" Target="{container_path}" Default="" '
                            f'Mode="{mode}" Description="" Type="Path" Display="always" '
                            f'Required="false" Mask="false">{host_path}</Config>'
                        )

            # Puertos
            if docker_compose.get("ports"):
                for port in docker_compose["ports"]:
                    if isinstance(port, str) and ":" in port:
                        host_port, container_port = port.split(":", 1)
                        protocol = "tcp"
                        if "/" in container_port:
                            container_port, protocol = container_port.split("/", 1)
                        config_sections.append(
                            f'  <Config Name="Puerto {container_port}" Target="{container_port}" '
                            f'Default="" Mode="{protocol}" Description="" Type="Port" '
                            f'Display="always" Required="false" Mask="false">{host_port}</Config>'
                        )

            # Dispositivos
            if docker_compose.get("devices"):
                for device in docker_compose["devices"]:
                    if isinstance(device, str):
                        device_value = device.strip("'\"")
                        device_name = (
                            device_value.split("/")[-1] if "/" in device_value else device_value
                        )
                        if ":" in device_value:
                            host_device, container_device = device_value.split(":", 1)
                            config_sections.append(
                                f'  <Config Name="Dispositivo {device_name}" '
                                f'Target="{container_device}" Default="" Mode="" Description="" '
                                f'Type="Device" Display="always" Required="false" '
                                f'Mask="false">{host_device}</Config>'
                            )
                        else:
                            config_sections.append(
                                f'  <Config Name="Dispositivo {device_name}" '
                                f'Target="{device_value}" Default="" Mode="" Description="" '
                                f'Type="Device" Display="always" Required="false" '
                                f'Mask="false">{device_value}</Config>'
                            )
                    elif isinstance(device, dict):
                        for path_host, path_container in device.items():
                            device_name = (
                                path_container.split("/")[-1]
                                if "/" in path_container
                                else path_container
                            )
                            config_sections.append(
                                f'  <Config Name="Dispositivo {device_name}" '
                                f'Target="{path_container}" Default="" Mode="" Description="" '
                                f'Type="Device" Display="always" Required="false" '
                                f'Mask="false">{path_host}</Config>'
                            )

            # Eliminar Config existentes y añadir las nuevas
            template = re.sub(r"<Config.*?</Config>", "", template, flags=re.DOTALL)
            if config_sections:
                all_configs = "\n".join(config_sections)
                template = template.replace("</Container>", f"{all_configs}\n</Container>")

            # Limpieza: colapsar líneas en blanco e indentar
            template = re.sub(r"\n{2,}", "\n", template)
            lines = template.split("\n")
            cleaned_lines: List[str] = []

            if lines and lines[0].startswith("<?xml"):
                cleaned_lines.append(lines[0])

            container_start_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith("<Container"):
                    container_start_idx = i
                    cleaned_lines.append(line)
                    break
            if container_start_idx == -1:
                container_start_idx = 0 if not cleaned_lines else 1

            for i in range(container_start_idx + 1, len(lines) - 1):
                line = lines[i].strip()
                if not line:
                    continue
                cleaned_lines.append(f"  {line}")

            if "</Container>" in lines[-1]:
                cleaned_lines.append("</Container>")
            else:
                for i in range(len(lines) - 1, -1, -1):
                    if "</Container>" in lines[i]:
                        cleaned_lines.append(lines[i])
                        break
                else:
                    cleaned_lines.append("</Container>")

            return "\n".join(cleaned_lines)
        except Exception as e:
            logger.debug(f"Error al generar la plantilla: {str(e)}")
            return ""

    def extract_ports(self, docker_compose: Dict[str, Any]) -> List[str]:
        """Extrae los puertos en formato host:container."""
        ports: List[str] = []
        if "ports" in docker_compose:
            for port in docker_compose["ports"]:
                port = str(port)
                if ":" in port:
                    ports.append(port.split("/")[0] if "/" in port else port)
                else:
                    ports.append(f"{port}:{port}".split("/")[0] if "/" in port else port)
        return ports

    def create_app_fields_example(
        self,
        description: str,
        icon_url: str,
        category: str,
        project_url: str,
        support_url: str,
    ) -> Dict[str, str]:
        """Crea el diccionario app_fields."""
        return {
            "Overview": description,
            "Icon": icon_url,
            "Category": category,
            "Project": project_url,
            "Support": support_url,
        }

    def extract_registry_from_image(self, image_name: str) -> str:
        """Construye la URL del repositorio según el registro de la imagen."""
        if ":" in image_name:
            image_name = image_name.split(":")[0]
            logger.debug(f"Quitando el tag de versión a la imagen: {image_name}")

        if "/" in image_name:
            parts = image_name.split("/")
            if "." in parts[0] or ":" in parts[0]:
                registry = parts[0]
                repo_path = "/".join(parts[1:])
                if registry == "ghcr.io":
                    if "/" in repo_path:
                        user = parts[1]
                        repo = parts[2]
                        return f"https://github.com/{user}/{repo}"
                    return f"https://github.com/{repo_path}"
                elif registry == "quay.io":
                    return f"https://quay.io/repository/{repo_path}"
                else:
                    return f"https://{registry}"
            else:
                return f"https://hub.docker.com/r/{image_name}"

        return f"https://hub.docker.com/_/{image_name}"
