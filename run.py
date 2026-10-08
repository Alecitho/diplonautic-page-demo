"""Punto de entrada para ejecutar la DEMO en local: python run.py"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # En local solo escucha en 127.0.0.1; en Codespaces el contenedor define HOST=0.0.0.0.
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"\n  Diplonautic DEMO en marcha: http://127.0.0.1:{port}\n")
    app.run(host=host, port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
