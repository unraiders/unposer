"""
Módulo para convertir un Docker Compose a plantilla Unraid.
"""
import os
import yaml
import re
import requests
from typing import Dict, List, Any
from datetime import datetime

from unposer.utils.utils import setup_logger, generate_trace_id

logger = setup_logger(__name__)

# Constantes
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
TEMPLATE_PATH = os.path.join(CONFIG_DIR, "template_unraid_xml.txt")
MAPEO_COMPOSE_PATH = os.path.join(CONFIG_DIR, "mapeo_compose.dic")
MAPEO_APP_PATH = os.path.join(CONFIG_DIR, "mapeo_app.dic")

class UnraidTemplateConverter:
    generate_trace_id()
    
    def __init__(self):
        """Inicializa el conversor con los mapeos de campos."""

        # Inicializar con diccionarios vacíos
        self.mapeo_compose = {}
        # El mapeo_app no necesita inicialización especial, ya que las claves
        # del diccionario app_fields coinciden directamente con las etiquetas XML
        
        # Cargar los mapeos desde los archivos (requeridos)
        self._cargar_mapeos()
        self.template_base = self._cargar_template_base()
        
    def _cargar_mapeos(self):
        """Carga los mapeos desde los archivos."""
        self._cargar_mapeo_compose()
        self._cargar_mapeo_app()
        
    def _cargar_mapeo_compose(self) -> Dict[str, str]:
        """Carga el mapeo de campos de Docker Compose a etiquetas Unraid."""
        try:
            # Verificar si existe el archivo
            logger.debug(f"Verificando archivo en: {MAPEO_COMPOSE_PATH}")
            if os.path.exists(MAPEO_COMPOSE_PATH):
                logger.debug(f"Archivo encontrado en: {MAPEO_COMPOSE_PATH}")
                with open(MAPEO_COMPOSE_PATH, "r") as file:
                    content = file.read()
                    self.mapeo_compose = eval(content)
                    return self.mapeo_compose
            
            # Si no se encuentra el archivo, mostramos un error
            logger.debug(f"ERROR: No se encontró el archivo de mapeo obligatorio en {MAPEO_COMPOSE_PATH}")
            raise FileNotFoundError(f"El archivo de mapeo obligatorio {MAPEO_COMPOSE_PATH} no existe")
        except Exception as e:
            logger.debug(f"Error al cargar el mapeo de compose: {str(e)}")
            raise Exception(f"No se pudo cargar el mapeo desde {MAPEO_COMPOSE_PATH}: {str(e)}")
            
    def _cargar_mapeo_app(self) -> Dict[str, str]:
        """Carga el mapeo de campos de la aplicación a etiquetas Unraid."""
        try:
            # Verificar si existe el archivo
            logger.debug(f"Verificando archivo en: {MAPEO_APP_PATH}")
            if os.path.exists(MAPEO_APP_PATH):
                logger.debug(f"Archivo encontrado en: {MAPEO_APP_PATH}")
                with open(MAPEO_APP_PATH, "r") as file:
                    content = file.read()
                    self.mapeo_app = eval(content)
                    logger.debug(f"Contenido de mapeo_app cargado: {self.mapeo_app}")
                    return self.mapeo_app
            
            # Si no se encuentra el archivo, mostramos un error
            logger.debug(f"ERROR: No se encontró el archivo de mapeo obligatorio en {MAPEO_APP_PATH}")
            raise FileNotFoundError(f"El archivo de mapeo obligatorio {MAPEO_APP_PATH} no existe")
        except Exception as e:
            logger.debug(f"Error al cargar el mapeo de app: {str(e)}")
            raise Exception(f"No se pudo cargar la plantilla base desde {MAPEO_APP_PATH}: {str(e)}")

    def _cargar_template_base(self) -> str:
        """Carga la plantilla base desde el archivo de configuración."""
        try:
            logger.debug(f"Verificando archivo de plantilla en: {TEMPLATE_PATH}")
            if os.path.exists(TEMPLATE_PATH):
                logger.debug(f"Archivo de plantilla encontrado en: {TEMPLATE_PATH}")
                with open(TEMPLATE_PATH, "r") as file:
                    return file.read()
            
            # Si no se encuentra el archivo, mostramos un error
            logger.debug(f"ERROR: No se encontró el archivo de plantilla obligatorio en {TEMPLATE_PATH}")
            raise FileNotFoundError(f"El archivo de plantilla obligatorio {TEMPLATE_PATH} no existe")
        except Exception as e:
            logger.debug(f"Error al cargar la plantilla base: {str(e)}")
            raise Exception(f"No se pudo cargar la plantilla base desde {TEMPLATE_PATH}: {str(e)}")

    def parse_docker_compose(self, docker_compose_content: str) -> Dict[str, Any]:
        """
        Parsea el contenido del docker-compose y devuelve un diccionario con los valores relevantes.
        """
        try:
            # Convertir el contenido a un diccionario de Python
            docker_compose = yaml.safe_load(docker_compose_content)
            
            # Verificar si el archivo tiene la estructura esperada
            if 'services' not in docker_compose:
                raise ValueError("El archivo Docker Compose no tiene la sección 'services'")
                
            # Tomar el primer servicio si hay varios
            service_name = list(docker_compose['services'].keys())[0]
            service = docker_compose['services'][service_name]
            
            # Si no hay container_name definido, usar el nombre del servicio
            if 'container_name' not in service:
                service['container_name'] = service_name
            
            # Normalizar el formato de etiquetas para asegurar que sea una lista
            if 'labels' in service:
                # Si labels es un diccionario, convertirlo a una lista de strings con el formato clave=valor
                if isinstance(service['labels'], dict):
                    service['labels'] = [f"{k}={v}" for k, v in service['labels'].items()]
                # Asegurarse de que es una lista
                elif not isinstance(service['labels'], list):
                    service['labels'] = [service['labels']]
            
            # Normalizar el formato de dispositivos para asegurar que sea una lista
            if 'devices' in service:
                # Si devices es un diccionario, convertirlo a una lista
                if isinstance(service['devices'], dict):
                    service['devices'] = [f"{k}:{v}" for k, v in service['devices'].items()]
                # Asegurarse de que es una lista
                elif not isinstance(service['devices'], list):
                    service['devices'] = [service['devices']]
                
                # Imprimir para debug
                logger.debug(f"Dispositivos normalizados: {service['devices']}")
            
            return service
        except Exception as e:
            logger.debug(f"Error al parsear el Docker Compose: {str(e)}")
            return {}

    def get_github_repo_images(self, repo_url: str) -> List[str]:
        """
        Obtiene todos los archivos de imagen (.jpg, .jpeg, .png, .ico) del repositorio de GitHub.
        """
        try:
            # Verificar si la URL es de GitHub
            if not repo_url.startswith("https://github.com/"):
                return []
            
            # Extraer el owner y el nombre del repositorio de la URL
            # Formato: https://github.com/{owner}/{repo}
            parts = repo_url.strip("/").split("/")
            if len(parts) < 5:
                logger.debug(f"URL de GitHub inválida: {repo_url}")
                return []
            
            owner = parts[3]
            repo = parts[4]
            
            # Construir la URL de la API de GitHub para obtener el contenido del repositorio
            api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
            
            # Hacer la solicitud a la API
            response = requests.get(api_url)
            if response.status_code == 404:
                # Si no encontramos la rama 'main', intentamos con 'master'
                api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
                response = requests.get(api_url)
                
            if response.status_code != 200:
                logger.debug(f"Error al acceder a la API de GitHub: {response.status_code}")
                return []
            
            # Obtener los datos de la respuesta
            data = response.json()
            
            # Buscar archivos de imagen
            images = []
            for item in data.get('tree', []):
                if item.get('type') == 'blob':  # Es un archivo
                    path = item.get('path', '')
                    if any(path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.ico', '.gif', '.svg']):
                        # Construir la URL para la imagen raw
                        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{'main' if 'main' in api_url else 'master'}/{path}"
                        images.append(raw_url)
            
            return images
        except Exception as e:
            logger.debug(f"Error al obtener imágenes del repositorio: {str(e)}")
            return []

    def generate_unraid_template(self, 
                                docker_compose: Dict[str, Any], 
                                icon_url: str = "", 
                                description: str = "",
                                web_port: str = "",
                                app_fields: Dict[str, str] = None) -> str:
        """
        Genera la plantilla de Unraid a partir del Docker Compose.
        
        Args:
            docker_compose: Diccionario con los datos del Docker Compose.
            icon_url: URL del icono para la plantilla (mantenido por compatibilidad).
            description: Descripción para la plantilla (mantenido por compatibilidad).
            web_port: Puerto web seleccionado para la etiqueta WebUI (formato "host:container").
            app_fields: Diccionario con campos adicionales de la aplicación.
        """
        try:
            # Verificar que tenemos los mapeos necesarios
            if not self.mapeo_compose or not self.mapeo_app:
                raise ValueError("Los mapeos de campos necesarios no están disponibles. No se puede generar la plantilla.")
                
            # Crear una copia de la plantilla base
            template = self.template_base
            
            # Extraer el registro de la imagen si está presente
            registry = ""
            if 'image' in docker_compose and docker_compose['image']:
                registry = self.extract_registry_from_image(docker_compose['image'])
                # Aplicar el registro a la etiqueta Registry en la plantilla
                template = re.sub('<Registry>(.*?)</Registry>', f'<Registry>{registry}</Registry>', template)
            
            # Aplicar mapeo directo de campos del docker-compose a etiquetas XML
            for compose_key, unraid_tag in self.mapeo_compose.items():
                if compose_key in docker_compose and docker_compose[compose_key]:
                    # Caso especial para el comando, que podría ser una lista
                    if compose_key == 'command':
                        command_value = docker_compose[compose_key]
                        # Si command es una lista, lo convertimos en una cadena
                        if isinstance(command_value, list):
                            command_value = ' '.join(command_value)
                        # Reemplazamos la etiqueta PostArgs con el valor del comando
                        tag_pattern = f'<{unraid_tag}>(.*?)</{unraid_tag}>'
                        replacement = f'<{unraid_tag}>{command_value}</{unraid_tag}>'
                        template = re.sub(tag_pattern, replacement, template)
                        continue  # Saltamos al siguiente campo
                    
                    # Caso especial para privileged: tiene su propia etiqueta en la plantilla de Unraid
                    if compose_key == 'privileged':
                        # Privileged se maneja directamente con su etiqueta: <Privileged>true|false</Privileged>
                        value = str(docker_compose[compose_key]).lower()  # Convertir a string "true" o "false"
                        tag_pattern = f'<{unraid_tag}>(.*?)</{unraid_tag}>'
                        replacement = f'<{unraid_tag}>{value}</{unraid_tag}>'
                        template = re.sub(tag_pattern, replacement, template)
                        continue  # Saltamos al siguiente campo
                        
                    # Casos especiales para opciones booleanas que deben transformarse en flags de línea de comandos
                    bool_flag_options = {
                        'tty': '--tty',
                        'init': '--init',
                        'read_only': '--read-only',
                        'stdin_open': '--interactive'
                    }
                    
                    if compose_key in bool_flag_options and docker_compose[compose_key] is True:
                        # Si la opción booleana es true, agregamos el flag correspondiente
                        tag_pattern = f'<{unraid_tag}>(.*?)</{unraid_tag}>'
                        
                        # Si ya hay contenido en la etiqueta, lo preservamos y añadimos el nuevo flag
                        match = re.search(tag_pattern, template)
                        current_content = match.group(1) if match else ""
                        
                        # Si ya hay contenido, agregamos un espacio antes del nuevo flag
                        new_content = f"{current_content} {bool_flag_options[compose_key]}".strip()
                        
                        replacement = f'<{unraid_tag}>{new_content}</{unraid_tag}>'
                        template = re.sub(tag_pattern, replacement, template)
                        continue  # Saltamos al siguiente campo
                    
                    # Procesamiento normal para otros campos
                    # Usamos expresiones regulares para encontrar y reemplazar dentro de las etiquetas
                    tag_pattern = f'<{unraid_tag}>(.*?)</{unraid_tag}>'
                    replacement = f'<{unraid_tag}>{docker_compose[compose_key]}</{unraid_tag}>'
                    template = re.sub(tag_pattern, replacement, template)
            
            # Aplicar mapeo directo de campos de la aplicación a etiquetas XML
            logger.debug(f"mapeo_app actual: {self.mapeo_app}")
            logger.debug(f"app_fields recibidos: {app_fields}")
            
            if app_fields and self.mapeo_app:
                for app_key, value in app_fields.items():
                    logger.debug(f"Procesando app_key: {app_key}, value: {value}")
                    if app_key in self.mapeo_app and value:
                        unraid_tag = self.mapeo_app[app_key]
                        logger.debug(f"unraid_tag encontrado: '{unraid_tag}'")
                        if unraid_tag:  # Asegurarse de que no está vacío
                            tag_pattern = f'<{unraid_tag}>(.*?)</{unraid_tag}>'
                            replacement = f'<{unraid_tag}>{value}</{unraid_tag}>'
                            template = re.sub(tag_pattern, replacement, template)
                            logger.debug(f"Aplicando mapeo app: <{unraid_tag}> = {value}")
                        else:
                            logger.debug(f"ERROR - El mapeo para {app_key} está vacío")
            
            # Para mantener compatibilidad con el código existente
            # Estos parámetros son redundantes con app_fields, pero se mantienen por compatibilidad
            if icon_url and not (app_fields and "Icon" in app_fields):
                template = re.sub('<Icon>(.*?)</Icon>', f'<Icon>{icon_url}</Icon>', template)
            
            if description and not (app_fields and "Overview" in app_fields):
                template = re.sub('<Overview>(.*?)</Overview>', f'<Overview>{description}</Overview>', template)
            
            # Reemplazar la fecha de instalación con la fecha actual
            current_timestamp = str(int(datetime.now().timestamp()))
            template = re.sub('<DateInstalled>(.*?)</DateInstalled>', f'<DateInstalled>{current_timestamp}</DateInstalled>', template)
            
            # Configurar WebUI si se proporciona un puerto web
            if web_port:
                try:
                    host_port, container_port = web_port.split(':')
                    webui_url = f'http://[IP]:[PORT:{host_port}]/'
                    template = re.sub('<WebUI>(.*?)</WebUI>', f'<WebUI>{webui_url}</WebUI>', template)
                except Exception as e:
                    logger.debug(f"Error al configurar WebUI con puerto {web_port}: {str(e)}")
            
            # Generar configuraciones para variables de entorno, volúmenes y puertos
            config_sections = []
            
            # Procesar variables de entorno
            if 'environment' in docker_compose and docker_compose['environment']:
                for env in docker_compose['environment']:
                    if isinstance(env, str) and '=' in env:
                        key, value = env.split('=', 1)
                        config_sections.append(f'  <Config Name="{key}" Target="{key}" Default="" Mode="" Description="" Type="Variable" Display="always" Required="false" Mask="false">{value}</Config>')
                    elif isinstance(env, dict):
                        for k, v in env.items():
                            config_sections.append(f'  <Config Name="{k}" Target="{k}" Default="" Mode="" Description="" Type="Variable" Display="always" Required="false" Mask="false">{v}</Config>')
            
            # Procesar labels
            if 'labels' in docker_compose and docker_compose['labels']:
                # Debug para verificar el formato de las etiquetas
                logger.debug(f"Procesando etiquetas: {docker_compose['labels']}")
                
                for label in docker_compose['labels']:
                    if isinstance(label, str) and '=' in label:
                        key, value = label.split('=', 1)
                        # Limpiar posibles comillas en el valor
                        value = value.strip("'\"")
                        logger.debug(f"Agregando etiqueta: {key}={value}")
                        config_sections.append(f'  <Config Name="{key}" Target="{key}" Default="" Mode="" Description="" Type="Label" Display="always" Required="false" Mask="false">{value}</Config>')
                    elif isinstance(label, dict):
                        for k, v in label.items():
                            # Limpiar posibles comillas en el valor
                            v = str(v).strip("'\"")
                            logger.debug(f"Agregando etiqueta (dict): {k}={v}")
                            config_sections.append(f'  <Config Name="{k}" Target="{k}" Default="" Mode="" Description="" Type="Label" Display="always" Required="false" Mask="false">{v}</Config>')
            
            # Procesar volúmenes
            if 'volumes' in docker_compose and docker_compose['volumes']:
                for vol in docker_compose['volumes']:
                    if isinstance(vol, str) and ':' in vol:
                        parts = vol.split(':')
                        host_path = parts[0]
                        container_path = parts[1]
                        mode = parts[2] if len(parts) > 2 else "rw"
                        name = os.path.basename(container_path)
                        config_sections.append(f'  <Config Name="{name}" Target="{container_path}" Default="" Mode="{mode}" Description="" Type="Path" Display="always" Required="false" Mask="false">{host_path}</Config>')
            
            # Procesar puertos
            if 'ports' in docker_compose and docker_compose['ports']:
                for port in docker_compose['ports']:
                    if isinstance(port, str) and ':' in port:
                        host_port, container_port = port.split(':', 1)
                        protocol = "tcp"
                        if '/' in container_port:
                            container_port, protocol = container_port.split('/', 1)
                        config_sections.append(f'  <Config Name="Puerto {container_port}" Target="{container_port}" Default="" Mode="{protocol}" Description="" Type="Port" Display="always" Required="false" Mask="false">{host_port}</Config>')
                        
            # Procesar dispositivos
            if 'devices' in docker_compose and docker_compose['devices']:
                # Debug para verificar el formato de los dispositivos
                logger.debug(f"Procesando dispositivos: {docker_compose['devices']}")
                
                for device in docker_compose['devices']:
                    if isinstance(device, str):
                        # Limpiar el valor del dispositivo
                        device_value = device.strip("'\"")
                        device_name = device_value.split('/')[-1] if '/' in device_value else device_value
                        
                        # Verificar si el dispositivo tiene formato host:container
                        if ':' in device_value:
                            host_device, container_device = device_value.split(':', 1)
                            logger.debug(f"Agregando dispositivo mapeado: {host_device} -> {container_device}")
                            config_sections.append(f'  <Config Name="Dispositivo {device_name}" Target="{container_device}" Default="" Mode="" Description="" Type="Device" Display="always" Required="false" Mask="false">{host_device}</Config>')
                        else:
                            # Caso donde el dispositivo es el mismo en host y contenedor
                            logger.debug(f"Agregando dispositivo directo: {device_value}")
                            config_sections.append(f'  <Config Name="Dispositivo {device_name}" Target="{device_value}" Default="" Mode="" Description="" Type="Device" Display="always" Required="false" Mask="false">{device_value}</Config>')
                    elif isinstance(device, dict):
                        # Caso para formatos más complejos de dispositivos
                        for path_host, path_container in device.items():
                            device_name = path_container.split('/')[-1] if '/' in path_container else path_container
                            logger.debug(f"Agregando dispositivo (dict): {path_host} -> {path_container}")
                            config_sections.append(f'  <Config Name="Dispositivo {device_name}" Target="{path_container}" Default="" Mode="" Description="" Type="Device" Display="always" Required="false" Mask="false">{path_host}</Config>')
            
            # Eliminar todas las etiquetas Config existentes
            config_pattern = r'<Config.*?</Config>'
            template = re.sub(config_pattern, '', template, flags=re.DOTALL)
            
            # Insertar las nuevas configuraciones antes de cerrar el contenedor
            if config_sections:
                all_configs = '\n'.join(config_sections)
                template = template.replace('</Container>', f'{all_configs}\n</Container>')
            
            # Limpiar la plantilla al final del proceso con una limpieza más exhaustiva
            # 1. Reemplazar múltiples líneas en blanco por una sola
            template = re.sub(r'\n{2,}', '\n', template)
            
            # 2. Asegurar que haya una indentación consistente (2 espacios) para elementos dentro de Container
            lines = template.split('\n')
            cleaned_lines = []
            
            # Procesamos la declaración XML y la etiqueta Container de apertura tal cual están
            if lines and lines[0].startswith('<?xml'):
                cleaned_lines.append(lines[0])
                
            container_start_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('<Container'):
                    container_start_idx = i
                    cleaned_lines.append(line)
                    break
            
            # Si no encontramos la etiqueta Container, usamos los índices por defecto
            if container_start_idx == -1:
                container_start_idx = 0 if not cleaned_lines else 1
                
            # Procesar todas las líneas entre Container de apertura y cierre con indentación
            for i in range(container_start_idx + 1, len(lines) - 1):  # -1 para excluir el </Container>
                line = lines[i].strip()
                if not line:  # Ignorar líneas vacías
                    continue
                    
                if line.startswith('</'):  # Es una etiqueta de cierre
                    cleaned_lines.append(f"  {line}")
                elif line.startswith('<'):  # Es una etiqueta de apertura o auto-cerrada
                    cleaned_lines.append(f"  {line}")
                else:  # Es contenido de texto
                    cleaned_lines.append(f"  {line}")
            
            # Agregar la etiqueta Container de cierre
            if '</Container>' in lines[-1]:
                cleaned_lines.append('</Container>')
            else:
                # Buscar la última etiqueta Container de cierre
                for i in range(len(lines)-1, -1, -1):
                    if '</Container>' in lines[i]:
                        cleaned_lines.append(lines[i])
                        break
                else:
                    # Si no encontramos la etiqueta de cierre, la añadimos
                    cleaned_lines.append('</Container>')
            
            # Recrear la plantilla con las líneas limpias
            template = '\n'.join(cleaned_lines)
            
            return template
        except Exception as e:
            logger.debug(f"Error al generar la plantilla: {str(e)}")
            return ""

    def extract_ports(self, docker_compose: Dict[str, Any]) -> List[str]:
        """
        Extrae los puertos definidos en el Docker Compose.
        Retorna una lista de puertos en formato [host_port]:[container_port].
        """
        ports = []
        if 'ports' in docker_compose:
            for port in docker_compose['ports']:
                if ':' in port:
                    ports.append(port.split('/')[0] if '/' in port else port)
                else:
                    # Si solo se especifica un puerto (sin mapeo), es el mismo en host y contenedor
                    ports.append(f"{port}:{port}".split('/')[0] if '/' in port else port)
        return ports

    def create_app_fields_example(self, description: str, icon_url: str, category: str, project_url: str, support_url: str) -> Dict[str, str]:
        """
        Crea un diccionario de ejemplo con los campos específicos de la aplicación.
        
        Args:
            description: Descripción para la plantilla.
            icon_url: URL del icono para la plantilla.
            category: Categoría de la plantilla.
            project_url: URL del proyecto.
            support_url: URL de soporte.
            
        Returns:
            Diccionario con los campos de la aplicación mapeados.
        """
        # Ejemplo de cómo crear el diccionario app_fields para usar en generate_unraid_template
        app_fields = {
            "Overview": description,
            "Icon": icon_url,
            "Category": category,
            "Project": project_url,
            "Support": support_url
        }
        return app_fields

    def extract_registry_from_image(self, image_name: str) -> str:
        """
        Extrae el registro de una imagen Docker y construye URLs apropiadas para todos los registros.
        
        Args:
            image_name: Nombre completo de la imagen Docker (ej: 'ghcr.io/usuario/repo:tag')
            
        Returns:
            URL completa al repositorio según el registro:
            - Docker Hub: 'https://hub.docker.com/r/usuario/repo'
            - GitHub Container Registry: 'https://github.com/usuario/repo/pkgs/container/repo'
            - Otros registros: URL adaptada según el formato correspondiente
        """
        # Eliminar la etiqueta si existe
        if ':' in image_name:
            image_name = image_name.split(':')[0]
        
        # Si la imagen contiene una URL de registro, la extraemos
        if '/' in image_name:
            parts = image_name.split('/')
            
            # Si el primer segmento contiene puntos o :, es probablemente un registro personalizado
            if '.' in parts[0] or ':' in parts[0]:
                registry = parts[0]
                # Extraer usuario y repo (puede haber más de un nivel)
                repo_path = '/'.join(parts[1:])
                
                # Casos especiales para registros conocidos
                if registry == 'ghcr.io':
                    # GitHub Container Registry: ghcr.io/usuario/repo -> https://github.com/usuario/repo/pkgs/container/repo
                    if '/' in repo_path:
                        user, repo = repo_path.split('/', 1)
                        # Si el repositorio tiene múltiples partes, tomamos la última como nombre del paquete
                        if '/' in repo:
                            package_name = repo.split('/')[-1]
                        else:
                            package_name = repo
                        return f"https://github.com/{user}/{repo.split('/')[0]}/pkgs/container/{package_name}"
                    return f"https://github.com/orgs/{repo_path}/packages"
                elif registry == 'quay.io':
                    # Quay.io: quay.io/usuario/repo -> https://quay.io/repository/usuario/repo
                    return f"https://quay.io/repository/{repo_path}"
                else:
                    # Para otros registros, devolvemos el enlace al registro
                    return f"https://{registry}"
            
            # Es una imagen de Docker Hub con formato usuario/repo
            else:
                # Construir URL de Docker Hub: https://hub.docker.com/r/usuario/repo
                return f"https://hub.docker.com/r/{image_name}"
        
        # Es una imagen oficial de Docker Hub (como 'ubuntu' o 'nginx')
        return f"https://hub.docker.com/_/{image_name}"
