import reflex as rx

from unposer.state.MainState import MainState


def compose_tab() -> rx.Component:
    # Pestaña 1: Docker Compose
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.box(height="2.5em"),
                rx.hstack(
                    rx.text("Introduce el contenido del archivo Docker Compose",
                    ),
                    MainState.create_info_hover("Puedes pegar el contenido del Docker Compose aquí. Asegúrate que tenga todas las etiquetas requeridas y el formato sea válido."),
                    spacing="1",
                    align="center",
                ),

                rx.box(height="0.7em"),
                rx.text_area(
                    placeholder="version: '3'\nservices:\n  app:\n    image: ...",
                    height="30rem",
                    width="100%",
                    radius="large",
                    on_change=MainState.set_docker_compose,
                    value=MainState.docker_compose_text,
                    font_family="monospace",
                ),
                width="100%",
            ),
            rx.vstack(
                rx.hstack(
                    rx.upload.root(
                        rx.box(
                            rx.icon(
                                tag="upload",
                                style={
                                    "width": "2rem",
                                    "height": "2rem",
                                    "marginBottom": "0.75rem",
                                },
                            ),
                            rx.text("Haz clic para subir o arrastra un archivo",
                                    size="2",),
                            rx.text(
                                "YAML o YML (archivo docker-compose)",
                                style={
                                    "fontSize": "0.75rem",
                                    "color": "#6b7280",
                                    "marginTop": "0.25rem",
                                },
                            ),
                            style={
                                "display": "flex",
                                "flexDirection": "column",
                                "alignItems": "center",
                                "justifyContent": "center",
                                "padding": "1.5rem",
                                "textAlign": "center",
                            },
                        ),
                        accept=".yml,.yaml",
                        max_files=1,
                        on_drop=MainState.handle_docker_compose_upload,
                        style={
                            "maxWidth": "24rem",
                            "height": "12rem",
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "0.75rem",
                            "cursor": "pointer",
                        },
                    ),
                    rx.vstack(
                        rx.hstack(
                            rx.text("Cargar desde un repositorio"),
                            MainState.create_info_hover("Puedes cargar un Docker Compose desde un repositorio de Github.<br><br>La URL debe ser en formato: https://<registro>/usuario/repositorio"),
                            spacing="1",
                            align="center",
                        ),
                        rx.hstack(
                            rx.input(
                                placeholder="URL del repositorio...",
                                on_change=MainState.load_github_repo_url,
                                value=MainState.github_repo_url,
                                width="100%",
                            ),
                            rx.button(
                                rx.cond(
                                    MainState.is_loading_compose,
                                    rx.hstack(
                                        rx.spinner(),
                                        rx.text("Cargando...")
                                    ),
                                    "Cargar Compose"
                                ),
                                on_click=MainState.load_docker_compose_from_github,
                                is_loading=MainState.is_loading_compose,
                                disabled=MainState.is_loading_compose
                            ),
                            width="100%",
                        ),
                        rx.blockquote(
                            "Si cargas el Compose desde un repositorio este se utilizará para más funciones.",
                            size="1",
                        ),
                        rx.cond(
                            MainState.found_compose_filename != "",
                            rx.vstack(
                                rx.text(
                                    f"Rama: {MainState.found_compose_branch}",
                                    size="1",
                                ),
                                rx.text(
                                    rx.cond(
                                        MainState.found_compose_directory == "",
                                        "Directorio: /",
                                        f"Directorio: {MainState.found_compose_directory}",
                                    ),
                                    size="1",
                                ),
                                rx.text(
                                    f"Fichero en: {MainState.found_compose_filename}",
                                    size="1",
                                ),
                                align_items="start",
                                spacing="0",
                                mt="2",
                            ),
                        ),
                        align_items="start",
                        width="100%",
                    ),
                    width="100%",
                    spacing="4",
                    align_items="stretch",
                ),
                width="100%",
                mb=6,
            ),
            rx.hstack(
                rx.button(
                    "Limpiar",
                    on_click=MainState.reset_app,
                    color_scheme="red",
                    size="3",
                    variant="outline",
                ),
                rx.button(
                    "Siguiente",
                    on_click=lambda: MainState.validate_tab_change("options"),
                    size="3",
                ),
                spacing="4",
            ),
            align_items="center",
            justify_content="center",
            spacing="5",
            py=4,
            px=2,
            width="100%",
        ),
        value="compose",
    ),
