# Diplonautic · DEMO web corporativa

[![Abrir en GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Alecitho/diplonautic-demo?quickstart=1)

DEMO funcional de la web corporativa de **Diplonautic** (reparación e instalación de sistemas náuticos) con:

- **Web pública**: inicio, servicios y contacto (formulario solo visual).
- **Acceso de empleados**: registro con correo corporativo, verificación por correo, inicio y cierre de sesión.
- **Roles** `empleado` y `administrador`, y **estados** de cuenta: verificado, no verificado y desactivado.
- **Foro interno** solo para usuarios verificados: hilos con título, autor y fecha, respuestas, categorías (duda, aviso, incidencia), búsqueda y moderación.
- **Panel de administración** de usuarios.

### Resumen en un minuto

| Pregunta              | Respuesta                                                                                  |
|-----------------------|--------------------------------------------------------------------------------------------|
| ¿Cómo se arranca?     | `iniciar.bat` (Windows) o `python run.py` → <http://127.0.0.1:5000>. La BD de prueba se crea sola. |
| ¿Por qué Flask + SQLite? | Poco código, sin servicios externos y fácil de leer de principio a fin.                 |
| ¿Cómo se organiza?    | Un blueprint por zona: `public`, `auth`, `forum`, `admin`. SQL directo en cada vista.      |
| ¿Cómo se controla el acceso? | `load_logged_in_user` carga el usuario en cada petición y los decoradores `login_required` → `verified_required` → `admin_required` protegen las vistas. |
| ¿Cómo se dan de alta los empleados? | Registro con correo corporativo y verificación, y además alta directa por el administrador (ver *Decisión: alta de usuarios*). |

📘 Documentación completa en PDF:
- [Manual técnico](docs/Manual_Tecnico_Diplonautic.pdf): stack, arquitectura, modelo de datos, rutas, seguridad, pruebas y flujo con Git.
- [Manual de usuario](docs/Manual_Usuario_Diplonautic.pdf): guía paso a paso con capturas.

---

## Puesta en marcha

### En la nube, sin instalar nada (GitHub Codespaces)

1. Pulsar el botón **Abrir en GitHub Codespaces** de arriba (o **Code → Codespaces → Create codespace on main**).
2. Esperar a que el entorno termine de prepararse: instala las dependencias y arranca la web solo.
3. Se abre una pestaña con la DEMO. Si no, ir a la pestaña **Puertos** y abrir el puerto **5000 · Diplonautic DEMO**.

La configuración está en `.devcontainer/devcontainer.json`. Para relanzar la web desde la terminal del codespace: `python run.py`.

> Codespaces es gratuito con un límite de horas al mes en cuentas personales de GitHub. Detén el codespace al terminar.

### En tu equipo

**Requisitos:** Python 3.10 o superior y Git.

#### Windows (doble clic)

Ejecutar `iniciar.bat`: crea el entorno virtual, instala dependencias, abre el navegador y arranca la web en <http://127.0.0.1:5000>.

#### Manual (cualquier sistema)

```bash
git clone https://github.com/Alecitho/diplonautic-demo.git
cd diplonautic-demo
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python run.py                       # http://127.0.0.1:5000
```

La primera ejecución crea `instance/diplonautic.db` con los datos de prueba. Para restablecerlos:

```bash
flask --app app init-db
```

## Usuarios de prueba

| Nombre        | Correo                          | Contraseña     | Rol      | Estado                      |
|---------------|---------------------------------|----------------|----------|-----------------------------|
| Laura Méndez  | `admin@diplonautic.com`         | `Admin1234`    | Admin    | Verificado                  |
| Ana García    | `ana.garcia@diplonautic.com`    | `Empleado1234` | Empleado | Verificado                  |
| Carlos Ruiz   | `carlos.ruiz@diplonautic.com`   | `Empleado1234` | Empleado | Verificado                  |
| Marta Vidal   | `marta.vidal@diplonautic.com`   | `Empleado1234` | Empleado | Verificado                  |
| Lucía Martín  | `lucia.martin@diplonautic.com`  | `Empleado1234` | Empleado | **No verificado**           |
| Javier Soler  | `javier.soler@diplonautic.com`  | `Empleado1234` | Empleado | **No verificado**           |
| Pedro Sanz    | `pedro.sanz@diplonautic.com`    | `Empleado1234` | Empleado | Verificado · **Desactivado** |

> Credenciales ficticias solo para la DEMO local. No hay servidor de correo: el correo de verificación se muestra en pantalla.

## Stack

| Capa              | Tecnología                                           |
|-------------------|------------------------------------------------------|
| Lenguaje          | Python 3 (backend), HTML5 + Jinja2, CSS3, JavaScript |
| Framework web     | Flask 3.1 (blueprints, sesiones firmadas)            |
| Base de datos     | SQLite con SQL parametrizado (`app/schema.sql`)      |
| Seguridad         | Werkzeug (hash scrypt), CSRF propio, autoescape      |
| Pruebas           | pytest (47 pruebas) + GitHub Actions                 |
| Control versiones | Git + GitHub (ramas por funcionalidad y Pull Requests) |

### Decisión: alta de usuarios

Modelo **mixto**: los empleados se registran con su correo corporativo (`@diplonautic.com`) y quedan **sin verificar** hasta confirmar el correo; un administrador puede además dar de alta, verificar, cambiar el rol o desactivar cuentas. Así el administrador no es un cuello de botella y se mantiene el control de acceso al foro.

## Estructura

```
app/
  __init__.py   fábrica de la aplicación      auth.py    registro, verificación, sesión, permisos
  public.py     web pública                    forum.py   foro interno
  admin.py      gestión de usuarios            db.py      SQLite y comando init-db
  security.py   protección CSRF                seed.py    datos de prueba
  schema.sql    esquema de la BD               templates/ static/
tests/          pruebas con pytest
docs/           manuales PDF y capturas
.github/        plantilla de PR y CI
.devcontainer/  entorno de GitHub Codespaces
```

## Pruebas

```bash
python -m pytest
```

## Documentación

Los manuales PDF de `docs/` se generaron con un script auxiliar que no forma parte de la DEMO, por eso no se incluye en el repositorio.

## Flujo de trabajo con Git

- `main` estable; cada funcionalidad en su rama (`feature/web-publica`, `feature/autenticacion`, `feature/foro`, `test/pruebas-automatizadas`, `docs/manuales`).
- Commits en español con [Conventional Commits](https://www.conventionalcommits.org/es/) (`feat`, `fix`, `style`, `test`, `docs`, `ci`, `chore`).
- Integración mediante Pull Request con la plantilla `.github/pull_request_template.md` y CI que ejecuta las pruebas.

## Uso de IA

Desarrollado con apoyo de **Claude Code** (Anthropic) como asistente para el código, las pruebas y la documentación, con revisión de cada paso. Detalle en el capítulo 12 del manual técnico.
