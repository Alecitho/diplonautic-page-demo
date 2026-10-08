-- Esquema de la base de datos SQLite de la DEMO de Diplonautic.
-- Se ejecuta completo al inicializar (borra y recrea las tablas).

DROP TABLE IF EXISTS posts;
DROP TABLE IF EXISTS threads;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT    NOT NULL,
    email                 TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash         TEXT    NOT NULL,
    role                  TEXT    NOT NULL DEFAULT 'empleado'
                                  CHECK (role IN ('empleado', 'admin')),
    department            TEXT,
    is_verified           INTEGER NOT NULL DEFAULT 0 CHECK (is_verified IN (0, 1)),
    is_active             INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    verification_token    TEXT,          -- hash SHA-256 del token, nunca el token en claro
    verification_sent_at  TEXT,
    verified_at           TEXT,
    created_at            TEXT    NOT NULL,
    last_login_at         TEXT
);

-- Hilos del foro interno
CREATE TABLE threads (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    title             TEXT    NOT NULL,
    body              TEXT    NOT NULL,
    category          TEXT    NOT NULL CHECK (category IN ('duda', 'aviso', 'incidencia')),
    author_id         INTEGER NOT NULL REFERENCES users (id),
    is_pinned         INTEGER NOT NULL DEFAULT 0 CHECK (is_pinned IN (0, 1)),
    is_closed         INTEGER NOT NULL DEFAULT 0 CHECK (is_closed IN (0, 1)),
    created_at        TEXT    NOT NULL,
    last_activity_at  TEXT    NOT NULL
);

-- Respuestas a un hilo (se borran junto con el hilo)
CREATE TABLE posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id   INTEGER NOT NULL REFERENCES threads (id) ON DELETE CASCADE,
    author_id   INTEGER NOT NULL REFERENCES users (id),
    body        TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);

CREATE INDEX idx_threads_activity ON threads (is_pinned DESC, last_activity_at DESC);
CREATE INDEX idx_posts_thread ON posts (thread_id, created_at);
