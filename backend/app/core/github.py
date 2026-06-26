"""Lógica de integración con GitHub (stateless).

Busca el docker-compose de un repositorio (rutas prioritarias, README y árbol
completo) y deduce URLs a partir de la imagen.

La selección del compose "correcto" usa un sistema de puntuación cuya señal
**dominante** es la coincidencia entre la imagen del compose y el repositorio:
un compose cuya imagen es `owner/repo` (o `ghcr.io/owner/repo`, etc.) se prefiere
aunque esté en una subcarpeta o sea un `.example`, por encima de un compose en la
raíz con una imagen ajena (p. ej. solo `postgres`).
"""
import re
from typing import List, Optional, Tuple

import requests
import yaml

from app.core.converter import UnraidTemplateConverter
from app.logging_config import setup_logger

logger = setup_logger(__name__)

_converter = UnraidTemplateConverter()

# --- Nombres y rutas reconocidas --------------------------------------------

# Nombres canónicos (incluye el Compose Spec moderno: compose.yaml/.yml)
CANONICAL_NAMES = {
    "compose.yaml",
    "compose.yml",
    "docker-compose.yml",
    "docker-compose.yaml",
}
EXAMPLE_NAMES = [
    "docker-compose.example.yml",
    "docker-compose.example.yaml",
    "compose.example.yaml",
    "compose.example.yml",
]
# Directorios donde suele vivir el compose
_COMPOSE_DIRS = ["", "docker", "compose"]

# Carpetas que indican que un compose NO es el principal
PENALIZE_DIRS = {
    "example",
    "examples",
    "test",
    "tests",
    "docs",
    ".github",
    "sample",
    "samples",
}


def _build_priority_paths() -> List[str]:
    """Genera las rutas a probar: canónicas primero (por dir), luego ejemplos."""
    paths: List[str] = []
    for d in _COMPOSE_DIRS:
        prefix = f"/{d}" if d else ""
        for name in sorted(CANONICAL_NAMES):
            paths.append(f"{prefix}/{name}")
    # variantes .example solo en la raíz (menos comunes), tras las canónicas
    for name in EXAMPLE_NAMES:
        paths.append(f"/{name}")
    return paths


PRIORITY_COMPOSE_PATHS = _build_priority_paths()

PRIORITY_BRANCHES = ["main", "master"]

# Reglas de validación de prioridad (menor número = mayor prioridad)
COMPOSE_VALIDATION_PRIORITY = [
    {
        "priority": 1,
        "required_fields": ["services", "image"],
        "must_have": ["environment"],
        "must_not_have": ["build"],
    },
    {
        "priority": 2,
        "required_fields": ["services", "image"],
        "must_have": [],
        "must_not_have": [],
    },
]

# Tope de descargas en el fallback al árbol del repo
_TREE_DOWNLOAD_LIMIT = 5


# --- Validación de estructura ------------------------------------------------

def _validate_compose_priority(compose_text: str) -> int:
    """Valida la prioridad de un compose inspeccionando su estructura real.

    Examina las **claves** reales: ``services`` a nivel raíz y los campos del
    primer servicio (``image``, ``environment``, ``build``...). Así un valor que
    contenga la palabra "build" no invalida el compose; solo cuenta una clave
    ``build:`` real. Devuelve la prioridad (1 mejor, 2 mínima) o -1 si no es válido.
    """
    try:
        raw = yaml.safe_load(compose_text)
    except Exception:
        return -1

    if not isinstance(raw, dict) or "services" not in raw:
        return -1

    services = raw.get("services")
    if not isinstance(services, dict) or not services:
        return -1

    first_service = next(iter(services.values()))
    if not isinstance(first_service, dict):
        return -1

    top_fields = set(raw.keys())
    service_fields = set(first_service.keys())

    def has_field(name: str) -> bool:
        return name in top_fields or name in service_fields

    for validation in COMPOSE_VALIDATION_PRIORITY:
        if not all(has_field(f) for f in validation["required_fields"]):
            continue
        if not all(has_field(f) for f in validation["must_have"]):
            continue
        if any(has_field(f) for f in validation["must_not_have"]):
            continue
        return validation["priority"]

    return -1


