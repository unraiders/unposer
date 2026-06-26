"""Transformaciones sobre el texto del docker-compose.

Operan sobre el texto crudo (no sobre el YAML parseado) para preservar
comentarios, orden y formato del resto del archivo; solo se reescriben las
líneas de volúmenes afectadas.
"""
import re

from app.core.converter import UnraidTemplateConverter

_converter = UnraidTemplateConverter()


def convert_host_paths_to_appdata(compose_text: str) -> str:
    """Reescribe el lado host de cada volumen a /mnt/user/appdata/<container><container_path>.

    Para un volumen ``host:container[:mode]`` deja
    ``/mnt/user/appdata/<container_name><container_path>:container[:mode]``,
    conservando el path del contenedor y el modo. Convierte también los
    volúmenes nombrados (``cache:/cache`` -> bind hacia appdata).
    """
    data = _converter.parse_docker_compose(compose_text)
    container_name = data.get("container_name") if data else None
    if not container_name:
        return compose_text

    base = f"/mnt/user/appdata/{container_name}"
    lines = compose_text.split("\n")
    out = []
    in_volumes = False
    volumes_indent = -1

    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        # Entrada al bloque "volumes:"
        if re.match(r"^volumes:\s*(#.*)?$", stripped):
            in_volumes = True
            volumes_indent = indent
            out.append(line)
            continue

        if in_volumes:
            if stripped.startswith("- "):
                dash_indent = indent
                item = stripped[2:].strip()

                # Conservar comentario en línea, si lo hubiera
                comment = ""
                m = re.search(r"\s+(#.*)$", item)
                if m:
                    comment = f"  {m.group(1)}"
                    item = item[: m.start()].rstrip()

                # Conservar comillas envolventes
                quote = ""
                if len(item) >= 2 and item[0] in "\"'" and item[-1] == item[0]:
                    quote = item[0]
                    item = item[1:-1]

                parts = item.split(":")
                # host:container[:mode] con path de contenedor absoluto
                if len(parts) >= 2 and parts[1].startswith("/") and not item.startswith("$"):
                    container_path = parts[1]
                    mode = parts[2] if len(parts) >= 3 else None
                    new_item = f"{base}{container_path}:{container_path}"
                    if mode:
                        new_item += f":{mode}"
                    if quote:
                        new_item = f"{quote}{new_item}{quote}"
                    out.append(f"{' ' * dash_indent}- {new_item}{comment}")
                    continue

                out.append(line)
                continue

            # Salida del bloque volumes al bajar la indentación con una nueva clave
            if stripped and indent <= volumes_indent:
                in_volumes = False
            out.append(line)
            continue

        out.append(line)

    return "\n".join(out)
