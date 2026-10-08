"""Foro interno: hilos y respuestas. Solo para empleados con la cuenta verificada."""
import math

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .auth import admin_required, verified_required
from .db import get_db, get_or_404, now_iso

bp = Blueprint("forum", __name__, url_prefix="/foro")

CATEGORIAS = {
    "duda": "Duda",
    "aviso": "Aviso",
    "incidencia": "Incidencia técnica",
}
POR_PAGINA = 10
TITULO_MIN, TITULO_MAX = 5, 120
TEXTO_MIN, TEXTO_MAX = 10, 5000


def get_thread_or_404(thread_id):
    return get_or_404(
        "SELECT t.*, u.name AS author_name, u.department AS author_department, u.role AS author_role"
        " FROM threads t JOIN users u ON u.id = t.author_id WHERE t.id = ?",
        (thread_id,),
    )


def can_moderate(author_id):
    """El autor puede gestionar su propio contenido; el administrador, cualquiera."""
    return g.user["role"] == "admin" or g.user["id"] == author_id


def validate_body(body):
    if not TEXTO_MIN <= len(body) <= TEXTO_MAX:
        return f"El mensaje debe tener entre {TEXTO_MIN} y {TEXTO_MAX} caracteres."
    return None


@bp.route("/")
@verified_required
def index():
    categoria = request.args.get("categoria", "")
    q = request.args.get("q", "").strip()
    pagina = max(request.args.get("pagina", 1, type=int), 1)

    where, params = ["1 = 1"], []
    if categoria in CATEGORIAS:
        where.append("t.category = ?")
        params.append(categoria)
    else:
        categoria = ""
    if q:
        where.append("(t.title LIKE ? OR t.body LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    where_sql = " AND ".join(where)

    db = get_db()
    total = db.execute(f"SELECT COUNT(*) FROM threads t WHERE {where_sql}", params).fetchone()[0]
    paginas = max(math.ceil(total / POR_PAGINA), 1)
    pagina = min(pagina, paginas)
    threads = db.execute(
        "SELECT t.*, u.name AS author_name,"
        "       (SELECT COUNT(*) FROM posts p WHERE p.thread_id = t.id) AS replies,"
        "       (SELECT u2.name FROM posts p2 JOIN users u2 ON u2.id = p2.author_id"
        "         WHERE p2.thread_id = t.id ORDER BY p2.created_at DESC, p2.id DESC LIMIT 1) AS last_author"
        " FROM threads t JOIN users u ON u.id = t.author_id"
        f" WHERE {where_sql}"
        " ORDER BY t.is_pinned DESC, t.last_activity_at DESC"
        " LIMIT ? OFFSET ?",
        params + [POR_PAGINA, (pagina - 1) * POR_PAGINA],
    ).fetchall()

    return render_template("forum/index.html", threads=threads, categorias=CATEGORIAS,
                           categoria=categoria, q=q, pagina=pagina, paginas=paginas, total=total)


@bp.route("/nuevo", methods=("GET", "POST"))
@verified_required
def new_thread():
    form = {"title": "", "category": request.args.get("categoria", "duda"), "body": ""}
    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in form}
        error = None
        if not TITULO_MIN <= len(form["title"]) <= TITULO_MAX:
            error = f"El título debe tener entre {TITULO_MIN} y {TITULO_MAX} caracteres."
        elif form["category"] not in CATEGORIAS:
            error = "Selecciona una categoría válida."
        else:
            error = validate_body(form["body"])

        if error:
            flash(error, "error")
        else:
            now = now_iso()
            db = get_db()
            cur = db.execute(
                "INSERT INTO threads (title, body, category, author_id, created_at, last_activity_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (form["title"], form["body"], form["category"], g.user["id"], now, now),
            )
            db.commit()
            flash("Hilo publicado.", "success")
            return redirect(url_for("forum.thread", thread_id=cur.lastrowid))

    return render_template("forum/nuevo.html", form=form, categorias=CATEGORIAS,
                           titulo_max=TITULO_MAX, texto_max=TEXTO_MAX)


@bp.route("/<int:thread_id>")
@verified_required
def thread(thread_id):
    thread = get_thread_or_404(thread_id)
    posts = get_db().execute(
        "SELECT p.*, u.name AS author_name, u.department AS author_department, u.role AS author_role"
        " FROM posts p JOIN users u ON u.id = p.author_id"
        " WHERE p.thread_id = ? ORDER BY p.created_at, p.id",
        (thread_id,),
    ).fetchall()
    return render_template("forum/hilo.html", thread=thread, posts=posts, categorias=CATEGORIAS,
                           can_moderate=can_moderate, texto_max=TEXTO_MAX)


@bp.route("/<int:thread_id>/responder", methods=("POST",))
@verified_required
def reply(thread_id):
    thread = get_thread_or_404(thread_id)
    if thread["is_closed"]:
        flash("Este hilo está cerrado y no admite nuevas respuestas.", "warning")
        return redirect(url_for("forum.thread", thread_id=thread_id))

    body = request.form.get("body", "").strip()
    error = validate_body(body)
    if error:
        flash(error, "error")
        return redirect(url_for("forum.thread", thread_id=thread_id) + "#responder")

    now = now_iso()
    db = get_db()
    cur = db.execute(
        "INSERT INTO posts (thread_id, author_id, body, created_at) VALUES (?, ?, ?, ?)",
        (thread_id, g.user["id"], body, now),
    )
    db.execute("UPDATE threads SET last_activity_at = ? WHERE id = ?", (now, thread_id))
    db.commit()
    flash("Respuesta publicada.", "success")
    return redirect(url_for("forum.thread", thread_id=thread_id) + f"#r{cur.lastrowid}")


@bp.route("/<int:thread_id>/fijar", methods=("POST",))
@admin_required
def toggle_pin(thread_id):
    thread = get_thread_or_404(thread_id)
    db = get_db()
    db.execute("UPDATE threads SET is_pinned = ? WHERE id = ?",
               (0 if thread["is_pinned"] else 1, thread_id))
    db.commit()
    flash("Hilo desfijado." if thread["is_pinned"] else "Hilo fijado al inicio del foro.", "success")
    return redirect(url_for("forum.thread", thread_id=thread_id))


@bp.route("/<int:thread_id>/cerrar", methods=("POST",))
@verified_required
def toggle_close(thread_id):
    thread = get_thread_or_404(thread_id)
    if not can_moderate(thread["author_id"]):
        abort(403)
    db = get_db()
    db.execute("UPDATE threads SET is_closed = ? WHERE id = ?",
               (0 if thread["is_closed"] else 1, thread_id))
    db.commit()
    flash("Hilo reabierto." if thread["is_closed"] else "Hilo cerrado: ya no admite respuestas.", "success")
    return redirect(url_for("forum.thread", thread_id=thread_id))


@bp.route("/<int:thread_id>/eliminar", methods=("POST",))
@verified_required
def delete_thread(thread_id):
    thread = get_thread_or_404(thread_id)
    if not can_moderate(thread["author_id"]):
        abort(403)
    db = get_db()
    db.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
    db.commit()
    flash("Hilo eliminado.", "success")
    return redirect(url_for("forum.index"))


@bp.route("/respuesta/<int:post_id>/eliminar", methods=("POST",))
@verified_required
def delete_post(post_id):
    post = get_or_404("SELECT * FROM posts WHERE id = ?", (post_id,))
    if not can_moderate(post["author_id"]):
        abort(403)
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    flash("Respuesta eliminada.", "success")
    return redirect(url_for("forum.thread", thread_id=post["thread_id"]))
