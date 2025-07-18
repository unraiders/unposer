import reflex as rx


def header() -> rx.Component:
    return rx.flex(
        rx.avatar(src="/unposer-logo-trans.png",
        position="absolute",
        size="5",
        top="1rem",
        left="1rem",
        ),

        rx.color_mode.button(
            position="absolute",
            top="1rem",
            right="1rem"
        ),
        rx.theme_panel(default_open=False),
        rx.vstack(

            rx.box(height="1em"),
            
            # Cabecera
            rx.heading(
                "UNPOSER", 
                size="8",
                text_align="center", 
                font_weight="bold",
            ),
            rx.text(
                "Convierte Docker Compose a Plantilla Unraid",
                size="6", 
                text_align="center"
            ),
        align_items="center",
        justify_content="center"
        ),
    )