# --- Coincidencia imagen <-> repositorio ------------------------------------

def _parse_owner_repo(repo_url: str) -> Tuple[str, str]:
    """Extrae (owner, repo) de una URL de GitHub."""
    base = repo_url.rstrip("/")
    for sep in ("/blob/", "/raw/", "/tree/"):
        if sep in base:
            base = base.split(sep)[0]
    parts = [p for p in base.split("/") if p]
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return "", ""


def _normalize_image_path(image: str) -> List[str]:
    """Devuelve los segmentos de la imagen sin registro, tag ni digest.

    Ej.: 'ghcr.io/user/repo:tag' -> ['user', 'repo']; 'nginx' -> ['nginx'].
    """
    img = image.strip().lower().split("@")[0]
    # quitar tag, pero respetando el posible puerto del registro (host:port/...)
    if ":" in img.rsplit("/", 1)[-1]:
        img = img.rsplit(":", 1)[0]
    parts = [p for p in img.split("/") if p]
    # quitar prefijo de registro (contiene '.' o ':' o es localhost)
    if len(parts) > 1 and ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost"):
        parts = parts[1:]
    return parts


def _image_match_grade(image: str, owner: str, repo: str) -> int:
    """Grado de coincidencia imagen<->repo: 3 (owner/repo) > 2 (*/repo) > 1 (repo) > 0."""
    if not repo:
        return 0
    parts = _normalize_image_path(image)
    owner_l, repo_l = owner.lower(), repo.lower()
    if len(parts) >= 2:
        if parts[-2] == owner_l and parts[-1] == repo_l:
            return 3
        if parts[-1] == repo_l:
            return 2
    elif len(parts) == 1 and parts[0] == repo_l:
        return 1
    return 0


def _iter_service_images(compose_dict: dict) -> List[str]:
    """Imágenes de TODOS los servicios (no solo el primero)."""
    images: List[str] = []
    services = compose_dict.get("services") if isinstance(compose_dict, dict) else None
    if isinstance(services, dict):
        for svc in services.values():
            if isinstance(svc, dict) and svc.get("image"):
                images.append(str(svc["image"]))
    return images


def _compose_image_grade(compose_text: str, owner: str, repo: str) -> int:
    """Mejor grado de coincidencia imagen<->repo entre todos los servicios."""
    try:
        raw = yaml.safe_load(compose_text)
    except Exception:
        return 0
    if not isinstance(raw, dict):
        return 0
    return max((_image_match_grade(img, owner, repo) for img in _iter_service_images(raw)), default=0)


def _any_service_has_key(compose_text: str, key: str) -> bool:
    """¿Algún servicio del compose define la clave indicada (p. ej. environment)?"""
    try:
        raw = yaml.safe_load(compose_text)
    except Exception:
        return False
    if not isinstance(raw, dict):
        return False
    services = raw.get("services")
    if not isinstance(services, dict):
        return False
    return any(isinstance(svc, dict) and key in svc for svc in services.values())


# --- Puntuación de candidatos ------------------------------------------------

def _path_score(path: str) -> int:
    """Puntúa un candidato por nombre de archivo y ubicación (sin mirar la imagen)."""
    relpath = path.lstrip("/").lower()
    segs = relpath.split("/")
    name = segs[-1]
    folders = segs[:-1]
    depth = len(folders)

    score = 0
    if name in CANONICAL_NAMES:
        score += 30
    elif "example" in name:
        score += 5

    if depth == 0:
        score += 20  # raíz
    elif folders and folders[0] in ("docker", "compose"):
        score += 10

    if any(seg in PENALIZE_DIRS for seg in folders):
        score -= 40

    score -= depth  # desempate: menor profundidad mejor
    return score


