import reflex as rx


def footer() -> rx.Component:
    """Componente de pie de página."""
    return rx.flex(
        rx.text(
            "UNPOSER - Desarrollado con",
            mt=6,
            font_size="sm",
            color="gray.500",
        ),
        rx.icon("heart", size=20, color="red"),
        spacing="2",
    )
