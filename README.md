# Diplonautic · DEMO web corporativa

[![Abrir en GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Alecitho/diplonautic-demo-refactor?quickstart=1)

DEMO funcional de la web corporativa de **Diplonautic** (reparación e instalación de sistemas náuticos) con:

- **Web pública**: inicio, servicios y contacto (formulario solo visual).
- **Acceso de empleados**: registro con correo corporativo, verificación por correo, inicio y cierre de sesión.
- **Roles** `empleado` y `administrador`, y **estados** de cuenta: verificado, no verificado y desactivado.
- **Foro interno** solo para usuarios verificados: hilos con título, autor y fecha, respuestas, categorías (duda, aviso, incidencia), búsqueda y moderación.
- **Panel de administración** de usuarios.

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


## Documentación

Los manuales PDF de `docs/` se generaron con un script auxiliar que no forma parte de la DEMO, por eso no se incluye en el repositorio.

## Uso de IA

Desarrollado con apoyo de **Claude Code** (Anthropic) como asistente para el código, las pruebas y la documentación, con revisión de cada paso.
