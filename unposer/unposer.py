import reflex as rx

from unposer.views.header import header
from unposer.views.footer import footer
from unposer.views.compose import compose_tab
from unposer.views.options import options_tab
from unposer.views.template import template_tab

from unposer.state.MainState import MainState


def index() -> rx.Component:
    """Página principal de la aplicación."""
    return rx.box(

        rx.vstack(

            # Cabecera de la aplicación            
            header(),
            
            # Contenedor principal con tabs
            rx.box(
                rx.tabs.root(
                    rx.tabs.list(
                        rx.tabs.trigger("Docker Compose", value="compose", on_click=lambda: MainState.validate_tab_change("compose")),
                        rx.tabs.trigger("Opciones Plantilla", value="options", on_click=lambda: MainState.validate_tab_change("options")),
                        rx.tabs.trigger("Plantilla Unraid", value="template", on_click=lambda: MainState.validate_tab_change("template")),
                        width="100%",
                        display="flex",
                        justify_content="center",
                    ),
                    
                    compose_tab(),

                    options_tab(),

                    template_tab(),

                    value=MainState.active_tab,
                    default_value="compose",
                    width="100%",
                ),
                background_color="var(--gray-3)",
                width="100%",
                margin="16px",
                padding="16px",
                style={
                    "borderWidth": "2px",
                    "borderStyle": "solid",
                    "borderColor": "#333334",
                    "borderRadius": "0.75rem",
                },
            ),
            
            # Pie de página
            footer(),
            
            # Propiedades del vstack principal
            spacing="4",
            width="100%",
            max_width="1000px",
            mx="auto",
            px="4",
            py="8",
            align_items="center",
            justify_content="center",
            background="transparent",
        ),
        
        # Propiedades del box principal
        width="100%",
        min_height="100vh",
        display="flex",
        justify_content="center",
        align_items="flex-start",
        bg="transparent",
    )

# Crear la aplicación aplicando tema y configuración
app = rx.App(
    theme=rx.theme(
        accent_color="brown", 
        gray_color="slate", 
        appearance="dark", 
        radius="full"
    )
)

# Añadir la página principal
app.add_page(index)
