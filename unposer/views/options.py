import reflex as rx

from unposer.state.MainState import MainState


def options_tab() -> rx.Component:
    # Pestaña 2: Opciones de Plantilla
    return rx.tabs.content(
        rx.vstack(
            rx.box(height="0.3em"),
            rx.box(
                rx.hstack(
                    rx.heading("URL del icono", size="4", mb=2),
                    MainState.create_info_hover("Icono que aparecerá en la interfaz de Unraid"),
                    spacing="1",
                    align="center",           
                ),
                rx.box(height="1em"),
                rx.box(
                    rx.radio_group.root(
                        rx.hstack(
                            rx.radio_group.item("URL externa", value="url"),
                            rx.radio_group.item("Repositorio", value="github"),
                        ),
                        value=MainState.icon_method,
                        on_change=MainState.set_icon_method,
                    ),
                    mb=4,
                ),
                rx.box(height="0.5em"),
                # URL externa
                rx.cond(
                    MainState.icon_method == "url",
                    rx.hstack(
                        rx.input(
                            placeholder="https://ejemplo.com/icono.png",
                            value=MainState.external_icon_url,
                            on_change=MainState.set_external_icon_url,
                            width="100%",
                        ),
                        rx.button(
                            "Obtener",
                            on_click=MainState.preview_external_icon,
                        ),
                        width="100%",
                    ),
                ),
                
                # GitHub
                rx.cond(
                    MainState.icon_method == "github",
                    rx.vstack(
                        rx.hstack(
                            rx.input(
                                placeholder="https://github.com/usuario/repo",
                                value=MainState.github_repo_icon_url,
                                on_change=MainState.set_github_repo_icon_url,
                                width="100%",
                            ),
                            rx.button(
                                "Buscar",
                                on_click=MainState.search_github_images,
                            ),
                            width="100%",
                        ),
                        rx.cond(
                            MainState.github_images.length() > 0,
                            rx.select.root(
                                rx.select.trigger(placeholder="Selecciona una imagen..."),
                                rx.select.content(
                                    rx.foreach(
                                        MainState.github_images,
                                        lambda image: rx.select.item(image, value=image)
                                    ),
                                ),
                                value=MainState.selected_github_image,
                                on_change=MainState.select_github_image,
                                width="100%",
                            ),
                        ),
                        width="100%",
                    ),
                ),
                
                # Vista previa
                rx.cond(
                    MainState.preview_icon_url != "",
                    rx.vstack(
                        rx.box(height="0.5em"),
                        rx.text("Vista previa:", mb=2),
                        rx.image(
                            src=MainState.preview_icon_url,
                            height="3rem",
                        ),
                        align_items="center",
                    ),
                ),
                
                width="100%",
                mb=6,
            ),

            # Selector de puerto web
            rx.cond(
                MainState.available_ports.length() > 0,
                rx.box(
                    rx.heading("Puerto Web para la Interfaz", size="4", mb=2),
                    rx.text(
                        "Selecciona el puerto que se usará para acceder a la interfaz web:",
                        mb=2,
                    ),
                    rx.box(height="0.5em"),
                    rx.hstack(
                        rx.select.root(
                            rx.select.trigger(placeholder="Selecciona un puerto..."),
                            rx.select.content(
                                rx.foreach(
                                    MainState.available_ports,
                                    lambda port: rx.select.item(port, value=port)
                                ),
                            ),
                            value=MainState.selected_web_port,
                            on_change=MainState.set_web_port,
                            width="100%",
                        ),
                        rx.box(height="0.5em"),
                        rx.text(
                            "Esto solo afecta al puerto de la interfaz Web de la plantilla, los puertos se seguirán configurando igualmente en la plantilla.",
                            size="1",
                            mt=1,
                        ),
                        spacing="1",
                        align="center",
                    ),
                    width="100%",
                    mb=6,
                ),
            ),
            
            # Descripción
            rx.box(
                rx.heading("Descripción de la plantilla", size="4", mb=2),
                rx.text_area(
                    placeholder="Descripción del contenedor...",
                    on_change=MainState.set_template_description,
                    value=MainState.template_description,
                    height="10rem",
                    width="100%",
                ),
                width="100%",
                mb=6,
            ),
            
            # URLs
            rx.box(
                rx.heading("URL de soporte", size="4", mb=2),
                rx.input(
                    placeholder="https://github.com/usuario/repo/releases",
                    on_change=MainState.set_support_url,
                    value=MainState.support_url,
                    width="100%",
                ),
                width="100%",
                mb=6,
            ),
            
            rx.box(
                rx.heading("URL del proyecto", size="4", mb=2),
                rx.input(
                    placeholder="https://github.com/usuario/repo",
                    on_change=MainState.set_project_url,
                    value=MainState.project_url,
                    width="100%",
                ),
                width="100%",
                mb=6,
            ),
            
            # Categoría
            rx.box(
                rx.heading("Categorías", size="4", mb=2),
                rx.select.root(
                    rx.select.trigger(placeholder="Selecciona una categoría..."),
                    rx.select.content(
                        rx.foreach(
                            MainState.available_categories,
                            lambda category: rx.select.item(category, value=category)
                        ),
                    ),
                    value=MainState.selected_category,
                    on_change=MainState.set_category,
                    width="100%",
                ),
                width="100%",
                mb=6,
            ),
            
            rx.hstack(
                rx.button(
                    "Anterior",
                    on_click=lambda: MainState.validate_tab_change("compose"),
                    size="3",
                    variant="outline",
                ),
                rx.button(
                    "Siguiente",
                    on_click=lambda: MainState.validate_tab_change("template"),
                    size="3",
                ),
                spacing="4",
            ),
            align_items="center",
            spacing="5",
            py=4,
            px=2,
            width="100%",
        ),
        value="options",
    ),
