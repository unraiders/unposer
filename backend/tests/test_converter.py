"""Tests del núcleo de conversión docker-compose -> XML Unraid."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.compose_tools import convert_host_paths_to_appdata  # noqa: E402
from app.core.converter import UnraidTemplateConverter  # noqa: E402
from app.core.github import _validate_compose_priority  # noqa: E402

COMPOSE = """
services:
  nginx:
    image: nginx:latest
    container_name: my-nginx
    environment:
      - NGINX_HOST=localhost
      - NGINX_PORT=80
    volumes:
      - /data/nginx/conf:/etc/nginx/conf.d:rw
    ports:
      - 8080:80/tcp
    labels:
      version: "1.0"
    network_mode: bridge
"""


def _convert():
    conv = UnraidTemplateConverter()
    data = conv.parse_docker_compose(COMPOSE)
    app_fields = {
        "Icon": "https://example.com/icon.png",
        "Overview": "Servidor web Nginx",
        "Support": "https://github.com/x/y/releases",
        "Project": "https://github.com/x/y",
        "Category": "Tools",
    }
    return data, conv.generate_unraid_template(data, web_port="8080:80", app_fields=app_fields)


def test_parse_extracts_first_service():
    conv = UnraidTemplateConverter()
    data = conv.parse_docker_compose(COMPOSE)
    assert data["container_name"] == "my-nginx"
    assert data["image"] == "nginx:latest"


def test_generate_basic_fields():
    _data, xml = _convert()
    assert "<Name>my-nginx</Name>" in xml
    assert "<Repository>nginx:latest</Repository>" in xml
    assert "hub.docker.com/_/nginx" in xml
    assert "<Overview>Servidor web Nginx</Overview>" in xml
    assert "<Category>Tools</Category>" in xml


def test_generate_config_sections():
    _data, xml = _convert()
    assert 'Type="Variable"' in xml and "NGINX_HOST" in xml
    assert 'Type="Port"' in xml and 'Target="80"' in xml
    assert 'Type="Path"' in xml and 'Target="/etc/nginx/conf.d"' in xml
    assert 'Type="Label"' in xml


def test_webui_port():
    _data, xml = _convert()
    assert "<WebUI>http://[IP]:[PORT:8080]/</WebUI>" in xml


def test_registry_ghcr():
    conv = UnraidTemplateConverter()
    assert conv.extract_registry_from_image("ghcr.io/user/repo:tag") == (
        "https://github.com/user/repo"
    )


APPDATA_COMPOSE = """services:
  jellyfin:
    image: jellyfin/jellyfin:latest
    container_name: jellyfin
    volumes:
      - /cualquier/ruta/config:/config
      - /mnt/disco/pelis:/media/movies:ro
      - jellyfin_cache:/cache
      - /sin/dos/puntos
"""


def test_appdata_paths_rewrites_host_side():
    out = convert_host_paths_to_appdata(APPDATA_COMPOSE)
    assert "- /mnt/user/appdata/jellyfin/config:/config" in out
    assert "- /mnt/user/appdata/jellyfin/media/movies:/media/movies:ro" in out
    # Volumen nombrado convertido a bind hacia appdata
    assert "- /mnt/user/appdata/jellyfin/cache:/cache" in out
    # Entrada sin ':' (volumen anónimo) se deja intacta
    assert "- /sin/dos/puntos" in out
    # La imagen y demás líneas no se tocan
    assert "image: jellyfin/jellyfin:latest" in out


def test_priority_1_full_compose():
    compose = """services:
  app:
    image: usuario/app
    environment:
      - TZ=Europe/Madrid
"""
    assert _validate_compose_priority(compose) == 1


def test_priority_2_minimal_compose():
    # Tiene services + image pero no environment -> regla de prioridad 2
    compose = """services:
  app:
    image: usuario/app
"""
    assert _validate_compose_priority(compose) == 2


def test_build_in_value_is_not_a_false_positive():
    # "build" aparece en el VALOR de una variable, no como clave build:.
    # La validación estricta no debe penalizarlo (la v1 sí lo hacía).
    compose = """services:
  app:
    image: usuario/app
    environment:
      - DESCRIPTION=build environment for tests
"""
    assert _validate_compose_priority(compose) == 1


def test_real_build_key_drops_priority():
    # Una clave build: real sí descarta la prioridad 1 (debe caer a 2).
    compose = """services:
  app:
    image: usuario/app
    build: .
    environment:
      - TZ=Europe/Madrid
"""
    assert _validate_compose_priority(compose) == 2


def test_invalid_compose_returns_minus_one():
    assert _validate_compose_priority("esto: no es un compose") == -1
    assert _validate_compose_priority("texto suelto sin estructura") == -1


if __name__ == "__main__":
    test_parse_extracts_first_service()
    test_appdata_paths_rewrites_host_side()
    test_priority_1_full_compose()
    test_priority_2_minimal_compose()
    test_build_in_value_is_not_a_false_positive()
    test_real_build_key_drops_priority()
    test_invalid_compose_returns_minus_one()
    test_generate_basic_fields()
    test_generate_config_sections()
    test_webui_port()
    test_registry_ghcr()
    print("OK")
