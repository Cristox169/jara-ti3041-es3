#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def runserver_url():
    """Obtiene la URL solicitada para mostrarla antes de cargar Django."""
    if len(sys.argv) < 2 or sys.argv[1] != "runserver":
        return None

    host = "127.0.0.1"
    port = "8000"
    for argument in sys.argv[2:]:
        if argument.startswith("-"):
            continue
        if ":" in argument:
            host, port = argument.rsplit(":", 1)
        elif argument.isdigit():
            port = argument
        break

    if host in {"0", "0.0.0.0", "::"}:
        host = "127.0.0.1"
    return f"http://{host}:{port}/"


def main():
    """Run administrative tasks."""
    url = runserver_url()
    if url:
        print("=" * 62)
        print("ENLACE DE LA PAGINA CRISSTEEL:")
        print(url)
        print("=" * 62)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
