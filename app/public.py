"""Parte pública de la web: inicio, servicios y contacto."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

bp = Blueprint("public", __name__)

SERVICIOS = [
    {
        "icono": "snow",
        "titulo": "Refrigeración marina",
        "texto": "Instalación y reparación de neveras, congeladores y cámaras frigoríficas "
                 "a bordo, con gases ecológicos y control de consumo.",
    },
    {
        "icono": "wind",
        "titulo": "Climatización",
        "texto": "Aire acondicionado y calefacción para veleros y yates: equipos "
                 "autocontenidos, chillers y mantenimiento preventivo.",
    },
    {
        "icono": "bolt",
        "titulo": "Electricidad a bordo",
        "texto": "Cuadros eléctricos, baterías de litio, cargadores, inversores y "
                 "conexión a puerto con certificación.",
    },
    {
        "icono": "drop",
        "titulo": "Fontanería y potabilizadoras",
        "texto": "Desalinizadoras, bombas de agua, circuitos sanitarios y "
                 "sistemas de aguas grises y negras.",
    },
    {
        "icono": "radar",
        "titulo": "Electrónica náutica",
        "texto": "Instalación de plotters, radares, pilotos automáticos y "
                 "redes NMEA 2000 integradas.",
    },
    {
        "icono": "wrench",
        "titulo": "Mantenimiento integral",
        "texto": "Planes de mantenimiento anual, invernaje y asistencia "
                 "técnica urgente en puerto.",
    },
]


@bp.route("/")
def index():
    return render_template("public/index.html", servicios=SERVICIOS[:3])


@bp.route("/servicios")
def servicios():
    return render_template("public/servicios.html", servicios=SERVICIOS)


@bp.route("/contacto", methods=("GET", "POST"))
def contacto():
    # Formulario solo visual: no se envía ningún correo ni se guarda el mensaje.
    if request.method == "POST":
        flash("Gracias por tu mensaje. Esta es una DEMO: el formulario no envía datos.", "info")
        return redirect(url_for("public.contacto"))
    return render_template("public/contacto.html")