def _score_candidate(path: str, compose_text: str, owner: str, repo: str) -> Optional[int]:
    """Puntuación total de un candidato; None si no es un compose válido.

    La coincidencia imagen<->repo es la señal DOMINANTE (peso x1000).
    """
    priority = _validate_compose_priority(compose_text)
    if priority < 0:
        return None
    grade = _compose_image_grade(compose_text, owner, repo)
    priority_pts = {1: 50, 2: 20}.get(priority, 0)

    # Preferencia fuerte por composes con environment: (variables inline que sí
    # podemos convertir) frente a env_file: (un .env externo que no tenemos).
    # Va por debajo de la coincidencia imagen<->repo (x1000) pero por encima del
    # resto de señales, para desempatar entre composes del mismo contenedor.
    if _any_service_has_key(compose_text, "environment"):
        env_pts = 200
    elif _any_service_has_key(compose_text, "env_file"):
        env_pts = -200
    else:
        env_pts = 0

    return grade * 1000 + env_pts + priority_pts + _path_score(path)


def select_best_compose(
    candidates: List[Tuple[str, str]], owner: str, repo: str
) -> Optional[Tuple[int, str, str]]:
    """De una lista de (path, texto), devuelve (score, path, texto) del mejor."""
    scored = []
    for path, text in candidates:
        s = _score_candidate(path, text, owner, repo)
        if s is not None:
            scored.append((s, path, text))
    if not scored:
        return None
    scored.sort(key=lambda t: t[0], reverse=True)
    return scored[0]


def _is_compose_path(path: str) -> bool:
    """¿El basename de la ruta parece un archivo compose?"""
    name = path.rsplit("/", 1)[-1].lower()
    if name in CANONICAL_NAMES:
        return True
    return ("compose" in name) and name.endswith((".yml", ".yaml"))


def _split_relpath(relpath: str) -> Tuple[str, str]:
    """Devuelve (directorio, archivo) de una ruta relativa al repo."""
    relpath = relpath.lstrip("/")
    if "/" in relpath:
        d, f = relpath.rsplit("/", 1)
        return d, f
    return "", relpath


# --- Extracción desde README -------------------------------------------------

def extract_docker_compose_from_readme(
    readme_text: str, owner: str = "", repo: str = ""
) -> Optional[str]:
    """Extrae el mejor bloque docker-compose del README.

    Recoge todos los bloques candidatos y elige el de mayor puntuación
    (preferencia por coincidencia de imagen con el repo).
    """
    code_patterns = [
        r"```ya?ml\s+([\s\S]*?)```",
        r"```docker[\-\s]?compose\s+([\s\S]*?)```",
        r"```\s+version:[\s\S]*?services:[\s\S]*?```",
        r"```\s+services:[\s\S]*?```",
        r"<pre>\s*version:[\s\S]*?services:[\s\S]*?</pre>",
        r"<pre>\s*services:[\s\S]*?</pre>",
        r"<code>\s*version:[\s\S]*?services:[\s\S]*?</code>",
        r"<code>\s*services:[\s\S]*?</code>",
        r"```[\s\S]*?services:[\s\S]*?image:[\s\S]*?```",
        r"<pre>[\s\S]*?services:[\s\S]*?image:[\s\S]*?</pre>",
    ]

    potential_blocks: List[str] = []
    for pattern in code_patterns:
        for match in re.findall(pattern, readme_text):
            if isinstance(match, str):
                if match.strip().startswith("```") or match.strip().startswith("<pre>"):
                    content = re.sub(r"^```\w*\s*|\s*```$", "", match.strip())
                    content = re.sub(r"^<pre>\s*|\s*</pre>$", "", content.strip())
                    content = re.sub(r"^<code>\s*|\s*</code>$", "", content.strip())
                else:
                    content = match.strip()
            else:
                content = match[0].strip() if match else ""
            potential_blocks.append(content)

    # URLs a docker-compose dentro del README
    for url in re.findall(r"(https?://[^\s\)\"\']+(?:docker-compose\.ya?ml))", readme_text):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                potential_blocks.append(resp.text)
        except Exception:
            continue

    # Bloques indentados no marcados
    indented_patterns = [
        r"(?:^|\n)(\s+services:[\s\S]*?)(?=\n\S|\Z)",
        r"(?:^|\n)(\s+version:[\s\S]*?services:[\s\S]*?)(?=\n\S|\Z)",
    ]
    for pattern in indented_patterns:
        for match in re.findall(pattern, readme_text):
            lines = match.splitlines()
            if not lines:
                continue
            min_indent = min(
                (len(l) - len(l.lstrip()) for l in lines if l.strip()), default=None
            )
            if min_indent is None:
                continue
            normalized = "\n".join(
                l[min_indent:] if len(l) >= min_indent else l for l in lines
            )
            potential_blocks.append(normalized)

    # Construir candidatos válidos (todos con "path" README.md) y elegir el mejor
    candidates: List[Tuple[str, str]] = []
    for block in potential_blocks:
        try:
            if len(block.strip().split("\n")) >= 2 and ("services:" in block or "image:" in block):
                compose_data = _converter.parse_docker_compose(block)
                if "image" in compose_data:
                    candidates.append(("README.md", block))
        except Exception:
            continue

    best = select_best_compose(candidates, owner, repo)
    return best[2] if best else None


