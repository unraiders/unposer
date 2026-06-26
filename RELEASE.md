# Cambios en esta versión

## 🐞 Correcciones

- **Selección del docker-compose en repos que usan `env_file`.** Cuando el compose principal de un repo coincidía con su imagen pero usaba `env_file:` (un `.env` externo que no tenemos), se elegía ese y no se generaban variables. Ahora, en ese caso, la búsqueda también consulta el README y el árbol del repo para encontrar una versión con `environment:`.

## 🔧 Mejoras

- **Preferencia `environment:` sobre `env_file:`.** Entre todos los composes encontrados (fichero, README o árbol del repo), se prioriza el que define `environment:` (variables inline convertibles a `<Config Type="Variable">`) frente al que usa `env_file:`. La coincidencia imagen↔repo sigue siendo la señal dominante, de modo que la preferencia solo desempata entre composes del mismo contenedor.
