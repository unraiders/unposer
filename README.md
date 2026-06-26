# UNPOSER - Docker Compose a Plantillas de Unraid

Una aplicación web que simplifica la conversión de archivos Docker Compose en plantillas XML compatibles con Unraid. La aplicación ofrece una interfaz intuitiva con modo claro/oscuro que guía al usuario a través del proceso de conversión.

## ¿Qué hace UNPOSER?

UNPOSER permite a los usuarios de Unraid convertir sus configuraciones de Docker Compose existentes en plantillas XML que pueden ser utilizadas directamente en la interfaz de Unraid. Esto facilita la migración de contenedores Docker y asegura una configuración correcta en el entorno Unraid, disponiendo de icono, enlace web (si lo tiene), URL de soporte, etc. en el contenedor de Docker levantado.

Si tu Docker Compose tiene varios servicios, UNPOSER genera **una plantilla XML por cada servicio**, pudiendo elegir cuáles convertir y configurar cada contenedor por separado.

### Configuración variables de entorno

| VARIABLE                | NECESARIA | VERSIÓN | VALOR |
|:----------------------- |:---------:| :------:| :-------------|
| DEBUG                   |     ❌    | v0.1.0  | Habilita el modo Debug en el log. (0 = No / 1 = Si) |

La VERSIÓN indica cuando se añadió esa variable o cuando sufrió alguna actualización. Consultar https://github.com/unraiders/unposer/releases

### Ejemplo docker-compose.yml
```yaml
services:
  unposer:
    image: unraiders/unposer
    container_name: unposer
    environment:
      - DEBUG=0    
    ports:
      - 8000:8000
    restart: unless-stopped
    network_mode: bridge
    volumes:
      - /boot/config/plugins/dockerMan/templates-user:/app/plantillas
```

---

### Instalación plantilla en Unraid.

- Nos vamos a una ventana de terminal en nuestro Unraid, pegamos esta línea y enter:
```sh
wget -O /boot/config/plugins/dockerMan/templates-user/my-unposer.xml https://raw.githubusercontent.com/unraiders/unposer/refs/heads/main/my-unposer.xml
```
- Nos vamos a DOCKER y abajo a la izquierda tenemos el botón "AGREGAR CONTENEDOR" hacemos click y en seleccionar plantilla seleccionamos unposer y botón "Aplicar".

---

## Preview Compose 😎

![alt text](https://github.com/unraiders/imagenes/blob/main/unposer_compose.png)

## Preview Opciones 😎

![alt text](https://github.com/unraiders/imagenes/blob/main/unposer_options.png)

## Preview Template 😎

![alt text](https://github.com/unraiders/imagenes/blob/main/unposer_template.png)


## Características Principales

### 🔄 Múltiples Métodos de Entrada
- **Entrada Manual**: Pega directamente tu docker-compose con validación en tiempo real.
- **Carga Local**: Arrastra y suelta tu archivo docker-compose.
- **Integración GitHub**: Carga directamente desde repositorios, con detección automática de archivos docker-compose.

### 📦 Soporte Multiservicio
- Genera una plantilla XML por cada servicio del docker-compose.
- Incluir o excluir servicios concretos (p. ej. una base de datos interna).
- Configuración independiente por contenedor (icono, puerto, descripción, soporte, proyecto y categoría).

### 🎨 Personalización Completa
- **Iconos Personalizados**: 
  - Usa URLs externas o selecciona desde repositorios.
  - Vista previa en tiempo real.
  - Validación automática de imágenes.

- **Configuración Web**: 
  - Selección inteligente de puertos.
  - Configuración automática de la interfaz web.
  - Detección de puertos del docker-compose.

- **Metadatos Enriquecidos**:
  - Descripción detallada del contenedor.
  - Enlaces a documentación y soporte.
  - Categorización para mejor organización.

### 📝 Editor Avanzado
- Editor Monaco integrado con resaltado de sintaxis XML.
- Edición manual de la plantilla final.
- Validación en tiempo real del formato.
- Autocompletado de etiquetas XML.

### 🔍 Características Inteligentes
- Detección automática de configuraciones.
- Mapeo inteligente de variables y volúmenes.
- Autocompletado de URLs de soporte y proyecto.
- Validación en tiempo real.

### 💡 Ayuda Contextual
- Mensajes toast informativos en cada paso.
- Info hovers con explicaciones detalladas.
- Validación y retroalimentación inmediata.
- Guía paso a paso en el proceso.

### 🎯 Resultado Final
- Plantillas XML perfectamente formateadas.
- Compatibilidad garantizada con Unraid.
- Descarga local de plantillas desde el navegador (un XML concreto o todos en un ZIP).
- Descarga de plantillas en el contenedor que mapeando la unidad del host /boot/config/plugins/dockerMan/templates-user:/app/plantillas la tendremos disponible para su instalación en Unraid.
- Nombres de archivo generados automáticamente con la combinación my-<nombre_contenedor>.xml.

## Porqué UNPOSER?

UNPOSER nace de la necesidad de simplificar la migración de contenedores Docker a Unraid. En lugar de crear manualmente las plantillas XML o modificar configuraciones existentes, UNPOSER automatiza el proceso mientras permite una personalización completa. Ideal para:

- Administradores de sistemas migrando a Unraid
- Usuarios de Docker que quieren aprovechar la interfaz de Unraid
- Desarrolladores que necesitan crear plantillas Unraid para sus aplicaciones
- Entusiastas del homelabbing que gestionan múltiples contenedores


Fin.
