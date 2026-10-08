"""Genera los manuales en PDF de la DEMO de Diplonautic.

Uso (desde la raíz del proyecto):
    python docs/generar_manuales.py            # genera los dos manuales
    python docs/generar_manuales.py tecnico    # solo el manual técnico
    python docs/generar_manuales.py usuario    # solo el manual de usuario

El manual técnico se construye en parte leyendo el propio proyecto, de modo que
siempre refleja el código actual:
  - rutas: se obtienen del mapa de URLs de Flask (app.url_map);
  - modelo de datos: se ejecuta app/schema.sql en una BD en memoria;
  - versiones: se leen de los paquetes instalados;
  - pruebas: se cuentan con "pytest --collect-only";
  - control de versiones: ramas y commits del repositorio Git;
  - estadísticas: líneas por lenguaje.
"""
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections import OrderedDict
from importlib.metadata import PackageNotFoundError, version

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(DOCS_DIR)
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, DOCS_DIR)

from maquetacion import (c, captura, codigo, construir, espacio, h1, h2, h3, lista,  # noqa: E402
                         nota, p, salto, tabla)

from app.seed import ADMIN_PASSWORD, EMPLEADO_PASSWORD, TEST_USERS  # noqa: E402

VERSION_DOC = "1.0"


# ==========================================================================
# Datos extraídos del proyecto
# ==========================================================================
def run(cmd):
    try:
        return subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True,
                              encoding="utf-8", timeout=120).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def pkg(nombre):
    try:
        return version(nombre)
    except PackageNotFoundError:
        return "no instalado"


def git_version():
    salida = run(["git", "--version"])
    return salida.replace("git version ", "") or "no disponible"


RUTAS_INFO = {
    "public.index": ("Público", "Página de inicio con presentación y servicios destacados."),
    "public.servicios": ("Público", "Catálogo de servicios y forma de trabajo."),
    "public.contacto": ("Público", "Página de contacto. El formulario es solo visual."),
    "auth.register": ("Público", "Registro de empleados con correo corporativo."),
    "auth.verify": ("Público", "Verifica la cuenta con el token recibido por correo."),
    "auth.resend_verification": ("Sesión", "Genera un nuevo enlace de verificación."),
    "auth.login": ("Público", "Inicio de sesión."),
    "auth.logout": ("Sesión", "Cierre de sesión (solo POST)."),
    "auth.area": ("Sesión", "Área privada: datos y estado de la cuenta."),
    "forum.index": ("Verificado", "Listado de hilos: filtro por categoría, búsqueda y paginación."),
    "forum.new_thread": ("Verificado", "Formulario y creación de un hilo."),
    "forum.thread": ("Verificado", "Hilo con todas sus respuestas y formulario de respuesta."),
    "forum.reply": ("Verificado", "Publica una respuesta (si el hilo no está cerrado)."),
    "forum.toggle_pin": ("Admin", "Fija o desfija un hilo."),
    "forum.toggle_close": ("Autor o admin", "Cierra o reabre un hilo."),
    "forum.delete_thread": ("Autor o admin", "Elimina un hilo y sus respuestas."),
    "forum.delete_post": ("Autor o admin", "Elimina una respuesta."),
    "admin.users": ("Admin", "Listado de usuarios con filtros por estado."),
    "admin.new_user": ("Admin", "Alta directa de un usuario."),
    "admin.verify_user": ("Admin", "Verifica manualmente una cuenta."),
    "admin.send_verification": ("Admin", "Genera un nuevo correo de verificación."),
    "admin.change_role": ("Admin", "Cambia el rol entre empleado y administrador."),
    "admin.toggle_active": ("Admin", "Activa o desactiva una cuenta."),
}


def rutas():
    from app import create_app

    tmp = tempfile.mkdtemp()
    app = create_app({"TESTING": True, "DATABASE": os.path.join(tmp, "doc.db")})
    filas = [["Método", "Ruta", "Acceso", "Descripción"]]
    orden = ["public", "auth", "forum", "admin"]
    reglas = [r for r in app.url_map.iter_rules() if r.endpoint != "static"]
    reglas.sort(key=lambda r: (orden.index(r.endpoint.split(".")[0])
                               if r.endpoint.split(".")[0] in orden else 99, r.rule))
    for regla in reglas:
        metodos = ", ".join(sorted(regla.methods - {"HEAD", "OPTIONS"}))
        acceso, desc = RUTAS_INFO.get(regla.endpoint, ("—", regla.endpoint))
        filas.append([metodos, regla.rule, acceso, desc])
    return filas


COLUMNAS_INFO = {
    "users.email": "Único, sin distinguir mayúsculas.",
    "users.password_hash": "Hash scrypt generado por Werkzeug.",
    "users.role": "'empleado' o 'admin'.",
    "users.is_verified": "1 si confirmó el correo o lo verificó un admin.",
    "users.is_active": "0 = cuenta desactivada (no puede entrar).",
    "users.verification_token": "Hash SHA-256 del token de verificación.",
    "users.verification_sent_at": "Fecha de envío; el enlace caduca a las 48 h.",
    "threads.category": "'duda', 'aviso' o 'incidencia'.",
    "threads.is_pinned": "Fijado al inicio del foro (solo admin).",
    "threads.is_closed": "Cerrado: no admite respuestas.",
    "threads.last_activity_at": "Se actualiza con cada respuesta; ordena el listado.",
    "posts.thread_id": "Hilo al que pertenece (borrado en cascada).",
}


