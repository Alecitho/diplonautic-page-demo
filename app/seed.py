"""Datos de prueba de la DEMO.

Todas las contraseñas son ficticias y solo sirven para probar la aplicación en local.
Ver la tabla completa de usuarios de prueba en el README y en los manuales.
"""
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

ADMIN_PASSWORD = "Admin1234"
EMPLEADO_PASSWORD = "Empleado1234"

# (nombre, correo, rol, departamento, verificado, activo)
TEST_USERS = [
    ("Laura Méndez", "admin@diplonautic.com", "admin", "Dirección", True, True),
    ("Ana García", "ana.garcia@diplonautic.com", "empleado", "Refrigeración", True, True),
    ("Carlos Ruiz", "carlos.ruiz@diplonautic.com", "empleado", "Electricidad", True, True),
    ("Marta Vidal", "marta.vidal@diplonautic.com", "empleado", "Electrónica", True, True),
    ("Lucía Martín", "lucia.martin@diplonautic.com", "empleado", "Climatización", False, True),
    ("Javier Soler", "javier.soler@diplonautic.com", "empleado", "Taller", False, True),
    ("Pedro Sanz", "pedro.sanz@diplonautic.com", "empleado", "Fontanería", True, False),
]


def ago(days=0, hours=0):
    return (datetime.now() - timedelta(days=days, hours=hours)).isoformat(timespec="seconds")


def seed_users(db):
    ids = {}
    admin_hash = generate_password_hash(ADMIN_PASSWORD)
    empleado_hash = generate_password_hash(EMPLEADO_PASSWORD)
    for i, (name, email, role, dept, verified, active) in enumerate(TEST_USERS):
        created = ago(days=60 - i * 5)
        cur = db.execute(
            "INSERT INTO users (name, email, password_hash, role, department, is_verified,"
            " is_active, verified_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, email, admin_hash if role == "admin" else empleado_hash, role, dept,
             int(verified), int(active), created if verified else None, created),
        )
        ids[email.split("@")[0]] = cur.lastrowid
    return ids


# Hilos de ejemplo: (clave autor, categoría, fijado, cerrado, hace_días, título, texto, respuestas)
# Cada respuesta: (clave autor, horas después de la publicación del hilo, texto)
TEST_THREADS = [
    ("admin", "aviso", True, False, 12,
     "Bienvenidos al foro interno de Diplonautic",
     "Este es el espacio para compartir dudas técnicas, avisos del taller e incidencias de las "
     "intervenciones.\n\nNormas básicas:\n- Un tema por hilo y un título descriptivo.\n"
     "- Indica modelo de equipo y embarcación cuando sea relevante.\n"
     "- Nada de datos personales de clientes.",
     [("ana.garcia", 3, "¡Genial! Por fin un sitio para dejar todo esto por escrito."),
      ("carlos.ruiz", 20, "Perfecto. ¿Podemos adjuntar fotos más adelante?"),
      ("admin", 26, "Está en la lista de mejoras, Carlos. De momento enlazad la carpeta compartida.")]),
    ("admin", "aviso", True, False, 2,
     "Nuevo procedimiento de recarga de gas R-452A",
     "A partir del lunes todas las recargas de R-452A deben registrarse en el libro de gases "
     "del taller con la matrícula de la embarcación y los kilos cargados. Inspección prevista "
     "para finales de mes.",
     [("ana.garcia", 4, "Entendido. ¿El libro sigue estando en la oficina del muelle 3?"),
      ("admin", 5, "Sí, y hay una copia digital en la carpeta de Refrigeración.")]),
    ("ana.garcia", "incidencia", False, False, 5,
     "Compresor Danfoss BD35F no arranca en el velero 'Tramontana'",
     "El cliente reporta que la nevera no enfría. El módulo electrónico da 3 parpadeos del LED "
     "(protección por velocidad mínima). La tensión en bornes es de 12,4 V en reposo pero cae a "
     "10,9 V al intentar arrancar.\n\n¿Alguien ha visto esto con baterías de litio nuevas?",
     [("carlos.ruiz", 2, "Mira la sección del cable desde el cuadro. Con 10,9 V en arranque "
                         "huele a caída de tensión: si es de 2,5 mm² y más de 5 m, se queda corto."),
      ("marta.vidal", 6, "Ojo también con el BMS: algunos limitan la corriente de pico y el "
                         "compresor lo interpreta como fallo."),
      ("ana.garcia", 30, "Era el cable: 2,5 mm² y 7 m de tirada. Cambiado a 6 mm² y arranca "
                         "a la primera. ¡Gracias!")]),
    ("carlos.ruiz", "duda", False, False, 4,
     "¿Qué cargador de puerto recomendáis para baterías de litio de 200 Ah?",
     "Tenemos que sustituir el cargador de un Beneteau Oceanis 38 al que el armador ha montado "
     "dos baterías LiFePO4 de 200 Ah. ¿Victron Skylla o Mastervolt ChargeMaster? Presupuesto ajustado.",
     [("marta.vidal", 5, "Victron Blue Smart IP22 30 A: perfil de litio configurable desde el "
                         "móvil y buen precio. El Skylla es excelente pero se sale de presupuesto.")]),
    ("marta.vidal", "incidencia", False, True, 9,
     "Plotter Garmin sin datos NMEA 2000 tras actualizar firmware",
     "Después de actualizar el GPSMAP 1243 a la última versión, dejó de mostrar datos del "
     "piloto automático y la sonda. La red tiene alimentación y terminadores correctos.",
     [("carlos.ruiz", 3, "¿Has revisado la selección de fuentes de datos? Tras actualizar a veces "
                         "se resetea a 'automático' y elige mal."),
      ("marta.vidal", 4, "Era eso. Seleccionando las fuentes a mano vuelve todo. Cierro el hilo.")]),
    ("pedro.sanz", "duda", False, False, 20,
     "Recambios de membrana para potabilizadora Schenker",
     "¿Alguien sabe si el proveedor de Alicante sigue teniendo membranas para el modelo Zen 30?",
     [("ana.garcia", 24, "Sí, pero con 2 semanas de plazo. Mejor pedirlas con antelación.")]),
]


def seed_forum(db, users):
    for author, category, pinned, closed, days, title, body, replies in TEST_THREADS:
        created = datetime.now() - timedelta(days=days)
        last = created
        cur = db.execute(
            "INSERT INTO threads (title, body, category, author_id, is_pinned, is_closed,"
            " created_at, last_activity_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, body, category, users[author], int(pinned), int(closed),
             created.isoformat(timespec="seconds"), created.isoformat(timespec="seconds")),
        )
        thread_id = cur.lastrowid
        for reply_author, hours, text in replies:
            last = min(created + timedelta(hours=hours), datetime.now())
            db.execute(
                "INSERT INTO posts (thread_id, author_id, body, created_at) VALUES (?, ?, ?, ?)",
                (thread_id, users[reply_author], text, last.isoformat(timespec="seconds")),
            )
        db.execute("UPDATE threads SET last_activity_at = ? WHERE id = ?",
                   (last.isoformat(timespec="seconds"), thread_id))


def seed_database(db):
    users = seed_users(db)
    seed_forum(db, users)
    db.commit()
