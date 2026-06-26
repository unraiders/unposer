"""Tests de la selección del docker-compose correcto (helpers puros, sin red)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.github import (  # noqa: E402
    PRIORITY_COMPOSE_PATHS,
    _image_match_grade,
    _parse_owner_repo,
    _path_score,
    _validate_compose_priority,
    extract_docker_compose_from_readme,
    select_best_compose,
)


# --- Reconocimiento de nombres ----------------------------------------------

def test_recognizes_compose_spec_names():
    assert "/compose.yaml" in PRIORITY_COMPOSE_PATHS
    assert "/compose.yml" in PRIORITY_COMPOSE_PATHS
    assert "/docker-compose.yml" in PRIORITY_COMPOSE_PATHS


def test_canonical_names_score_higher_than_examples():
    assert _path_score("docker-compose.yml") > _path_score("docker-compose.example.yml")
    assert _path_score("compose.yaml") > _path_score("examples/docker-compose.yml")


# --- owner/repo y coincidencia de imagen ------------------------------------

def test_parse_owner_repo():
    assert _parse_owner_repo("https://github.com/user/foo") == ("user", "foo")
    assert _parse_owner_repo("https://github.com/user/foo/tree/main") == ("user", "foo")


def test_image_match_grades():
    assert _image_match_grade("user/foo:latest", "user", "foo") == 3
    assert _image_match_grade("ghcr.io/user/foo", "user", "foo") == 3
    assert _image_match_grade("otro/foo", "user", "foo") == 2          # */repo
    assert _image_match_grade("foo", "user", "foo") == 1               # bare
    assert _image_match_grade("postgres:16", "user", "foo") == 0       # sin match
    assert _image_match_grade("registry:5000/user/foo", "user", "foo") == 3  # puerto


# --- Selección dominada por la imagen ---------------------------------------

ROOT_POSTGRES = """services:
  db:
    image: postgres:16
    environment:
      - POSTGRES_PASSWORD=x
"""

EXAMPLE_MATCH = """services:
  app:
    image: user/foo:latest
    environment:
      - TZ=Europe/Madrid
"""


def test_image_match_dominates_location():
    # El compose en examples/ con imagen del repo gana al de raíz con imagen ajena
    candidates = [
        ("docker-compose.yml", ROOT_POSTGRES),
        ("examples/docker-compose.yml", EXAMPLE_MATCH),
    ]
    best = select_best_compose(candidates, "user", "foo")
    assert best is not None
    assert best[1] == "examples/docker-compose.yml"


def test_without_image_match_prefers_root_canonical():
    candidates = [
        ("examples/docker-compose.yml", ROOT_POSTGRES),
        ("docker-compose.yml", ROOT_POSTGRES),
    ]
    best = select_best_compose(candidates, "user", "foo")
    assert best is not None
    assert best[1] == "docker-compose.yml"


def test_multiservice_match_in_non_first_service():
    compose = """services:
  db:
    image: postgres:16
  app:
    image: ghcr.io/user/foo
    environment:
      - TZ=Europe/Madrid
"""
    candidates = [("nested/dir/docker-compose.yml", compose)]
    best = select_best_compose(candidates, "user", "foo")
    assert best is not None  # se detecta el match aunque no sea el primer servicio
    # Y supera con creces a un root sin match
    candidates2 = [
        ("docker-compose.yml", ROOT_POSTGRES),
        ("nested/dir/docker-compose.yml", compose),
    ]
    assert select_best_compose(candidates2, "user", "foo")[1] == "nested/dir/docker-compose.yml"


def test_invalid_candidate_is_ignored():
    candidates = [("docker-compose.yml", "esto no es un compose")]
    assert select_best_compose(candidates, "user", "foo") is None


# --- README puntuado --------------------------------------------------------

README_TWO_BLOCKS = """
# Mi proyecto

Primero necesitas una base de datos:

```yaml
services:
  db:
    image: postgres:16
    environment:
      - POSTGRES_PASSWORD=x
```

Y aquí el stack de la aplicación:

```yaml
services:
  app:
    image: user/foo:latest
    environment:
      - TZ=Europe/Madrid
```
"""


def test_readme_prefers_image_matching_block():
    block = extract_docker_compose_from_readme(README_TWO_BLOCKS, "user", "foo")
    assert block is not None
    assert "user/foo" in block
    assert "postgres" not in block


def test_readme_validates_priority_regression():
    # Regresión: la validación estricta sigue intacta
    assert _validate_compose_priority("services:\n  a:\n    image: x\n    build: .\n") == 2


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("OK")
