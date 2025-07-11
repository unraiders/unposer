import reflex as rx
from typing import List
import requests
import re
import yaml
import os

from unposer.utils.converter import UnraidTemplateConverter

class MainState(rx.State):
    """Estado principal de la aplicación."""
    
    # Estado de las pestañas
    active_tab: str = "compose"
    
    # Estados para la primera pestaña - Docker Compose
    docker_compose_text: str = ""
    github_repo_url: str = ""
    has_loaded_docker_compose: bool = False
    found_compose_branch: str = ""
    found_compose_directory: str = ""
    found_compose_filename: str = ""
    
    # Nombre del archivo para descarga
    download_filename: str = "unraid-template.xml"
    
    # Estados para la segunda pestaña - Opciones de la plantilla
    icon_method: str = "url"
    external_icon_url: str = ""
    github_repo_icon_url: str = ""
    github_images: List[str] = []
    selected_github_image: str = ""
    preview_icon_url: str = ""
    template_description: str = ""
    support_url: str = ""
    project_url: str = ""
    selected_category: str = ""
    available_categories: List[str] = [
        "MediaServer", "Downloaders", "Tools", "Backup", "Cloud",
        "Productivity", "HomeAutomation", "Security", "Development",
        "GameServers", "Other"
    ]
    
    # Estados para la tercera pestaña - Plantilla Unraid
    unraid_template: str = ""
    formatted_xml: str = ""
    download_xml: str = ""
    has_generated_template: bool = False
    
    # Estados para manejar puertos web
    available_ports: List[str] = []
    selected_web_port: str = ""
    
    # Instancia del conversor
    _converter: UnraidTemplateConverter = UnraidTemplateConverter()
    
    # Listas de prioridad para búsqueda de docker-compose
    _priority_compose_paths = [
        "/docker-compose.yml",             
        "/docker-compose.yaml",
        "/docker-compose.example.yml",      
        "/docker-compose.example.yaml",               
        "/docker/docker-compose.yml",       
        "/docker/docker-compose.yaml",
        "/compose/docker-compose.yml",      
        "/compose/docker-compose.yaml",
        ]
    
    # Estado de carga del compose
    is_loading_compose: bool = False

    _priority_branches = [
        "main",
        "master",
    ]

    # Definición de prioridades para validación de composes
    _compose_validation_priority = [
        {
            'priority': 1,
            'required_fields': ['services', 'image'],
            'must_have': ['environment'],
            'must_not_have': ['build']
        },
        {
            'priority': 2,
            'required_fields': ['services', 'image'],
            'must_have': [],
            'must_not_have': []
        },
    ]


    def change_tab(self, tab: str):
        """Cambia la pestaña activa."""
        self.active_tab = tab
        return None
        
    def _reset_fields(self):
        """Reinicia todas las variables de la aplicación sin mostrar mensaje."""
        # Reinicio de estados de la primera pestaña
        self.docker_compose_text = ""
        self.github_repo_url = ""
        self.has_loaded_docker_compose = False
        self.found_compose_branch = ""
        self.found_compose_directory = ""
        self.found_compose_filename = ""
        
        # Reinicio de estados de la segunda pestaña
        self.icon_method = "url"
        self.external_icon_url = ""
        self.github_repo_icon_url = ""
        self.github_images = []
        self.selected_github_image = ""
        self.preview_icon_url = ""
        self.template_description = ""
        self.support_url = ""
        self.project_url = ""  
        self.selected_category = ""  
        self.available_ports = []
        self.selected_web_port = ""
        
        # Reinicio de estados de la tercera pestaña
        self.unraid_template = ""
        self.formatted_xml = ""
        self.download_xml = ""
        self.has_generated_template = False
        

    def reset_app(self):
        """Reinicia todas las variables de la aplicación y muestra un mensaje."""
        self._reset_fields()
        yield rx.toast.success("Todos los campos han sido reiniciados.")
    
    def next_tab(self):
        """Avanza a la siguiente pestaña."""
        if self.active_tab == "compose":
            # Validamos el cambio a la pestaña de opciones
            yield from self.validate_tab_change("options")
        elif self.active_tab == "options":
            # Validamos el cambio a la pestaña de plantilla
            yield from self.validate_tab_change("template")
            if self.active_tab == "template":
                # Si el cambio fue exitoso, mostramos el mensaje de éxito
                yield rx.toast.success("Plantilla generada correctamente.")
    
    def set_docker_compose(self, text: str):
        """Establece el texto del Docker Compose."""
        self.docker_compose_text = text
        
    def set_icon_method(self, method: str):
        """Establece el método para seleccionar el icono."""
        self.icon_method = method
        # Limpiar la vista previa al cambiar el método
        self.preview_icon_url = ""
        
    # Variable para rastrear si ya se mostró un mensaje de error
    _error_shown: bool = False
    
    def handle_tab_change(self, tab_value: str):
        """Maneja el cambio de pestaña desde el componente tabs."""
        # Si la pestaña actual ya es la que se quiere cambiar, no hacemos nada
        if self.active_tab == tab_value:
            return
        
        # Reiniciamos la bandera de error
        self._error_shown = False
        
        # Si el usuario intenta cambiar a una pestaña distinta de "compose" 
        # y el Docker Compose está vacío
        if tab_value != "compose" and not self.docker_compose_text:
            # Mostrar un mensaje de error solo si no se ha mostrado antes
            yield rx.toast.error("Por favor, introduce el contenido del archivo Docker Compose antes de continuar y pulsa Siguiente.")
            self._error_shown = True
            # No permitir el cambio de pestaña
            return
            
        # Si intenta ir a la pestaña "options" pero no ha cargado Docker Compose
        if tab_value == "options" and not self.has_loaded_docker_compose:
            # Mostrar un mensaje de error
            yield rx.toast.error("Por favor, carga un Docker Compose válido antes de continuar y pulsa Siguiente.")
            # No permitir el cambio de pestaña
            return
            
        # Si intenta ir a la pestaña "template"
        if tab_value == "template":
            # Generar la plantilla con los valores actuales antes de cambiar a la pestaña
            try:
                # Solo generamos la plantilla si ya hemos cargado el Docker Compose
                if self.has_loaded_docker_compose:
                    self._generate_template()
                    self.has_generated_template = True
                else:
                    # Si no ha cargado Docker Compose, mostrar error
                    yield rx.toast.error("Por favor, carga un Docker Compose válido antes de continuar y pulsa Siguiente.")
                    return
            except Exception as e:
                yield rx.toast.error(f"Error al generar la plantilla: {str(e)}")
                return
            
        # Si todo está bien, permitir el cambio
        self.active_tab = tab_value
    
    def validate_tab_change(self, tab_value: str):
        """Valida si se puede cambiar a una pestaña y realiza el cambio si es válido."""
        # Si la pestaña actual ya es la que se quiere cambiar, no hacemos nada
        if self.active_tab == tab_value:
            return
        
        # Si el usuario intenta cambiar a una pestaña distinta de "compose" 
        # y el Docker Compose está vacío
        if tab_value != "compose" and not self.docker_compose_text:
            # Mostrar un mensaje de error
            yield rx.toast.error("Por favor, introduce el contenido del archivo Docker Compose antes de continuar y pulsa Siguiente.")
            # No permitir el cambio de pestaña
            return
            
        # Si intenta ir a la pestaña "options"
        if tab_value == "options":
            # Siempre procesamos el Docker Compose actual para actualizar los puertos y otras configuraciones
            try:
                # Extraer los puertos del Docker Compose
                docker_compose_data = self._converter.parse_docker_compose(self.docker_compose_text)
                
                # Verificar que el Docker Compose contiene el campo 'image'
                if 'image' not in docker_compose_data:
                    yield rx.toast.error("El Docker Compose no contiene el campo 'image' que es necesario para generar la plantilla.")
                    return
                
                # Actualizar la lista de puertos disponibles
                ports = self._converter.extract_ports(docker_compose_data)
                # Agregar la opción "No seleccionar puerto" al principio de la lista
                self.available_ports = ["No seleccionar puerto"] + ports if ports else []
                
                # Si hay puertos disponibles, seleccionamos el primero por defecto
                # pero solo si no hay uno ya seleccionado o si el seleccionado ya no existe en la lista
                if self.available_ports:
                    if not self.selected_web_port or self.selected_web_port not in self.available_ports:
                        # No seleccionamos automáticamente ningún puerto
                        self.selected_web_port = "No seleccionar puerto"
                
                # Si aún no tenemos URLs configuradas, intentamos configurarlas desde el compose
                if not any([self.support_url, self.project_url, self.github_repo_icon_url]):
                    if self._try_configure_github_urls_from_compose(self.docker_compose_text):
                        yield rx.toast.success("URLs de GitHub configuradas automáticamente desde el compose.")
                        
                        # Si se ha configurado el método de icono como GitHub, buscar imágenes automáticamente
                        if self.icon_method == "github" and self.github_repo_icon_url:
                            try:
                                self.search_github_images()
                            except Exception as e:
                                yield rx.toast.warning(f"Error al buscar imágenes en GitHub: {str(e)}")
                
                # Marcamos que ya se ha cargado el Docker Compose correctamente
                self.has_loaded_docker_compose = True
                
                # Mostramos un mensaje de éxito si el Docker Compose se procesó correctamente
                yield rx.toast.success("Docker Compose procesado correctamente.")
                
            except Exception as e:
                yield rx.toast.warning(f"Error al procesar el Docker Compose: {str(e)}")
                return
            
        # Si intenta ir a la pestaña "template"
        if tab_value == "template":
            # Generar la plantilla con los valores actuales antes de cambiar a la pestaña
            try:
                # Solo generamos la plantilla si ya hemos cargado el Docker Compose
                if self.has_loaded_docker_compose:
                    self._generate_template()
                    self.has_generated_template = True
                else:
                    # Si no ha cargado Docker Compose, mostrar error
                    yield rx.toast.error("Por favor, carga un Docker Compose válido antes de continuar y pulsa Siguiente.")
                    return
            except Exception as e:
                yield rx.toast.error(f"Error al generar la plantilla: {str(e)}")
                return
            
        # Si todo está bien, permitir el cambio
        self.active_tab = tab_value
    
    async def handle_docker_compose_upload(self, files):
        """Maneja la subida de un archivo Docker Compose."""
        try:
            if not files or len(files) == 0:
                return
            
            file = files[0]
            # Comprueba si file ya es bytes o si es un UploadFile
            if isinstance(file, bytes):
                content = file
            else:
                content = await file.read()
            
            compose_content = content.decode("utf-8")
            
            try:
                # Verificar que es un docker-compose válido con el campo image
                compose_data = self._converter.parse_docker_compose(compose_content)
                if 'image' in compose_data:
                    self.docker_compose_text = compose_content
                    yield rx.toast.success("Archivo Docker Compose válido cargado correctamente.")
                    
                    # Intentamos configurar las URLs de GitHub automáticamente
                    if self._try_configure_github_urls_from_compose(compose_content):
                        yield rx.toast.success("URLs de GitHub configuradas automáticamente desde el compose.")
                else:
                    yield rx.toast.error("El archivo cargado no contiene el campo 'image' que es necesario para generar la plantilla.")
            except Exception as e:
                yield rx.toast.error(f"El archivo cargado no es un Docker Compose válido: {str(e)}")
        except Exception as e:
            yield rx.toast.error(f"Error al cargar el archivo: {str(e)}")
            
    async def load_docker_compose_from_github(self):
        """Carga un archivo Docker Compose desde un repositorio de GitHub."""
        if not self.github_repo_url:    
            yield rx.toast.error(f"Por favor, introduce la URL de un repositorio válido.")
            return
            
        # Guardamos la URL actual antes de limpiar
        current_url = self.github_repo_url
        
        # Limpiamos todos los campos usando la función existente
        self._reset_fields()
        
        # Restauramos la URL
        self.github_repo_url = current_url
            
        # Activamos el estado de carga
        self.is_loading_compose = True
        # Aseguramos que el estado se actualice inmediatamente
        yield
        
        try:
            # Preparamos la URL base del repositorio
            base_url = self.github_repo_url.rstrip('/')
            if "blob" in base_url:
                base_url = base_url.split("/blob/")[0]
            elif "raw" in base_url:
                base_url = base_url.split("/raw/")[0]
                
            # Si es una URL normal de GitHub, la convertimos al formato raw para acceder a archivos
            raw_base_url = base_url.replace("github.com", "raw.githubusercontent.com")
            api_base_url = base_url.replace("github.com", "api.github.com/repos")
            
            # Determinar la rama principal (main o master)
            branch = "main"  # Por defecto asumimos main
            try:
                # Consultar información del repositorio para obtener la rama por defecto
                repo_info_url = f"{api_base_url}"
                repo_response = requests.get(repo_info_url)
                if repo_response.status_code == 200:
                    repo_data = repo_response.json()
                    branch = repo_data.get('default_branch', 'main')
                else:
                    # Intentamos con main y si falla usaremos master más adelante
                    test_url = f"{raw_base_url}/main/README.md"
                    test_response = requests.get(test_url)
                    if test_response.status_code != 200:
                        branch = "master"
            except Exception as e:
                # Si hay algún error, seguimos con las ramas por defecto
                pass

            # Inicializamos las variables que contendrán el compose encontrado
            compose_text = None
            best_priority = float('inf')  # Inicializamos con prioridad infinita para que cualquier compose sea mejor
                
            # 1. Primero buscamos exactamente los archivos prioritarios
            for compose_path in self._priority_compose_paths:
                try:
                    full_path = f"/{branch}{compose_path}"
                    compose_url = f"{raw_base_url}{full_path}"
                    response = requests.get(compose_url)
                    
                    if response.status_code == 200:
                        result = self._process_compose_content(response.text, compose_path, branch)
                        if result:
                            priority, compose_data, content = result
                            
                            # Guardamos el mejor compose encontrado hasta ahora
                            if compose_text is None or priority < best_priority:
                                # Procesamos el path para extraer la información correctamente
                                path_parts = full_path.split('/')
                                self.found_compose_branch = path_parts[1]  # rama
                                if len(path_parts) > 3:
                                    self.found_compose_directory = '/'.join(path_parts[2:-1])
                                else:
                                    self.found_compose_directory = ""
                                self.found_compose_filename = path_parts[-1]
                                compose_text = content
                                best_priority = priority
                                yield rx.toast.success(f"Docker Compose válido encontrado en {compose_path} (prioridad {priority})")
                except Exception:
                    continue

            if not compose_text:
                # 2. Si no encontramos en los paths prioritarios, buscamos en el README
                yield rx.toast.info("No se encontró un archivo docker-compose.yml directamente. Buscando en el README...")
                
                readme_paths = [
                    f"/{branch}/README.md",
                    f"/{branch}/readme.md"
                ]
                # Extender la búsqueda a otras ramas prioritarias
                for alt_branch in [b for b in self._priority_branches if b != branch]:
                    readme_paths.extend([
                        f"/{alt_branch}/README.md",
                        f"/{alt_branch}/readme.md"
                    ])

                # Buscar en los README
                readme_text = None
                for readme_path in readme_paths:
                    try:
                        readme_url = f"{raw_base_url}{readme_path}"
                        readme_response = requests.get(readme_url)
                        if readme_response.status_code == 200:
                            readme_text = readme_response.text
                            break
                    except:
                        continue
                
                if readme_text:
                    # Encontramos el README, ahora buscamos bloques docker-compose
                    compose_text = self._extract_docker_compose_from_readme(readme_text)
                    
                    if compose_text:
                        # Actualizar información de ubicación para composes encontrados en README
                        self.found_compose_branch = branch
                        self.found_compose_directory = ""  # En el directorio raíz
                        self.found_compose_filename = "README.md"
                        yield rx.toast.success("Se encontró un Docker Compose válido en el README.")
                
                if not compose_text:
                    # 3. Si no encontramos en el README ni en las rutas prioritarias, buscamos en todo el repositorio
                    yield rx.toast.info("No se encontró un Docker Compose en el README. Buscando en otros directorios...")
                        
                    # Buscamos usando la API de GitHub para encontrar archivos docker-compose en cualquier ubicación
                    try:
                        # Obtenemos la estructura del repositorio
                        contents_url = f"{api_base_url}/git/trees/{branch}?recursive=1"
                        contents_response = requests.get(contents_url)
                        if contents_response.status_code == 200:
                            contents = contents_response.json()
                            docker_compose_files = []
                                
                            # Primero buscamos los archivos que coinciden con nuestros patrones prioritarios
                            for priority_path in self._priority_compose_paths:
                                # Quitamos la barra inicial para coincidir con el formato de GitHub
                                search_file = priority_path.lstrip('/')
                                for item in contents.get('tree', []):
                                    if item.get('type') == 'blob' and item.get('path'):
                                        if item.get('path').endswith(search_file):
                                            docker_compose_files.append(item.get('path'))
                            
                            # Si no encontramos ningún archivo prioritario, entonces buscamos cualquier docker-compose
                            if not docker_compose_files:
                                for item in contents.get('tree', []):
                                    if item.get('type') == 'blob' and item.get('path'):
                                        path = item.get('path')
                                        if path.endswith('docker-compose.yml') or path.endswith('docker-compose.yaml'):
                                            docker_compose_files.append(path)
                            
                            # Intentar cargar cada archivo encontrado
                            for file_path in docker_compose_files:
                                try:
                                    file_url = f"{raw_base_url}/{branch}/{file_path}"
                                    file_response = requests.get(file_url)
                                    if file_response.status_code == 200:
                                        try:
                                            compose_data = self._converter.parse_docker_compose(file_response.text)
                                            if 'image' in compose_data:
                                                compose_text = file_response.text
                                                # Actualizamos la información de ubicación
                                                path_parts = file_path.split('/')
                                                self.found_compose_branch = branch
                                                if len(path_parts) > 1:
                                                    self.found_compose_directory = '/'.join(path_parts[:-1])
                                                else:
                                                    self.found_compose_directory = ""
                                                self.found_compose_filename = path_parts[-1]
                                                yield rx.toast.success(f"Docker Compose válido encontrado en {file_path}")
                                                break
                                        except:
                                            continue
                                except:
                                    continue
                            
                            if not compose_text:
                                yield rx.toast.error("No se encontró un archivo docker-compose válido en el repositorio.")
                        
                    except Exception as e:
                        yield rx.toast.error(f"Error al buscar en el repositorio: {str(e)}")
                        return
                # Si no se encontró ningún compose, lo indicamos
                if not compose_text:
                    yield rx.toast.error("No se encontró un Docker Compose válido en el repositorio.")
            
            # Desactivamos el estado de carga antes de procesar el resultado
            self.is_loading_compose = False
            
            # Si encontramos un compose_text válido, lo procesamos
            if compose_text:
                try:
                    # Verificamos que es un docker-compose válido
                    compose_data = self._converter.parse_docker_compose(compose_text)
                    if 'image' in compose_data:
                        self.docker_compose_text = compose_text
                        yield rx.toast.success("Docker Compose cargado exitosamente.")
                        self.has_loaded_docker_compose = True
                    else:
                        yield rx.toast.error("El archivo encontrado no contiene el campo 'image' requerido.")
                except Exception as e:
                    yield rx.toast.error(f"Error al procesar el Docker Compose: {str(e)}")
            else:
                yield rx.toast.error("No se encontró un Docker Compose válido en el repositorio.")
                return
            
            # Si llegamos aquí, tenemos un compose válido
            if compose_text:
                try:
                    # Configuramos automáticamente las URLs
                    self.project_url = base_url
                    self.support_url = f"{base_url}/releases"
                    self.github_repo_icon_url = base_url
                    self.icon_method = "github"
                    
                    # Intentamos obtener la descripción del repositorio desde el About
                    try:
                        # Usamos la API de GitHub para obtener la descripción del repositorio
                        repo_info_url = f"{api_base_url}"
                        repo_response = requests.get(repo_info_url)
                        if repo_response.status_code == 200:
                            repo_data = repo_response.json()
                            if 'description' in repo_data and repo_data['description']:
                                self.template_description = repo_data['description']
                            elif 'name' in repo_data:
                                # Si no hay descripción, usamos el nombre del repo
                                self.template_description = f"Plantilla para {repo_data['name']}"
                    except Exception as e:
                        yield rx.toast.warning(f"No se pudo obtener la descripción del repositorio: {str(e)}")
                    
                    # Intentamos buscar imágenes
                    try:
                        self.search_github_images()
                    except Exception as e:
                        pass
                    
                    # Marcamos como exitoso y mostramos mensaje
                    self.has_loaded_docker_compose = True
                    yield rx.toast.success("Docker Compose válido cargado correctamente desde el repositorio.")
                except Exception as e:
                    yield rx.toast.error(f"Error al procesar el Docker Compose: {str(e)}")
                    
        except Exception as e:
            yield rx.toast.error(f"Error al cargar el archivo desde GitHub: {str(e)}")
        
        finally:
            # Nos aseguramos de que el estado de carga se desactive siempre
            self.is_loading_compose = False
            
    def _extract_docker_compose_from_readme(self, readme_text):
        """
        Extrae un bloque docker-compose válido desde el contenido del README.
        
        Args:
            readme_text: Contenido del archivo README.md
            
        Returns:
            Texto del docker-compose si se encuentra, None en caso contrario
        """
        # Estrategia 1: Buscar bloques de código markdown explícitamente marcados
        code_patterns = [
            # Formato markdown estándar para bloques de código
            r'```ya?ml\s+([\s\S]*?)```',                    # Bloque de código YAML 
            r'```docker[\-\s]?compose\s+([\s\S]*?)```',     # Bloque de código docker-compose
            r'```\s+version:[\s\S]*?services:[\s\S]*?```',  # Bloque con formato docker-compose sin especificación
            r'```\s+services:[\s\S]*?```',                  # docker-compose moderno (sin version)
            
            # Formatos HTML para bloques de código
            r'<pre>\s*version:[\s\S]*?services:[\s\S]*?</pre>',
            r'<pre>\s*services:[\s\S]*?</pre>',
            r'<code>\s*version:[\s\S]*?services:[\s\S]*?</code>',
            r'<code>\s*services:[\s\S]*?</code>',
            
            # Bloques que contienen claves docker-compose típicas
            r'```[\s\S]*?services:[\s\S]*?image:[\s\S]*?```',
            r'<pre>[\s\S]*?services:[\s\S]*?image:[\s\S]*?</pre>'
        ]
        
        # Buscar todos los bloques de código que coincidan con los patrones
        potential_blocks = []
        
        for pattern in code_patterns:
            matches = re.findall(pattern, readme_text)
            if matches:
                # Tenemos que manejar grupos de captura o bloques completos
                for match in matches:
                    if isinstance(match, str):
                        # Si el patrón captura todo el bloque incluyendo los delimitadores
                        if match.strip().startswith('```') or match.strip().startswith('<pre>'):
                            # Extraer solo el contenido entre los delimitadores
                            content = re.sub(r'^```\w*\s*|\s*```$', '', match.strip())
                            content = re.sub(r'^<pre>\s*|\s*</pre>$', '', content.strip())
                            content = re.sub(r'^<code>\s*|\s*</code>$', '', content.strip())
                        else:
                            content = match.strip()
                    else:
                        # El primer grupo capturado es el contenido
                        content = match[0].strip() if match else ""
                    
                    potential_blocks.append(content)
        
        # Estrategia 2: Buscar URL a archivos docker-compose en el README
        docker_compose_urls = re.findall(r'(https?://[^\s\)\"\']+(?:docker-compose\.ya?ml))', readme_text)
        for url in docker_compose_urls:
            try:
                url_response = requests.get(url)
                if url_response.status_code == 200:
                    potential_blocks.append(url_response.text)
            except:
                continue
        
        # Filtrar y validar bloques para encontrar docker-compose válidos
        for block in potential_blocks:
            try:
                # Solo si tiene al menos 2 líneas y contiene "services:" o "image:"
                if len(block.strip().split('\n')) >= 2 and ('services:' in block or 'image:' in block):
                    compose_data = self._converter.parse_docker_compose(block)
                    if 'image' in compose_data:
                        return block
            except Exception:
                continue
                
        # Estrategia 3: Intentar extraer bloques de código indentados que no están marcados explícitamente
        # Buscamos patrones que parezcan docker-compose pero no están en bloques de código formales
        indented_block_patterns = [
            r'(?:^|\n)(\s+services:[\s\S]*?)(?=\n\S|\Z)',  # Bloques indentados que comienzan con services:
            r'(?:^|\n)(\s+version:[\s\S]*?services:[\s\S]*?)(?=\n\S|\Z)'  # Bloques indentados que comienzan con version:
        ]
        
        for pattern in indented_block_patterns:
            matches = re.findall(pattern, readme_text)
            for match in matches:
                try:
                    # Desindentamos para normalizar
                    lines = match.splitlines()
                    if not lines:
                        continue
                        
                    # Encontrar la indentación mínima
                    min_indent = float('inf')
                    for line in lines:
                        if line.strip():  # Solo líneas no vacías
                            current_indent = len(line) - len(line.lstrip())
                            min_indent = min(min_indent, current_indent)
                    
                    if min_indent == float('inf'):
                        continue
                    
                    # Desidentar todas las líneas
                    normalized_lines = [line[min_indent:] if len(line) >= min_indent else line for line in lines]
                    normalized_block = '\n'.join(normalized_lines)
                    
                    # Validar como docker-compose
                    compose_data = self._converter.parse_docker_compose(normalized_block)
                    if 'image' in compose_data:
                        return normalized_block
                except Exception:
                    continue
        
        # No se encontró un bloque docker-compose válido
        return None
            
    def _generate_template(self):
        """Genera la plantilla de Unraid a partir del Docker Compose."""
        try:
            # Parsear el Docker Compose
            docker_compose_data = self._converter.parse_docker_compose(self.docker_compose_text)
            
            # Determinar la URL del icono según el método seleccionado
            icon_url = ""
            if self.icon_method == "url" and self.external_icon_url:
                icon_url = self.external_icon_url
            elif self.icon_method == "github" and self.selected_github_image:
                icon_url = self.selected_github_image
            elif self.icon_method == "upload" and self.preview_icon_url and self.preview_icon_url.startswith("http"):
                icon_url = self.preview_icon_url
            
            # Crear un diccionario con los campos de la aplicación
            app_fields = {
                'Icon': icon_url,
                'Overview': self.template_description,
                'Support': self.support_url,
                'Project': self.project_url,
                'Category': self.selected_category
            }
            
            # Generar la plantilla
            web_port = self.selected_web_port if self.selected_web_port and self.selected_web_port != "No seleccionar puerto" else ""
            self.unraid_template = self._converter.generate_unraid_template(
                docker_compose_data,
                icon_url,
                self.template_description,
                web_port,
                app_fields
            )
            
            # Formatear la plantilla para visualización y descarga
            self.formatted_xml = self.unraid_template
            self.download_xml = self.unraid_template
            
            # Marcamos que la plantilla ha sido generada
            self.has_generated_template = True
            
            # Preparar el nombre del archivo para descarga
            self.prepare_download_filename()
            
        except Exception as e:
            self.unraid_template = f"Error al generar la plantilla: {str(e)}"
            self.has_generated_template = False
            
    def set_external_icon_url(self, url: str):
        """Establece la URL externa del icono."""
        self.external_icon_url = url
        # Si se modifica la URL, limpiar la vista previa
        self.preview_icon_url = ""
    
    def preview_external_icon(self):
        """Muestra una vista previa del icono desde la URL externa."""
        if not self.external_icon_url:
            return rx.toast.error("Error, Por favor, introduce una URL de icono válida.")
            
        try:
            # Realizar una petición HEAD para verificar la existencia y tipo de la imagen
            response = requests.head(self.external_icon_url, allow_redirects=True)
            
            # Verificar el código de respuesta
            if response.status_code != 200:
                self.preview_icon_url = ""
                return rx.toast.error("No se encontró imagen en esa URL o la imagen no es válida")
                
            # Verificar que el contenido es una imagen
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                self.preview_icon_url = ""
                return rx.toast.error("No se encontró imagen en esa URL o la imagen no es válida")
                
            # Si llegamos aquí, la imagen es válida
            self.preview_icon_url = self.external_icon_url
            return rx.toast.success("¡Éxito!, Vista previa del icono cargada.")
            
        except Exception as e:
            # En caso de cualquier error (timeout, conexión, etc.)
            self.preview_icon_url = ""
            return rx.toast.error("No se encontró imagen en esa URL o la imagen no es válida")
        
    def set_github_repo_icon_url(self, url: str):
        """Establece la URL del repositorio de GitHub para buscar iconos."""
        self.github_repo_icon_url = url
        # Limpiar la lista de imágenes y la imagen seleccionada al modificar la URL
        self.github_images = []
        self.selected_github_image = ""
        self.preview_icon_url = ""
        
    def load_github_repo_url(self, url: str):
        """Establece la URL del repositorio GitHub para Docker Compose."""
        self.github_repo_url = url
        
    def search_github_images(self):
        """Busca imágenes en el repositorio de GitHub."""
        if not self.github_repo_icon_url:
            yield rx.toast.error("Por favor, introduce una URL de GitHub válida.")
            return
        
        try:
            images = self._converter.get_github_repo_images(self.github_repo_icon_url)
            if images:
                # Agregar la opción "No seleccionar imagen" al principio de la lista
                self.github_images = ["No seleccionar imagen"] + images
                yield rx.toast.success(f"Se encontraron {len(images)} imágenes en el repositorio.")
            else:
                yield rx.toast.error("No se encontraron imágenes en el repositorio.")
        except Exception as e:
            yield rx.toast.error(f"Error al buscar imágenes: {str(e)}")
            
    def select_github_image(self, image: str):
        """Selecciona una imagen del repositorio de GitHub."""
        if image == "No seleccionar imagen":
            # Limpiar la selección y la vista previa
            self.selected_github_image = ""
            self.preview_icon_url = ""
        else:
            self.selected_github_image = image
            self.preview_icon_url = image
            
    def set_template_description(self, description: str):
        """Establece la descripción de la plantilla."""
        self.template_description = description
    
    def set_support_url(self, url: str):
        """Establece la URL de soporte."""
        self.support_url = url
    
    def set_web_port(self, port: str):
        """Establece el puerto seleccionado para la WebUI."""
        # Si se selecciona "No seleccionar puerto", limpiamos la selección
        if port == "No seleccionar puerto":
            self.selected_web_port = ""
        else:
            self.selected_web_port = port
    
    def set_project_url(self, url: str):
        """Establece la URL del proyecto."""
        self.project_url = url
    
    def set_category(self, category: str):
        """Establece la categoría seleccionada."""
        self.selected_category = category
        
    def update_unraid_template(self, value: str):
        """Actualiza la plantilla Unraid."""
        self.unraid_template = value
        self.formatted_xml = value
        self.download_xml = value
        
    def prepare_download_filename(self):
        """Prepara el nombre de archivo para la descarga basado en el contenido de la plantilla."""
        template_name = "unraid-template"
        if self.unraid_template:
            # Intentamos con la etiqueta <Name>
            name_match = re.search(r'<Name>([^<]+)</Name>', self.unraid_template)
            
            if name_match:
                container_name = name_match.group(1)
                clean_name = re.sub(r'[^\w\-\.]', '_', container_name)
                template_name = f"my-{clean_name}"
        
        self.download_filename = f"{template_name}.xml"
        
    def download_template_local(self):
        """Descarga la plantilla con nombre personalizado."""
        if not self.unraid_template:
            return rx.toast.error("No hay plantilla para descargar.")
            
        self.prepare_download_filename()
        
        return rx.download(
            data=self.download_xml, 
            filename=self.download_filename
        )
        
    def save_template_unraid(self):
        """Guarda la plantilla en la carpeta de plantillas de Unraid."""
        if not self.unraid_template:
            return rx.toast.error("No hay plantilla para guardar.")
            
        try:
            # Preparar el nombre del archivo
            self.prepare_download_filename()
            
            # Construir la ruta completa
            save_path = os.path.join(os.getcwd(), "plantillas", self.download_filename)
            
            # Guardar el archivo
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(self.download_xml)
                
            return rx.toast.success(f"Plantilla guardada en: {save_path}")
            
        except Exception as e:
            return rx.toast.error(f"Error al guardar la plantilla: {str(e)}")
    
    def _get_prioritized_compose_paths(self, initial_branch: str) -> list:
        """Obtiene las rutas de búsqueda para los archivos docker-compose ordenadas por prioridad.
        
        Args:
            initial_branch: Rama inicial del repositorio
            
        Returns:
            Lista de rutas completas ordenadas por prioridad
        """
        all_paths = []
        
        # Primero intentamos con la rama inicial
        all_paths.extend([f"/{initial_branch}{path}" for path in self._priority_compose_paths])
        
        # Luego con el resto de ramas prioritarias, excluyendo la inicial
        for branch in [b for b in self._priority_branches if b != initial_branch]:
            all_paths.extend([f"/{branch}{path}" for path in self._priority_compose_paths])
        
        return all_paths

    def _validate_compose_priority(self, compose_data: dict) -> int:
        """Valida la prioridad de un compose según sus campos.
        
        Args:
            compose_data: Diccionario con el contenido del docker-compose parseado
            
        Returns:
            Prioridad del compose (menor número = mayor prioridad)
            -1 si no cumple ninguna condición
        """
        # Convertir el compose_data a string para búsqueda global
        compose_str = str(compose_data).lower()
        
        for validation in self._compose_validation_priority:
            # Verificar campos requeridos en el nivel principal
            required_fields_valid = True
            for field in validation.get('required_fields', []):
                if field not in compose_data:
                    required_fields_valid = False
                    break
                    
            if not required_fields_valid:
                continue
                
            # Verificar campos que deben estar presentes en cualquier parte
            must_have_valid = True
            for field in validation.get('must_have', []):
                if field.lower() not in compose_str:
                    must_have_valid = False
                    break
                    
            if not must_have_valid:
                continue
                
            # Verificar campos que NO deben estar presentes en ninguna parte
            must_not_have_valid = True
            for field in validation.get('must_not_have', []):
                if field.lower() in compose_str:
                    must_not_have_valid = False
                    break
                    
            if not must_not_have_valid:
                continue
                
            # Si llegamos aquí, es porque cumple todas las condiciones
            return validation.get('priority', -1)
            
        # Si no cumple ninguna validación, devolvemos -1
        return -1

        async def _process_compose_content(self, content: str, file_path: str = "", branch: str = "") -> tuple[int | None, dict | None, str | None]:
            """
            Procesa el contenido de un posible docker-compose y valida su prioridad.
            
            Args:
                content: El contenido del archivo a validar
                file_path: La ruta del archivo (opcional, para logging)
                branch: La rama del repositorio (opcional, para logging)
                
            Returns:
                Tuple de (prioridad, datos_compose, contenido) si es válido, o (None, None, None) si no lo es
            """
            try:
                # Verificamos que el contenido no esté vacío
                if not content or not content.strip():
                    return None, None, None

                # Intentamos parsear como YAML y validar estructura básica
                compose_data = self._converter.parse_docker_compose(content)
                
                # Validar la prioridad del compose
                priority = self._validate_compose_priority(compose_data)
                if priority is not None:
                    return priority, compose_data, content
                    
            except Exception as e:
                print(f"Error procesando compose en {branch}/{file_path}: {str(e)}")
                
            return None, None, None

        def _validate_compose_priority(self, compose_data: dict) -> int | None:
            """
            Valida la prioridad de un compose según las reglas definidas.
            
            Args:
                compose_data: Datos del compose parseado como diccionario
                
            Returns:
                Prioridad del compose (menor es mejor) o None si no es válido
            """
            if not compose_data:
                return None
                
            # Recorremos las reglas de validación en orden
            for rule in self._compose_validation_priority:
                # Verificar campos requeridos
                if not all(field in compose_data for field in rule["required_fields"]):
                    continue
                    
                # Verificar campos que deben estar presentes
                if not all(field in str(compose_data) for field in rule["must_have"]):
                    continue
                    
                # Verificar campos que no deben estar presentes
                if any(field in str(compose_data) for field in rule["must_not_have"]):
                    continue
                    
                # Si pasó todas las validaciones, devolver la prioridad de esta regla
                return rule["priority"]
                
            # Si no coincide con ninguna regla, devolver None
            return None

    async def handle_compose_upload(self, compose_content: str) -> dict:
        """Maneja la carga y validación de un archivo docker-compose.
        
        Args:
            compose_content: Contenido del archivo docker-compose en formato string
            
        Returns:
            Diccionario con el resultado de la validación:
            {
                'success': bool,
                'message': str,
                'priority': int,
                'compose_data': dict
            }
        """
        try:
            # Intentar parsear el compose
            compose_data = yaml.safe_load(compose_content)
            
            if not compose_data:
                return {
                    'success': False,
                    'message': "El archivo docker-compose está vacío",
                    'priority': -1,
                    'compose_data': None
                }
                
            # Validar la estructura básica
            if not isinstance(compose_data, dict):
                return {
                    'success': False,
                    'message': "El archivo docker-compose no tiene un formato válido",
                    'priority': -1,
                    'compose_data': None
                }
                
            # Obtener la prioridad
            priority = self._validate_compose_priority(compose_data)
            
            if priority == -1:
                return {
                    'success': False,
                    'message': "El archivo docker-compose no cumple con los requisitos mínimos",
                    'priority': -1,
                    'compose_data': None
                }
                
            return {
                'success': True,
                'message': "Docker-compose válido",
                'priority': priority,
                'compose_data': compose_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error al procesar el docker-compose: {str(e)}",
                'priority': -1,
                'compose_data': None
            }

    @staticmethod
    def create_info_hover(hover_text: str) -> rx.Component:
        """Crea un icono de información con un hovercard.
        
        Args:
            hover_text: Texto que se mostrará en el hovercard
            
        Returns:
            Componente con el icono y su hovercard
        """
        return rx.hover_card.root(
            rx.hover_card.trigger(
                rx.icon(
                    "info",
                    size=16,
                ),
            ),
            rx.hover_card.content(
                rx.html(hover_text,
                        #size="4px",
                        ),
                style={
                        "max_width": "325px",
                        "font-size": "14px"
                        },
            ),
        )
    
    def _try_configure_github_urls_from_compose(self, compose_text: str) -> bool:
        """
        Intenta extraer y configurar las URLs de GitHub a partir del contenido del compose.
        
        Args:
            compose_text: El contenido del docker-compose
            
        Returns:
            bool: True si se pudieron configurar las URLs, False en caso contrario
        """
        try:
            compose_data = self._converter.parse_docker_compose(compose_text)
            if 'image' in compose_data:
                image_name = compose_data['image']
                # Intentamos extraer el usuario/repositorio de la imagen
                parts = image_name.split('/')
                
                # Si la imagen tiene formato usuario/repositorio
                if len(parts) >= 2:
                    # Si es de GitHub
                    if any(domain in parts[0] for domain in ['ghcr.io', 'docker.pkg.github.com']):
                        # El formato es ghcr.io/usuario/repo o docker.pkg.github.com/usuario/repo
                        user_repo = '/'.join(parts[1:2])
                    else:
                        # Asumimos que es usuario/repo directamente
                        user_repo = '/'.join(parts[:2])
                    
                    # Limpiamos el nombre del repositorio (quitamos el tag si existe)
                    user_repo = user_repo.split(':')[0]
                    
                    # Configuramos las URLs
                    base_url = f"https://github.com/{user_repo}"
                    self.project_url = base_url
                    self.support_url = f"{base_url}/releases"
                    self.github_repo_icon_url = base_url
                    self.icon_method = "github"
                    
                    return True
                    
            return False
        except Exception:
            return False