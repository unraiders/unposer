# UNPOSER v2 — Docker Compose a Plantillas de Unraid

Reescritura de [UNPOSER](../unposer) abandonando **Reflex** en favor de un stack
desacoplado: **React + Vite + TypeScript + Tailwind + shadcn/ui** en el frontend y
**FastAPI** en el backend, empaquetados en **una sola imagen Docker**.

La lógica de conversión docker-compose → XML de Unraid es la misma del proyecto
original (`UnraidTemplateConverter`), portada a Python puro sin dependencias de Reflex.

## ¿Qué hace?

Convierte un `docker-compose.yml` en una plantilla XML lista para usar en Unraid,
con icono, enlace web, URL de soporte/proyecto, categoría, etc. Soporta tres métodos
de entrada (pegado manual, drag & drop y carga desde un repositorio de GitHub),
personalización de icono/puerto/metadatos, edición final en un editor Monaco y
descarga local o guardado directo en la carpeta de plantillas de Unraid.

## Mejora frente a la v1

El frontend ya **no se exporta en build-time**, por lo que **desaparece la atadura al
puerto 25500**. Ahora hay un único proceso (Uvicorn) y puedes mapear el puerto que
quieras (`-p loquesea:8000`).

## Arquitectura

```
unposerv2/
├── backend/            FastAPI + converter portado
│   └── app/
│       ├── main.py     monta /api y sirve los estáticos del front (SPA)
│       ├── api/routes.py
│       ├── core/       converter.py, github.py, mappings.py
│       └── config_data/template_unraid_xml.txt
├── frontend/           React + Vite + Tailwind + shadcn/ui
│   └── src/
│       ├── store/useAppStore.ts   estado global (Zustand)
│       ├── api/client.ts
│       └── components/            Header, Footer, tabs/, ui/
└── Dockerfile          multi-stage: node build → python runtime (imagen única)
```

En producción, FastAPI sirve el `dist/` de Vite y la API bajo `/api` en el mismo
origen y puerto (sin CORS, sin Caddy).

## Desarrollo

Dos procesos, conectados por el proxy de Vite (`/api` → `localhost:8000`):

```sh
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000

# Frontend (en otra terminal)
cd frontend
npm install
npm run dev                     # http://localhost:3000
```

Tests del núcleo de conversión:

```sh
cd backend
pip install pytest
pytest
```

## Producción (Docker)

```sh
docker build --build-arg VERSION=0.1.0 -t unposerv2 .
docker run -p 8000:8000 \
  -v /boot/config/plugins/dockerMan/templates-user:/app/plantillas \
  unposerv2
```

O con `docker compose up --build`. Abre `http://<host>:8000`.

### Variables de entorno

| Variable        | Por defecto      | Descripción                                            |
|-----------------|------------------|--------------------------------------------------------|
| `DEBUG`         | `0`              | Nivel de log (0 = INFO, 1 = DEBUG).                    |
| `VERSION`       | `dev`            | Versión mostrada en el footer y en `/api/health`.     |
| `PLANTILLAS_DIR`| `/app/plantillas`| Carpeta donde se guardan los XML (volumen de Unraid). |
| `STATIC_DIR`    | `app/static`     | Carpeta de estáticos del frontend compilado.          |

### Volumen para Unraid

Montando `/boot/config/plugins/dockerMan/templates-user:/app/plantillas`, el botón
"Guardar en la carpeta de plantillas Unraid" deja el XML directamente disponible
para instalarlo desde la interfaz de Docker de Unraid. Los archivos se nombran
`my-<nombre_contenedor>.xml`.
