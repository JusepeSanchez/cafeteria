Cafetería

Aplicación web para administrar el catálogo y los pedidos de una cafetería.
Está desarrollada con Django y usa SQLite para el almacenamiento local.

Requisitos

- Python 3.12 o posterior.
- `pip`.

Las dependencias están declaradas en [`requirements.txt`](requirements.txt).

Instalación y ejecución

Desde la carpeta raíz del repositorio, ejecuta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd .\cafeteria
python manage.py migrate
python manage.py cargar_datos_prueba
python manage.py runserver
```

Abre <http://127.0.0.1:8000/>. La aplicación redirige al usuario autenticado
a la vista correspondiente a su rol.

Para ejecutar las pruebas:

```powershell
python manage.py test pedido
```

Usuarios de prueba

El comando cargar_datos_prueba carga categorías, productos y estos usuarios:

| Rol | Usuario | Contraseña |
|---|---|---|
| Encargado | `encargado` | `cafe1234` |
| Cliente | `cliente1` | `cafe1234` |
| Cliente | `cliente2` | `cafe1234` |

El comando crea los usuarios si no existen; no restablece la contraseña de un
usuario que ya existía. Cambia estas credenciales antes de usar la aplicación
fuera de un entorno local de prueba.

Funcionalidades

- Catálogo con búsqueda y filtro por categoría para clientes.
- Carrito guardado en sesión, con límite de 10 unidades y validación de stock.
- Confirmación de pedidos con hora de retiro entre las 08:00 y las 18:00, y
  al menos 20 minutos después de la hora actual.
- Historial y cancelación de pedidos por el cliente; gestión de estados por el
  encargado.
- Administración de categorías y productos por el encargado.
- Sesión de 30 minutos y control de acceso según el rol.

La aplicación está configurada para desarrollo local (`DEBUG = True`) y usa
SQLite; no está preparada para desplegarse en producción sin configuración
adicional.
