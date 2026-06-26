"""Configuración de la aplicación vía variables de entorno."""
import os

VERSION = os.getenv("VERSION", "dev")
DEBUG = int(os.getenv("DEBUG", "0"))
# Carpeta donde se guardan las plantillas (montada en Unraid)
PLANTILLAS_DIR = os.getenv("PLANTILLAS_DIR", os.path.join(os.getcwd(), "plantillas"))
# Carpeta con los estáticos del frontend compilado (Vite build)
STATIC_DIR = os.getenv("STATIC_DIR", os.path.join(os.path.dirname(__file__), "static"))
