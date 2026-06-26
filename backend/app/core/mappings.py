"""Mapeos de campos docker-compose / app hacia etiquetas XML de Unraid.

Antes vivían en archivos `.dic` que se cargaban con ``eval()``. Aquí se definen
como diccionarios Python literales (mismo contenido, sin ``eval``).
"""

# Mapeo de los campos del docker-compose con las etiquetas de la plantilla de Unraid.
MAPEO_COMPOSE: dict[str, str] = {
    "container_name": "Name",
    "image": "Repository",
    "environment": "Variable",
    "labels": "Label",
    "volumes": "Path",
    "ports": "Port",
    "devices": "Device",
    "command": "PostArgs",
    "network_mode": "Network",
    "privileged": "Privileged",
    "tty": "ExtraParams",
    "init": "ExtraParams",
    "stdin_open": "ExtraParams",
}

# Mapeo de etiquetas de la plantilla que se rellenan desde la aplicación
# (no del docker-compose).
MAPEO_APP: dict[str, str] = {
    "Overview": "Overview",      # Descripción proporcionada por el usuario
    "Icon": "Icon",              # URL del icono seleccionado por el usuario
    "TemplateURL": "TemplateURL",  # URL del template (si aplica)
    "Category": "Category",      # Categoría seleccionada por el usuario
    "Project": "Project",        # URL del proyecto o repositorio
    "Support": "Support",        # URL de soporte
}
