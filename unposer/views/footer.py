import reflex as rx
import os

VERSION = os.getenv('VERSION', 'dev')  # Valor por defecto si no se establece la variable de entorno)

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
        rx.text(
            f"Versión {VERSION}",
            mt=6,
            font_size="sm",
            color="gray.500",
        ),
        spacing="2",
        
    )
