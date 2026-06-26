# Cambios en esta versión

## ✨ Novedades

- **Primera versión de UNPOSER.** Reescritura completa abandonando Reflex en favor de un stack desacoplado: **React + Vite + TypeScript + Tailwind + shadcn/ui** en el frontend y **FastAPI** en el backend, empaquetados en una **única imagen Docker**.
- **Soporte multiservicio.** Un `docker-compose` con varios servicios genera **una plantilla XML por servicio**. Se pueden **incluir/excluir** contenedores (p. ej. una base de datos interna) y configurar **cada uno por separado** (icono, puerto web, descripción, soporte, proyecto y categoría).
- **Pestaña de resultado con sub-tabs por XML**, editor Monaco por plantilla y descarga de **un XML concreto** o **todos** (ZIP en local o en la carpeta de plantillas de Unraid).
- **Sin atadura de puerto.** El frontend ya no se exporta en build-time, así que desaparece la limitación del puerto fijo: un único proceso (Uvicorn) y mapeo de puerto libre.

## 🔧 Mejoras

- **Búsqueda más fiable del docker-compose en repos remotos:** reconoce `compose.yaml`/`compose.yml` (Compose Spec), usa la coincidencia imagen↔repo como señal dominante y puntúa candidatos (penalizando `examples/`, `test/`, `docs/`).
- **Validación estricta del compose** por estructura real (claves) en lugar de subcadenas, eliminando falsos positivos.
- Soporte de la forma de **mapa** en `environment` (`KEY: value`) además de la lista (`- KEY=value`).
- Botón reversible para **reescribir host paths a `/mnt/user/appdata/<contenedor>`**.

## 🚀 CI/CD

- Workflow `despliegue.yml`: en cada push a `main` o `develop` crea tag + release en GitHub y publica la imagen `linux/amd64` en **DockerHub** (`unraiders/unposer`) y **GHCR** (`ghcr.io/unraiders/unposer`).
- La versión se gestiona por rama mediante los ficheros `.version_main` y `.version_develop`, que se inyectan en la imagen vía `--build-arg`.
- El `Dockerfile` usa `ARG VERSION=local` como valor por defecto, de modo que los builds manuales se identifican como `local` mientras que los builds del workflow muestran la versión real.
