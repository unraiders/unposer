"""Tests de soporte multiservicio (parse_all_services, generación y zip)."""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.routes import build_templates_zip  # noqa: E402
from app.core.converter import UnraidTemplateConverter  # noqa: E402
from app.schemas import SaveItem  # noqa: E402

MULTI = """services:
  backend:
    container_name: plex-trans-backend
    image: unraiders/plex-trans:backend
    environment:
      - APP_DB_PATH=/data/app.db
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
  frontend:
    container_name: plex-trans-frontend
    image: unraiders/plex-trans:frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
"""

SINGLE = """services:
  app:
    image: usuario/app
    ports:
      - 8080:80
"""


def test_parse_all_services_returns_all():
    conv = UnraidTemplateConverter()
    services = conv.parse_all_services(MULTI)
    assert [k for k, _ in services] == ["backend", "frontend"]
    assert services[0][1]["container_name"] == "plex-trans-backend"
    assert services[1][1]["container_name"] == "plex-trans-frontend"


def test_parse_all_services_container_name_fallback():
    conv = UnraidTemplateConverter()
    services = conv.parse_all_services(SINGLE)
    assert len(services) == 1
    # sin container_name -> usa el nombre del servicio
    assert services[0][1]["container_name"] == "app"


def test_generate_per_service_distinct_names():
    conv = UnraidTemplateConverter()
    services = conv.parse_all_services(MULTI)
    xmls = [conv.generate_unraid_template(svc) for _, svc in services]
    assert "<Name>plex-trans-backend</Name>" in xmls[0]
    assert "<Name>plex-trans-frontend</Name>" in xmls[1]
    # cada XML lleva su propio puerto
    assert 'Target="8000"' in xmls[0]
    assert 'Target="3000"' in xmls[1]
    assert 'Target="8000"' not in xmls[1]


ENV_MAP = """services:
  app:
    image: usuario/app
    environment:
      APP_DB_PATH: /data/app.db
      JWT_SECRET: ${JWT_SECRET:-secreto}
      EMPTY_VAR:
"""


def test_environment_map_form_generates_variables():
    conv = UnraidTemplateConverter()
    data = conv.parse_docker_compose(ENV_MAP)
    # Normalizado a lista clave=valor
    assert "APP_DB_PATH=/data/app.db" in data["environment"]
    assert "EMPTY_VAR=" in data["environment"]
    xml = conv.generate_unraid_template(data)
    assert 'Name="APP_DB_PATH"' in xml and 'Type="Variable"' in xml
    assert ">/data/app.db</Config>" in xml
    assert 'Name="JWT_SECRET"' in xml
    assert "${JWT_SECRET:-secreto}" in xml


def test_environment_list_form_still_works():
    conv = UnraidTemplateConverter()
    data = conv.parse_docker_compose(
        "services:\n  app:\n    image: usuario/app\n    environment:\n      - TZ=Europe/Madrid\n"
    )
    xml = conv.generate_unraid_template(data)
    assert 'Name="TZ"' in xml and ">Europe/Madrid</Config>" in xml


def test_build_templates_zip_contains_all():
    items = [
        SaveItem(filename="my-a.xml", xml_content="<Container><Name>a</Name></Container>"),
        SaveItem(filename="my-b.xml", xml_content="<Container><Name>b</Name></Container>"),
    ]
    data = build_templates_zip(items)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        assert sorted(names) == ["my-a.xml", "my-b.xml"]
        assert b"<Name>a</Name>" in zf.read("my-a.xml")


def test_build_templates_zip_dedupes_names():
    items = [
        SaveItem(filename="dup.xml", xml_content="<x>1</x>"),
        SaveItem(filename="dup.xml", xml_content="<x>2</x>"),
    ]
    data = build_templates_zip(items)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert sorted(zf.namelist()) == ["dup-2.xml", "dup.xml"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("OK")