def esquema():
    db = sqlite3.connect(":memory:")
    with open(os.path.join(ROOT_DIR, "app", "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())
    tablas = OrderedDict()
    for (nombre,) in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"):
        fks = {fk[3]: f"{fk[2]}.{fk[4]}" for fk in db.execute(f"PRAGMA foreign_key_list({nombre})")}
        filas = [["Columna", "Tipo", "Restricciones", "Descripción"]]
        for _cid, col, tipo, notnull, default, pk in db.execute(f"PRAGMA table_info({nombre})"):
            r = []
            if pk:
                r.append("PK autoincremental")
            if notnull and not pk:
                r.append("NOT NULL")
            if default is not None:
                r.append(f"DEFAULT {default}")
            if col in fks:
                r.append(f"FK → {fks[col]}".replace("→", "->"))
            filas.append([col, tipo, ", ".join(r) or "—", COLUMNAS_INFO.get(f"{nombre}.{col}", "")])
        tablas[nombre] = filas
    return tablas


def contar_pruebas():
    salida = run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"])
    m = re.search(r"(\d+) tests? collected", salida)
    if m:
        return int(m.group(1))
    # Con -qq pytest muestra "fichero: N"
    total = sum(int(n) for n in re.findall(r"^tests/\S+: (\d+)$", salida, re.M))
    return total or None


def estadisticas_codigo():
    grupos = OrderedDict([
        ("Python (backend)", (["app"], (".py",))),
        ("Python (pruebas)", (["tests"], (".py",))),
        ("Python (documentación)", (["docs"], (".py",))),
        ("HTML + Jinja2", (["app/templates"], (".html",))),
        ("CSS", (["app/static/css"], (".css",))),
        ("JavaScript", (["app/static/js"], (".js",))),
        ("SQL", (["app"], (".sql",))),
    ])
    filas = [["Lenguaje / uso", "Ficheros", "Líneas"]]
    for nombre, (carpetas, exts) in grupos.items():
        n_fich = n_lin = 0
        for carpeta in carpetas:
            for raiz, _dirs, ficheros in os.walk(os.path.join(ROOT_DIR, carpeta)):
                if "__pycache__" in raiz:
                    continue
                if nombre.startswith("Python (backend)") and "templates" in raiz:
                    continue
                for fich in ficheros:
                    if fich.endswith(exts):
                        n_fich += 1
                        with open(os.path.join(raiz, fich), encoding="utf-8") as f:
                            n_lin += sum(1 for _ in f)
        filas.append([nombre, n_fich, n_lin])
    return filas


def git_historial():
    salida = run(["git", "log", "--pretty=format:%h\t%ad\t%s", "--date=short"])
    filas = [["Commit", "Fecha", "Mensaje"]]
    for linea in salida.splitlines():
        partes = linea.split("\t", 2)
        if len(partes) == 3:
            filas.append(partes)
    return filas


def git_ramas():
    salida = run(["git", "branch", "--all", "--format=%(refname:short)"])
    return [r for r in salida.splitlines() if r and "HEAD" not in r]


# ==========================================================================
# Bloques compartidos
# ==========================================================================
def tabla_usuarios_prueba():
    filas = [["Nombre", "Correo", "Contraseña", "Rol", "Estado", "Para probar"]]
    usos = {
        "admin": "Panel de usuarios, moderación y fijar hilos.",
        "ana.garcia": "Empleada verificada: foro completo.",
        "carlos.ruiz": "Segundo empleado verificado (permisos entre autores).",
        "marta.vidal": "Empleada verificada.",
        "lucia.martin": "Cuenta no verificada: foro bloqueado y reenvío del correo.",
        "javier.soler": "Cuenta no verificada: verificación por un administrador.",
        "pedro.sanz": "Cuenta desactivada: no puede iniciar sesión.",
    }
    for nombre, email, rol, _dept, verificado, activo in TEST_USERS:
        estado = "Verificado" if verificado else "No verificado"
        if not activo:
            estado += " · Desactivado"
        clave = ADMIN_PASSWORD if rol == "admin" else EMPLEADO_PASSWORD
        filas.append([nombre, email, clave, rol.capitalize(), estado, usos.get(email.split("@")[0], "")])
    return tabla(filas, [2.3, 4.5, 2.5, 1.8, 2.3, 3.5], escapar=True)


def instalacion():
    return [
        h3("Requisitos"),
        lista([
            "Windows, macOS o Linux con <b>Python 3.10 o superior</b> (probado con Python 3.14).",
            "<b>Git</b> para clonar el repositorio.",
            "Conexión a internet solo para instalar las dependencias y cargar las fuentes tipográficas.",
        ]),
        h3("Opción en la nube: GitHub Codespaces"),
        p("Sin instalar nada: en la página del repositorio, pulsar <b>Code → Codespaces → Create codespace "
          "on main</b> (o el botón <i>Abrir en GitHub Codespaces</i> del README). El entorno definido en "
          f"{c('.devcontainer/devcontainer.json')} instala las dependencias, arranca la web y reenvía el "
          "puerto 5000, que se abre en el navegador. Codespaces es gratuito con un límite de horas al mes."),
        h3("Opción rápida en Windows"),
        p(f"Hacer doble clic en {c('iniciar.bat')} en la carpeta del proyecto. El script crea el entorno "
          f"virtual {c('.venv')}, instala las dependencias, abre el navegador y arranca la web en "
          f"{c('http://127.0.0.1:5000')}."),
        h3("Opción manual (cualquier sistema)"),
        codigo("""
git clone <URL-del-repositorio> diplonautic-demo
cd diplonautic-demo
python -m venv .venv
.venv\\Scripts\\activate          # Windows
source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt
python run.py                     # http://127.0.0.1:5000
"""),
        p("La primera vez que arranca, la aplicación crea la base de datos "
          f"{c('instance/diplonautic.db')} con los datos de prueba. Para volver al estado inicial:"),
        codigo("flask --app app init-db"),
    ]


# ==========================================================================
# Manual técnico
# ==========================================================================
def manual_tecnico():
    n_pruebas = contar_pruebas()
    tablas = esquema()
    ramas = git_ramas()
    historial = git_historial()

    s = []
    # 1 -------------------------------------------------------------------
    s += [h1("1. Introducción"),
          p("Este documento describe la solución técnica de la <b>DEMO de web corporativa de Diplonautic</b>, "
            "empresa de reparación e instalación de sistemas náuticos. La DEMO incluye una parte pública "
            "de presentación de la empresa y un área privada en la que los empleados acceden con sus "
            "credenciales y participan en un <b>foro interno</b> para compartir dudas, avisos e incidencias técnicas."),
          p("El objetivo es entregar algo que funcione de principio a fin, con un código fácil de leer y "
            "explicar, un flujo de trabajo con Git ordenado y datos de prueba listos para usar."),
          h2("1.1 Requisitos cubiertos"),
          tabla([
              ["Requisito del enunciado", "Implementación"],
              ["Web pública: inicio y servicios", "Rutas /, /servicios con contenido de ejemplo."],
              ["Página de contacto (formulario visual)", "Ruta /contacto; el formulario no envía ni guarda datos."],
              ["Registro o alta por administrador", "Ambos: autorregistro con correo corporativo + verificación, "
                                                    "y alta directa desde el panel de administración."],
              ["Inicio y cierre de sesión", "Sesión firmada de Flask; cierre por POST con token CSRF."],
              ["Roles empleado y administrador", "Columna role con restricción CHECK y decoradores de permisos."],
              ["Usuarios verificados / no verificados", "Columna is_verified; solo los verificados acceden al foro."],
              ["Foro: listado con título, autor y fecha", "Ruta /foro/ con respuestas, última actividad y filtros."],
              ["Crear hilo y responder", "Rutas /foro/nuevo y /foro/&lt;id&gt;/responder."],
              ["Solo usuarios autenticados leen y escriben", "Todas las rutas del foro exigen sesión y cuenta verificada."],
              ["Datos de prueba", "Usuarios en todos los estados e hilos con respuestas (app/seed.py)."],
              ["Control de versiones con ramas y PR", "Ramas por funcionalidad, commits descriptivos y Pull Request."],
          ], [6.3, 10.6]),
          ]

    # 2 -------------------------------------------------------------------
    s += [salto(), h1("2. Stack tecnológico"),
          p("Se ha elegido un stack <b>ligero, sin compilación y con renderizado en servidor</b>: arranca con un "
            "solo comando, no necesita Node.js ni un servidor de base de datos y todo el código es fácil de "
            "seguir durante una revisión en directo."),
          h2("2.1 Lenguajes"),
          tabla([
              ["Lenguaje", "Dónde se usa"],
              ["Python " + sys.version.split()[0], "Lógica de servidor, acceso a datos, pruebas y generación de manuales."],
              ["HTML5 + Jinja2", "Plantillas de todas las páginas (app/templates)."],
              ["CSS3", "Hoja de estilos propia, responsive y sin frameworks (app/static/css/style.css)."],
              ["JavaScript (vanilla)", "Menú móvil y confirmación de acciones destructivas (app/static/js/main.js)."],
              ["SQL (SQLite)", "Esquema de la base de datos (app/schema.sql) y consultas parametrizadas."],
          ], [4.2, 12.7]),
          h2("2.2 Frameworks, librerías y herramientas"),
          tabla([
              ["Componente", "Versión", "Uso"],
              ["Flask", pkg("flask"), "Microframework web: rutas, blueprints, sesiones, plantillas."],
              ["Werkzeug", pkg("werkzeug"), "Servidor de desarrollo y hash de contraseñas (scrypt)."],
              ["Jinja2", pkg("jinja2"), "Motor de plantillas con autoescape de HTML."],
              ["Click", pkg("click"), "Comando de consola flask init-db."],
              ["SQLite", sqlite3.sqlite_version, "Base de datos embebida en un único fichero."],
              ["pytest", pkg("pytest"), "Pruebas automatizadas."],
              ["ReportLab", pkg("reportlab"), "Generación de estos manuales en PDF."],
              ["Git", git_version(), "Control de versiones."],
              ["GitHub", "—", "Repositorio remoto, Pull Requests y GitHub Actions (CI)."],
              ["Google Fonts", "—", "Tipografías Exo 2 (títulos) e Inter (texto)."],
          ], [3.4, 2.4, 11.1]),
          h2("2.3 Tamaño del proyecto"),
          tabla(estadisticas_codigo(), [7.0, 3.0, 3.0]),
          h2("2.4 Justificación de las decisiones"),
          lista([
              "<b>Flask</b> frente a Django: para una DEMO de este tamaño Flask permite ver todo el flujo "
              "(petición, permisos, consulta, plantilla) sin capas ocultas. Los blueprints mantienen el código "
              "separado por áreas.",
              "<b>SQLite con SQL directo</b> frente a un ORM: cero configuración, el esquema se lee en un único "
              "fichero y las consultas son explícitas. Todas usan parámetros (?) para evitar inyección SQL.",
              "<b>Renderizado en servidor</b> frente a SPA: menos piezas, funciona sin JavaScript, mejor "
              "accesibilidad y SEO para la parte pública.",
              "<b>CSS propio</b> frente a Bootstrap/Tailwind: la identidad visual se adapta al logotipo "
              "(azul petróleo) sin depender de un CDN ni de un proceso de compilación.",
              "<b>Alta de usuarios mixta</b> (ver capítulo 6): autorregistro con verificación de correo "
              "corporativo + gestión por administrador.",
          ]),
          ]

    # 3 -------------------------------------------------------------------
    s += [salto(), h1("3. Arquitectura"),
          p("La aplicación sigue el patrón <b>application factory</b> de Flask: "
            f"{c('create_app()')} crea la aplicación, carga la configuración y registra los módulos. "
            "Cada área funcional es un <b>blueprint</b> independiente:"),
          tabla([
              ["Módulo", "Responsabilidad"],
              ["app/__init__.py", "Fábrica de la aplicación, configuración, filtro de fechas y páginas de error."],
              ["app/public.py", "Blueprint public: inicio, servicios y contacto."],
              ["app/auth.py", "Blueprint auth: registro, verificación, login/logout, área privada y "
                              "decoradores login_required, verified_required y admin_required."],
              ["app/forum.py", "Blueprint forum: hilos, respuestas, búsqueda y moderación."],
              ["app/admin.py", "Blueprint admin: gestión de usuarios."],
              ["app/db.py", "Conexión SQLite por petición, creación del esquema y comando init-db."],
              ["app/security.py", "Protección CSRF para todos los formularios POST."],
              ["app/seed.py", "Usuarios e hilos de prueba."],
          ], [3.6, 13.3]),
          h2("3.1 Flujo de una petición"),
          lista([
              "El navegador solicita una URL; Flask la asocia a una función de un blueprint.",
              f"Antes de la vista, {c('security.csrf_protect')} valida el token en los POST y "
              f"{c('auth.load_logged_in_user')} carga el usuario de la sesión en {c('g.user')} "
              "(si la cuenta se ha desactivado, cierra la sesión).",
              "Los decoradores de permisos comprueban sesión, verificación y rol; si no se cumplen, redirigen "
              "al login, al área privada o devuelven 403.",
              f"La vista consulta SQLite mediante {c('get_db()')} con consultas parametrizadas.",
              "Se renderiza la plantilla Jinja2 (con autoescape) y se devuelve el HTML.",
          ], numerada=True),
          h2("3.2 Estructura del proyecto"),
          codigo("""
Demo Diplonautic/
├── app/
│   ├── __init__.py          Fábrica de la aplicación
│   ├── public.py            Web pública
│   ├── auth.py              Registro, verificación, sesión y permisos
│   ├── forum.py             Foro interno
│   ├── admin.py             Gestión de usuarios
│   ├── db.py                Base de datos y comando init-db
│   ├── security.py          Protección CSRF
│   ├── seed.py              Datos de prueba
│   ├── schema.sql           Esquema SQLite
│   ├── templates/           Plantillas Jinja2 (public, auth, forum, admin)
│   └── static/              CSS, JavaScript e imágenes
├── tests/                   Pruebas automatizadas (pytest)
├── docs/                    Manuales PDF, capturas y generador
├── .github/                 Plantilla de Pull Request y CI
├── .devcontainer/           Entorno de GitHub Codespaces
├── instance/                Base de datos local (no se versiona)
├── run.py                   Arranque del servidor
├── iniciar.bat              Arranque con doble clic en Windows
├── requirements.txt         Dependencias con versión fijada
└── README.md
""".replace("├──", "|--").replace("└──", "`--").replace("│", "|")),
          ]

    # 4 -------------------------------------------------------------------
    s += [h1("4. Modelo de datos"),
          p("La base de datos tiene tres tablas. Un usuario puede escribir muchos hilos y muchas respuestas; "
            "un hilo tiene muchas respuestas, que se borran en cascada al eliminar el hilo. Los usuarios no "
            "se borran, se <b>desactivan</b>, para conservar la autoría de los mensajes."),
          codigo("""
users (1) ----< threads (N)          users.id = threads.author_id
users (1) ----< posts   (N)          users.id = posts.author_id
threads (1) --< posts   (N)          threads.id = posts.thread_id  (ON DELETE CASCADE)
"""),
          ]
    for nombre, filas in tablas.items():
        s += [h2(f"Tabla {nombre}"), tabla(filas, [3.6, 1.8, 4.6, 6.9], escapar=True)]
    s += [nota("Las tablas de este capítulo se generan automáticamente a partir de "
               f"{c('app/schema.sql')} cada vez que se ejecuta el generador de manuales.")]

    # 5 -------------------------------------------------------------------
    s += [salto(), h1("5. Rutas de la aplicación"),
          p("Tabla generada desde el mapa de URLs de Flask. <b>Sesión</b> = cualquier usuario autenticado; "
            "<b>Verificado</b> = autenticado y con el correo verificado; <b>Admin</b> = verificado y con rol "
            "administrador; <b>Autor o admin</b> = el autor del contenido o un administrador."),
          tabla(rutas(), [1.6, 6.5, 2.3, 6.5], escapar=True),
          ]

    # 6 -------------------------------------------------------------------
    s += [salto(), h1("6. Usuarios, roles y estados"),
          h2("6.1 Decisión: alta de usuarios mixta"),
          p("El enunciado permite elegir entre registro de empleados o alta por un administrador. "
            "Se han implementado <b>los dos</b>, combinados:"),
          lista([
              "<b>Autorregistro</b> restringido al dominio corporativo (@diplonautic.com, configurable con "
              f"{c('ALLOWED_EMAIL_DOMAIN')}). La cuenta nace con rol <i>empleado</i> y <b>sin verificar</b>.",
              "<b>Verificación por correo</b>: enlace con un token aleatorio de un solo uso que caduca en 48 h. "
              "En la base de datos solo se guarda su hash SHA-256.",
              "<b>Gestión por administrador</b>: puede dar de alta usuarios ya verificados, verificar cuentas "
              "pendientes, reenviar el enlace, cambiar el rol y desactivar cuentas.",
          ]),
          p("<b>Motivo:</b> el administrador no se convierte en un cuello de botella para cada alta, pero se "
            "mantiene el control: sin correo corporativo verificado no se accede al foro, el rol de "
            "administrador solo lo concede otro administrador y cualquier cuenta se puede desactivar al momento."),
          nota("<b>Correo simulado.</b> La DEMO no tiene servidor SMTP. El correo de verificación se muestra en "
               "pantalla (y en la consola del servidor) con el mismo contenido que se enviaría. Para producción "
               f"bastaría con sustituir {c('render_demo_email()')} por un envío real (p. ej. Flask-Mail)."),
          h2("6.2 Estados de una cuenta"),
          tabla([
              ["Estado", "Cómo se llega", "Qué puede hacer"],
              ["No verificado", "Registro propio, o alta por admin sin marcar 'verificado'.",
               "Iniciar sesión y ver su área privada. No puede leer ni escribir en el foro."],
              ["Verificado", "Pulsa el enlace del correo, o un admin lo verifica.",
               "Usar el foro completo según su rol."],
              ["Desactivado", "Un administrador desactiva la cuenta.",
               "Nada: no puede iniciar sesión y, si tenía sesión abierta, se cierra."],
          ], [3.0, 6.4, 7.5]),
          h2("6.3 Matriz de permisos"),
          tabla([
              ["Acción", "Visitante", "No verificado", "Empleado", "Admin"],
              ["Ver la web pública", "Sí", "Sí", "Sí", "Sí"],
              ["Registrarse", "Sí", "—", "—", "—"],
              ["Entrar al área privada", "No", "Sí", "Sí", "Sí"],
              ["Reenviar correo de verificación", "No", "Sí", "—", "—"],
              ["Leer el foro", "No", "No", "Sí", "Sí"],
              ["Crear hilos y responder", "No", "No", "Sí", "Sí"],
              ["Cerrar / eliminar hilos y respuestas propios", "No", "No", "Sí", "Sí"],
              ["Cerrar / eliminar contenido de otros", "No", "No", "No", "Sí"],
              ["Fijar hilos", "No", "No", "No", "Sí"],
              ["Gestionar usuarios", "No", "No", "No", "Sí"],
          ], [6.9, 2.3, 2.7, 2.3, 2.7]),
          p("Un administrador no puede quitarse a sí mismo el rol ni desactivar su propia cuenta, para que "
            "siempre quede al menos un administrador operativo."),
          ]

    # 7 -------------------------------------------------------------------
    s += [h1("7. Seguridad"),
          lista([
              "<b>Contraseñas</b> con hash scrypt y sal (Werkzeug); nunca se guardan en claro. Política mínima: "
              "8 caracteres combinando letras y números.",
              "<b>Mensajes de error genéricos</b> en el login: no revelan si un correo existe.",
              "<b>Sesión</b> en cookie firmada con SECRET_KEY, HttpOnly y SameSite=Lax. Se regenera al iniciar "
              "sesión (evita fijación de sesión) y el cierre de sesión es por POST.",
              "<b>CSRF</b>: todos los formularios POST llevan un token por sesión comparado en tiempo constante.",
              "<b>Inyección SQL</b>: todas las consultas usan parámetros. Los únicos fragmentos SQL dinámicos "
              "(filtros del panel) salen de un diccionario fijo, nunca de la entrada del usuario.",
              "<b>XSS</b>: Jinja2 escapa automáticamente todo el contenido; los mensajes del foro se muestran "
              "como texto plano.",
              "<b>Redirecciones abiertas</b>: el parámetro next solo acepta rutas internas.",
              "<b>Cabeceras de proxy</b>: X-Forwarded-* solo se tienen en cuenta con TRUST_PROXY=1 "
              "(activado en Codespaces); sin proxy delante, nadie puede falsear el dominio de los enlaces.",
              "<b>Tokens de verificación</b> aleatorios (secrets), de un solo uso, con caducidad y guardados con hash.",
              "<b>Control de acceso</b> en el servidor con decoradores, no solo ocultando botones.",
          ]),
          nota("Antes de un despliegue real: definir SECRET_KEY por variable de entorno, servir con HTTPS "
               "(SESSION_COOKIE_SECURE=True), usar un servidor WSGI (waitress o gunicorn) y añadir límite de "
               "intentos de login.", "warn"),
          ]

    # 8 -------------------------------------------------------------------
    s += [salto(), h1("8. Instalación y configuración")] + instalacion() + [
        h2("8.1 Variables de entorno"),
        tabla([
            ["Variable", "Por defecto", "Descripción"],
            ["SECRET_KEY", "valor de desarrollo", "Clave para firmar la sesión. Obligatoria en producción."],
            ["ALLOWED_EMAIL_DOMAIN", "diplonautic.com", "Dominio permitido en el registro. Vacío = cualquiera."],
            ["PORT", "5000", "Puerto del servidor local."],
            ["HOST", "127.0.0.1", "Interfaz de escucha; Codespaces usa 0.0.0.0."],
            ["TRUST_PROXY", "(desactivado)", "Con 1 confía en las cabeceras X-Forwarded-* del proxy (Codespaces)."],
            ["FLASK_DEBUG", "(desactivado)", "Con 1 activa el modo depuración y la recarga automática."],
        ], [5.0, 3.4, 8.5], escapar=True),
        h2("8.2 Comandos útiles"),
        tabla([
            ["Comando", "Para qué sirve"],
            ["python run.py", "Arranca la web en http://127.0.0.1:5000"],
            ["flask --app app init-db", "Borra la base de datos y la recrea con los datos de prueba."],
            ["python -m pytest", "Ejecuta las pruebas automatizadas."],
            ["python docs/generar_manuales.py", "Regenera los manuales PDF técnico y de usuario."],
        ], [6.0, 10.9], escapar=True),
    ]

    # 9 -------------------------------------------------------------------
    s += [salto(), h1("9. Datos y usuarios de prueba"),
          p("Al crear la base de datos se cargan usuarios en <b>todos los estados</b> (verificado, no "
            "verificado y desactivado) y seis hilos de ejemplo con respuestas, en las tres categorías del foro, "
            "uno fijado, uno cerrado y uno escrito por la cuenta desactivada (para mostrar que su historial se conserva)."),
          tabla_usuarios_prueba(),
          nota("Credenciales ficticias, solo para la DEMO local. Los correos no existen y nunca se envía nada."),
          ]

    # 10 ------------------------------------------------------------------
    s += [h1("10. Pruebas automatizadas"),
          p(f"El proyecto incluye <b>{n_pruebas or 'varias'} pruebas</b> con pytest. Cada prueba usa una base "
            "de datos temporal recién creada con los datos de prueba, por lo que son independientes entre sí."),
          codigo("python -m pytest"),
          tabla([
              ["Fichero", "Qué comprueba"],
              ["tests/test_public.py", "Páginas públicas, formulario de contacto y error 404."],
              ["tests/test_auth.py", "Login y logout, cuentas desactivadas, redirección segura, registro "
                                     "(dominio, contraseña, duplicados), verificación (flujo completo, "
                                     "caducidad, un solo uso, reenvío)."],
              ["tests/test_admin.py", "Permisos del panel, filtros, verificar, crear, cambiar rol, desactivar y "
                                      "protección contra la autodesactivación."],
              ["tests/test_forum.py", "Acceso solo verificado, listado con título/autor/fecha, fijados primero, "
                                      "crear y responder, hilos cerrados, búsqueda, escape de HTML y moderación."],
              ["tests/test_security.py", "CSRF activo, cookies de sesión y contraseñas con hash."],
          ], [4.4, 12.5]),
          p("Además, el flujo de GitHub Actions (.github/workflows/tests.yml) ejecuta las pruebas en cada "
            "push y en cada Pull Request."),
          ]

    # 11 ------------------------------------------------------------------
    s += [salto(), h1("11. Control de versiones"),
          h2("11.1 Estrategia de ramas"),
          p("Se usa un flujo sencillo basado en ramas de funcionalidad (<i>feature branches</i>): "
            f"{c('main')} contiene siempre una versión estable y cada funcionalidad se desarrolla en su "
            "propia rama, que se integra mediante Pull Request con descripción. Las fusiones se hacen con "
            f"{c('--no-ff')} para que cada rama quede visible en el historial."),
          tabla([
              ["Rama", "Contenido"],
              ["main", "Rama principal y estable."],
              ["feature/web-publica", "Fábrica de la app, páginas públicas y estilos."],
              ["feature/autenticacion", "Base de datos, CSRF, registro, verificación, login, roles y panel admin."],
              ["feature/foro", "Foro interno: hilos, respuestas, búsqueda y moderación."],
              ["test/pruebas-automatizadas", "Batería de pruebas con pytest."],
              ["docs/manuales", "README, manuales PDF, plantilla de PR y CI."],
              ["feature/codespaces", "Entorno de GitHub Codespaces y enlaces que funcionan tras un proxy."],
          ], [5.2, 11.7]),
          p("Ramas presentes en el repositorio al generar este documento: "
            + ", ".join(c(r) for r in ramas) + "."),
          h2("11.2 Convención de commits"),
          p("Mensajes en español siguiendo <b>Conventional Commits</b>: un prefijo de tipo, un ámbito opcional "
            "y un resumen en imperativo, con un cuerpo que explica el qué y el porqué."),
          tabla([
              ["Prefijo", "Uso"],
              ["feat", "Nueva funcionalidad."],
              ["fix", "Corrección de un error."],
              ["style", "Cambios visuales o de estilos sin cambiar la lógica."],
              ["test", "Pruebas automatizadas."],
              ["docs", "Documentación."],
              ["ci", "Integración continua."],
              ["chore", "Tareas de mantenimiento (configuración, dependencias)."],
          ], [3.0, 13.9]),
          h2("11.3 Pull Requests"),
          p("Cada rama se integra con un Pull Request que sigue la plantilla "
            f"{c('.github/pull_request_template.md')}: resumen, cambios, cómo probarlo y checklist "
            "(pruebas en verde, sin datos sensibles, documentación actualizada). La CI de GitHub Actions "
            "ejecuta las pruebas automáticamente en cada PR."),
          h2("11.4 Historial de commits"),
          p("Generado con git log al construir este documento (del más reciente al más antiguo):"),
          tabla(historial, [1.8, 2.2, 12.9], escapar=True),
          ]

    # 12 ------------------------------------------------------------------
    s += [salto(), h1("12. Uso de IA en el desarrollo"),
          p("Siguiendo las normas de la prueba, el proyecto se ha desarrollado con apoyo de un asistente de IA "
            "(<b>Claude Code</b>, de Anthropic) integrado en el entorno de trabajo. La IA se ha usado como "
            "herramienta, con revisión humana de cada paso:"),
          lista([
              "Análisis del enunciado y propuesta de arquitectura y stack.",
              "Generación del código por funcionalidades, una rama cada vez.",
              "Revisión visual en el navegador y corrección de errores de maquetación detectados.",
              "Redacción de la batería de pruebas y ejecución hasta dejarla en verde.",
              "Redacción de los mensajes de commit, la descripción de los Pull Requests y esta documentación.",
          ]),
          p("Todas las decisiones están documentadas en el código y en este manual para poder explicarlas y "
            "modificarlas en directo durante la entrevista técnica."),
          h1("13. Limitaciones y mejoras futuras"),
          tabla([
              ["Limitación actual", "Mejora propuesta"],
              ["El correo de verificación se muestra en pantalla.", "Envío real por SMTP (Flask-Mail) o un servicio transaccional."],
              ["No hay recuperación de contraseña.", "Flujo de 'he olvidado mi contraseña' con token, igual que la verificación."],
              ["Sin límite de intentos de login.", "Bloqueo temporal tras varios fallos (Flask-Limiter)."],
              ["Los mensajes no se pueden editar ni adjuntar ficheros.", "Edición con historial y adjuntos (fotos de averías)."],
              ["SQLite y servidor de desarrollo.", "PostgreSQL + SQLAlchemy/Alembic y despliegue con gunicorn/waitress en Docker."],
              ["Sin notificaciones.", "Avisos por correo cuando responden a un hilo propio."],
              ["Fechas con la hora local del servidor.", "Guardar en UTC y mostrar en la zona horaria del usuario."],
          ], [7.4, 9.5]),
          h1("14. Regenerar esta documentación"),
          p("Los dos manuales se generan con un script, por lo que pueden actualizarse tras cualquier cambio "
            "en el código:"),
          codigo("python docs/generar_manuales.py"),
          p(f"Salida: {c('docs/Manual_Tecnico_Diplonautic.pdf')} y {c('docs/Manual_Usuario_Diplonautic.pdf')}. "
            "Las rutas, el modelo de datos, las versiones, el número de pruebas, las estadísticas de código y "
            "el historial de Git se leen del proyecto en el momento de la generación."),
          ]
    return s


# ==========================================================================
# Manual de usuario
# ==========================================================================
def manual_usuario():
    s = []
    s += [h1("1. Introducción"),
          p("Este manual explica cómo usar la DEMO de la web corporativa de <b>Diplonautic</b>. La web tiene "
            "dos partes:"),
          lista([
              "<b>Web pública</b>, visible para cualquier visitante: presentación de la empresa, servicios y contacto.",
              "<b>Área privada para empleados</b>, con acceso mediante usuario y contraseña, que incluye el "
              "<b>foro interno</b> para compartir dudas, avisos e incidencias técnicas.",
          ]),
          h2("1.1 Tipos de usuario"),
          tabla([
              ["Tipo", "Descripción"],
              ["Visitante", "Cualquier persona sin sesión iniciada. Solo ve la web pública."],
              ["Empleado no verificado", "Se ha registrado pero aún no ha confirmado su correo. Puede entrar a "
                                         "su área privada, pero no al foro."],
              ["Empleado verificado", "Ha confirmado su correo. Puede leer, crear hilos y responder en el foro."],
              ["Administrador", "Empleado verificado con permisos extra: gestiona usuarios y modera el foro."],
              ["Cuenta desactivada", "Un administrador ha desactivado la cuenta. No puede iniciar sesión."],
          ], [4.4, 12.5]),
          h1("2. Puesta en marcha")] + instalacion() + [
          p(f"Con la aplicación en marcha, abrir {c('http://127.0.0.1:5000')} en el navegador."),
          ]

    s += [salto(), h1("3. Usuarios de prueba"),
          p("La DEMO incluye estas cuentas para probar todos los casos:"),
          tabla_usuarios_prueba(),
          nota("Para volver a los datos originales en cualquier momento: " + c("flask --app app init-db")),
          ]

    s += [salto(), h1("4. Web pública"),
          p("La página de inicio presenta la empresa, sus servicios principales y un acceso directo al área de "
            "empleados. Desde el menú superior se navega a <b>Inicio</b>, <b>Servicios</b> y <b>Contacto</b>."),
          captura("01_inicio.jpg", "Figura 1. Página de inicio."),
          lista([
              "<b>Servicios</b>: catálogo de servicios (refrigeración, climatización, electricidad, fontanería, "
              "electrónica y mantenimiento) y forma de trabajo.",
              "<b>Contacto</b>: datos de contacto y formulario. En la DEMO el formulario es solo visual: al "
              "enviarlo se muestra un aviso y no se guarda ni envía ningún dato.",
              "En el móvil, el menú se abre con el botón de tres líneas de la esquina superior derecha.",
          ]),
          ]

    s += [salto(), h1("5. Registro y verificación"),
          h2("5.1 Crear una cuenta"),
          lista([
              "Pulsar <b>Acceso empleados</b> y después <b>Regístrate con tu correo corporativo</b>.",
              "Completar nombre, correo corporativo (@diplonautic.com), departamento y contraseña (mínimo 8 "
              "caracteres con letras y números) y pulsar <b>Crear cuenta</b>.",
          ], numerada=True),
          captura("03_registro.jpg", "Figura 2. Formulario de registro."),
          h2("5.2 Verificar el correo"),
          p("Tras el registro se envía un correo con un enlace de verificación que caduca en 48 horas. "
            "<b>En la DEMO no hay servidor de correo</b>, así que el mensaje se muestra directamente en pantalla: "
            "basta con pulsar <b>Verificar mi cuenta</b>."),
          captura("04_correo_verificacion.jpg", "Figura 3. Correo de verificación simulado."),
          nota("Si el enlace ha caducado o se ha perdido, iniciar sesión y pulsar <b>Reenviar correo de "
               "verificación</b> en el área privada, o pedir a un administrador que verifique la cuenta."),
          ]

    s += [salto(), h1("6. Iniciar y cerrar sesión"),
          lista([
              "Pulsar <b>Acceso empleados</b> en el menú.",
              "Introducir el correo corporativo y la contraseña y pulsar <b>Iniciar sesión</b>.",
              "Para salir, pulsar <b>Salir</b> en el menú superior.",
          ], numerada=True),
          captura("02_acceso.jpg", "Figura 4. Pantalla de acceso de empleados."),
          tabla([
              ["Mensaje", "Qué significa"],
              ["Correo o contraseña incorrectos.", "Alguno de los dos datos no es correcto."],
              ["Tu cuenta está desactivada.", "Un administrador ha desactivado la cuenta; hay que contactar con él."],
              ["Tu cuenta aún no está verificada.", "Falta confirmar el correo para acceder al foro."],
          ], [6.0, 10.9]),
          ]

    s += [salto(), h1("7. Área privada"),
          p("Tras iniciar sesión se muestra el área privada con los datos de la cuenta (nombre, correo, "
            "departamento, rol, estado y último acceso) y accesos directos a las secciones disponibles."),
          p("Si la cuenta <b>no está verificada</b>, aparece un aviso con el botón para reenviar el correo de "
            "verificación y el acceso al foro aparece bloqueado:"),
          captura("05_area_no_verificado.jpg", "Figura 5. Área privada de una cuenta pendiente de verificación."),
          p("Con la cuenta verificada, el menú muestra <b>Foro</b> y, para administradores, <b>Usuarios</b>:"),
          captura("10_area_admin.jpg", "Figura 6. Área privada de un administrador."),
          ]

    s += [salto(), h1("8. Foro interno"),
          p("El foro es el espacio del equipo para plantear <b>dudas</b> técnicas, publicar <b>avisos</b> y "
            "documentar <b>incidencias técnicas</b>. Solo pueden usarlo empleados con la cuenta verificada."),
          h2("8.1 Listado de hilos"),
          p("Muestra cada hilo con su título, categoría, autor, fecha de publicación, número de respuestas y "
            "última actividad. Los hilos <b>fijados</b> por un administrador aparecen siempre arriba; el resto "
            "se ordena por actividad más reciente."),
          captura("06_foro_listado.jpg", "Figura 7. Listado de hilos del foro."),
          lista([
              "<b>Filtrar</b>: pulsar Todos, Duda, Aviso o Incidencia técnica.",
              "<b>Buscar</b>: escribir en el cuadro de búsqueda y pulsar la lupa (busca en título y texto).",
              "Con más de 10 hilos aparece la paginación al final de la lista.",
          ]),
          h2("8.2 Crear un hilo"),
          lista([
              "Pulsar <b>Nuevo hilo</b>.",
              "Escribir un título descriptivo (5 a 120 caracteres).",
              "Elegir la categoría: Duda, Aviso o Incidencia técnica.",
              "Describir el problema indicando equipo y embarcación, y pulsar <b>Publicar hilo</b>.",
          ], numerada=True),
          captura("09_foro_nuevo_hilo.jpg", "Figura 8. Formulario de nuevo hilo."),
          h2("8.3 Leer y responder"),
          p("Al abrir un hilo se ve el mensaje original y todas las respuestas en orden. Al final de la página "
            "está el cuadro <b>Tu respuesta</b>: escribir el texto y pulsar <b>Responder</b>."),
          captura("07_foro_hilo.jpg", "Figura 9. Hilo con las herramientas de moderación."),
          captura("08_foro_responder.jpg", "Figura 10. Formulario para responder."),
          h2("8.4 Gestionar mis mensajes"),
          tabla([
              ["Acción", "Quién puede", "Cómo"],
              ["Cerrar / reabrir un hilo", "Autor del hilo o administrador",
               "Botón Cerrar hilo. Un hilo cerrado no admite nuevas respuestas."],
              ["Eliminar un hilo", "Autor del hilo o administrador",
               "Botón Eliminar (pide confirmación). Se borran también sus respuestas."],
              ["Eliminar una respuesta", "Autor de la respuesta o administrador", "Enlace Eliminar respuesta."],
              ["Fijar / desfijar un hilo", "Solo administrador", "Botón Fijar."],
          ], [4.2, 4.6, 8.1]),
          ]

    s += [salto(), h1("9. Administración de usuarios"),
          p("Los administradores acceden desde <b>Usuarios</b> en el menú. El listado muestra cada empleado con "
            "su departamento, rol, estado y último acceso, y permite filtrar por <b>Verificados</b>, "
            "<b>No verificados</b>, <b>Administradores</b> y <b>Desactivados</b>."),
          captura("11_admin_usuarios.jpg", "Figura 11. Gestión de usuarios."),
          tabla([
              ["Botón", "Qué hace"],
              ["Verificar", "Marca la cuenta como verificada sin necesidad del correo."],
              ["Enviar enlace", "Genera un nuevo correo de verificación (en la DEMO se muestra en pantalla)."],
              ["Hacer admin / Quitar admin", "Cambia el rol del usuario."],
              ["Desactivar / Reactivar", "Bloquea o recupera el acceso. Sus mensajes del foro se conservan."],
          ], [5.0, 11.9]),
          p("Por seguridad, un administrador no puede quitarse el rol ni desactivar su propia cuenta."),
          h2("9.1 Dar de alta un usuario"),
          lista([
              "Pulsar <b>Nuevo usuario</b>.",
              "Rellenar nombre, correo corporativo, departamento, rol y una contraseña inicial.",
              "Dejar marcado <b>Marcar como verificado</b> si el administrador responde de la identidad del "
              "empleado; si se desmarca, el empleado tendrá que verificar su correo.",
              "Pulsar <b>Crear usuario</b> y comunicar la contraseña inicial al empleado por un canal seguro.",
          ], numerada=True),
          captura("12_admin_nuevo_usuario.jpg", "Figura 12. Alta de un nuevo usuario."),
          ]

    s += [salto(), h1("10. Preguntas frecuentes"),
          tabla([
              ["Problema", "Solución"],
              ["No veo el enlace Foro en el menú.", "La cuenta no está verificada. Reenviar el correo desde el "
                                                    "área privada o pedir la verificación a un administrador."],
              ["El registro dice 'Usa tu correo corporativo'.", "Solo se admiten correos @diplonautic.com."],
              ["El formulario ha caducado.", "La página llevaba mucho tiempo abierta o se cerró la sesión. "
                                              "Recargar la página y repetir la acción."],
              ["No puedo responder a un hilo.", "El hilo está cerrado. Su autor o un administrador puede reabrirlo."],
              ["Quiero dejar la DEMO como al principio.", "Ejecutar flask --app app init-db."],
              ["La página no carga.", "Comprobar que la consola de iniciar.bat / run.py sigue abierta y "
                                      "visitar http://127.0.0.1:5000."],
          ], [6.0, 10.9]),
          ]
    return s


# ==========================================================================
def main(argv):
    que = argv[1] if len(argv) > 1 else "todos"
    generados = []
    if que in ("todos", "tecnico"):
        generados.append(construir(os.path.join(DOCS_DIR, "Manual_Tecnico_Diplonautic.pdf"),
                                   "Manual técnico", "Arquitectura, stack, instalación y desarrollo",
                                   manual_tecnico(), VERSION_DOC))
    if que in ("todos", "usuario"):
        generados.append(construir(os.path.join(DOCS_DIR, "Manual_Usuario_Diplonautic.pdf"),
                                   "Manual de usuario", "Guía de uso de la web y del foro interno",
                                   manual_usuario(), VERSION_DOC))
    for ruta in generados:
        print("Generado:", os.path.relpath(ruta, ROOT_DIR))


if __name__ == "__main__":
    main(sys.argv)