# --- Helpers de red ----------------------------------------------------------

def _fetch_readme(raw_base_url: str, branch: str) -> Optional[str]:
    readme_paths = [f"/{branch}/README.md", f"/{branch}/readme.md"]
    for alt in [b for b in PRIORITY_BRANCHES if b != branch]:
        readme_paths.extend([f"/{alt}/README.md", f"/{alt}/readme.md"])
    for rp in readme_paths:
        try:
            r = requests.get(f"{raw_base_url}{rp}", timeout=15)
            if r.status_code == 200:
                return r.text
        except Exception:
            continue
    return None


def _collect_priority_candidates(raw_base_url: str, branch: str, owner: str, repo: str) -> List[Tuple[str, str]]:
    """Descarga las rutas prioritarias y devuelve los (relpath, texto) válidos.

    Optimización: si encuentra una coincidencia de imagen fuerte (grado >= 2),
    deja de descargar el resto de rutas.
    """
    candidates: List[Tuple[str, str]] = []
    for compose_path in PRIORITY_COMPOSE_PATHS:
        try:
            response = requests.get(f"{raw_base_url}/{branch}{compose_path}", timeout=15)
        except Exception:
            continue
        if response.status_code != 200:
            continue
        if _validate_compose_priority(response.text) < 0:
            continue
        relpath = compose_path.lstrip("/")
        candidates.append((relpath, response.text))
        if _compose_image_grade(response.text, owner, repo) >= 2:
            break
    return candidates


def _collect_tree_candidates(api_base_url: str, raw_base_url: str, branch: str) -> List[Tuple[str, str]]:
    """Fallback: lista el árbol del repo y descarga los mejores composes (acotado)."""
    try:
        contents_response = requests.get(
            f"{api_base_url}/git/trees/{branch}?recursive=1", timeout=15
        )
        if contents_response.status_code != 200:
            return []
        tree = contents_response.json().get("tree", [])
    except Exception:
        return []

    paths = [
        item["path"]
        for item in tree
        if item.get("type") == "blob" and item.get("path") and _is_compose_path(item["path"])
    ]
    # Ordenar por puntuación estática (nombre + ubicación) y descargar las mejores
    paths.sort(key=_path_score, reverse=True)

    candidates: List[Tuple[str, str]] = []
    for path in paths[:_TREE_DOWNLOAD_LIMIT]:
        try:
            fr = requests.get(f"{raw_base_url}/{branch}/{path}", timeout=15)
            if fr.status_code == 200 and _validate_compose_priority(fr.text) >= 0:
                candidates.append((path, fr.text))
        except Exception:
            continue
    return candidates


# --- Orquestación ------------------------------------------------------------

