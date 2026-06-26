# Cambios en esta versión

## ✨ Novedades

- **El control «Cambiar todos los host paths a /mnt/user/appdata» se deshabilita si el compose no tiene `volumes:`.** Al cargar o editar el compose se comprueba si existe alguna clave `volumes:`; si no hay ninguna, el interruptor queda inactivo (no hay rutas host que convertir) y su etiqueta se atenúa.
