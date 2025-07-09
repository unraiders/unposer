import reflex as rx

config = rx.Config(
    app_name="unposer",
    api_url=f"http://0.0.0.0:8000",
    frontend_port=3000,
    backend_port=8000,
    tailwind=None,
    show_built_with_reflex=False,
)