def load_docker_compose_from_github(repo_url: str) -> dict:
    """Busca y carga el docker-compose más probable de un repositorio de GitHub.

    Returns dict con: success, compose_text, branch, directory, filename,
    project_url, support_url, repo_icon_url, description, message.
    """
    result = {
        "success": False,
        "compose_text": "",
        "branch": "",
        "directory": "",
        "filename": "",
        "project_url": "",
        "support_url": "",
        "repo_icon_url": "",
        "description": "",
        "message": "",
    }

    if not repo_url:
        result["message"] = "Por favor, introduce la URL de un repositorio válido."
        return result

    base_url = repo_url.rstrip("/")
    for sep in ("/blob/", "/raw/", "/tree/"):
        if sep in base_url:
            base_url = base_url.split(sep)[0]

    raw_base_url = base_url.replace("github.com", "raw.githubusercontent.com")
    api_base_url = base_url.replace("github.com", "api.github.com/repos")
    owner, repo = _parse_owner_repo(base_url)

    # Determinar rama por defecto
    branch = "main"
    try:
        repo_response = requests.get(api_base_url, timeout=15)
        if repo_response.status_code == 200:
            branch = repo_response.json().get("default_branch", "main")
        else:
            test = requests.get(f"{raw_base_url}/main/README.md", timeout=15)
            if test.status_code != 200:
                branch = "master"
    except Exception:
        pass

    # 1. Rutas prioritarias (descargas raw, no cuentan contra el rate limit de la API)
    candidates = _collect_priority_candidates(raw_base_url, branch, owner, repo)
    best = select_best_compose(candidates, owner, repo)

    # 2. Ampliamos la búsqueda (README + árbol) si el mejor candidato de las rutas
    #    no coincide con la imagen del repo, o si NO trae environment: (puede existir
    #    en el README u otra ruta una versión con environment, preferible a env_file).
    best_has_env = best is not None and _any_service_has_key(best[2], "environment")
    need_more = (
        best is None
        or _compose_image_grade(best[2], owner, repo) == 0
        or not best_has_env
    )
    if need_more:
        extra: List[Tuple[str, str]] = list(candidates)

        readme_text = _fetch_readme(raw_base_url, branch)
        if readme_text:
            block = extract_docker_compose_from_readme(readme_text, owner, repo)
            if block:
                extra.append(("README.md", block))

        extra.extend(_collect_tree_candidates(api_base_url, raw_base_url, branch))

        best = select_best_compose(extra, owner, repo)

    if not best:
        result["message"] = "No se encontró un Docker Compose válido en el repositorio."
        return result

    _score, relpath, compose_text = best
    directory, filename = _split_relpath(relpath)
    result["branch"] = branch
    result["directory"] = directory
    result["filename"] = filename

    compose_data = _converter.parse_docker_compose(compose_text)
    if "image" not in compose_data:
        result["message"] = "El archivo encontrado no contiene el campo 'image' requerido."
        return result

    # URLs automáticas + descripción del repo
    result["project_url"] = base_url
    result["support_url"] = f"{base_url}/releases"
    result["repo_icon_url"] = base_url
    try:
        repo_response = requests.get(api_base_url, timeout=15)
        if repo_response.status_code == 200:
            repo_data = repo_response.json()
            if repo_data.get("description"):
                result["description"] = repo_data["description"]
            elif repo_data.get("name"):
                result["description"] = f"Plantilla para {repo_data['name']}"
    except Exception:
        pass

    result["success"] = True
    result["compose_text"] = compose_text
    result["message"] = "Docker Compose cargado correctamente desde el repositorio."
    return result


def configure_github_urls_from_compose(compose_text: str) -> Optional[dict]:
    """Deduce URLs de GitHub a partir de la imagen del compose."""
    try:
        compose_data = _converter.parse_docker_compose(compose_text)
        if "image" not in compose_data:
            return None
        image_name = compose_data["image"].split(":")[0]
        parts = image_name.split("/")

        if len(parts) == 1:
            user_repo = f"{parts[0]}/{parts[0]}"
        elif len(parts) == 2:
            user_repo = "/".join(parts[:2])
        elif len(parts) >= 3:
            user_repo = "/".join(parts[1:3])
        else:
            return None

        base_url = f"https://github.com/{user_repo}"
        return {
            "project_url": base_url,
            "support_url": f"{base_url}/releases",
            "repo_icon_url": base_url,
        }
    except Exception:
        return None
