import reflex as rx
from reflex_monaco import monaco

from unposer.state.MainState import MainState

def template_tab() -> rx.Component:
    # Pestaña 3: Plantilla Unraid
    return rx.tabs.content(
        rx.vstack(
            rx.box(height="1.5em"),
            rx.text("Plantilla Unraid generada", mb=2, text_align="left"),
            rx.box(
                monaco(
                    default_language='xml',
                    default_value=MainState.unraid_template,
                    on_change=MainState.update_unraid_template,
                    height='500px',
                    width='100%',
                ),
                background_color="var(--gray-3)",
                width="100%",
                padding="10px",
                style={
                    "borderWidth": "1px",
                    "borderStyle": "solid",
                    "borderRadius": "0.75rem",
                },  
            ),
            rx.hstack(
                rx.button(
                    "Anterior",
                    on_click=lambda: MainState.validate_tab_change("options"),
                    size="3",
                    variant="outline",
                ),
                rx.menu.root(
                    rx.menu.trigger(
                        rx.button("Descargar Plantilla", variant="classic", size="3"),
                    ),
                    rx.menu.content(
                        rx.menu.item("En el equipo local", on_click=lambda: MainState.download_template_local()),
                        rx.menu.separator(),
                        rx.menu.item("En la carpeta de plantillas de Unraid", disabled=False, on_click=lambda: MainState.save_template_unraid()),
                    ),
                ),
                spacing="4",
                mt=4,
            ),
            align_items="center",
            spacing="5",
            py=4,
            px=2,
            width="100%",
        ),
        value="template",
    ),