import os
import sys
import threading
import webbrowser

from django.contrib.staticfiles.management.commands.runserver import (
    Command as StaticRunserverCommand,
)


class Command(StaticRunserverCommand):
    """Muestra la URL principal y abre el sitio cuando el servidor está listo."""

    default_addr = "127.0.0.1"
    default_port = "8000"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--no-browser",
            action="store_true",
            help="No abrir el navegador automáticamente.",
        )

    def handle(self, *args, **options):
        self.open_browser = not options.pop("no_browser", False)
        super().handle(*args, **options)

    @staticmethod
    def open_url(url):
        try:
            if sys.platform == "win32":
                os.startfile(url)
            else:
                webbrowser.open_new_tab(url)
        except OSError:
            webbrowser.open_new_tab(url)

    def on_bind(self, server_port):
        super().on_bind(server_port)
        host = self.addr
        if host in {"0", "0.0.0.0", "::"}:
            host = "127.0.0.1"
        url = f"{self.protocol}://{host}:{server_port}/"

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 62))
        self.stdout.write(self.style.SUCCESS("PAGINA DE CRISSTEEL LISTA - ABRE ESTE ENLACE:"))
        self.stdout.write(self.style.SUCCESS(url))
        if self.open_browser:
            self.stdout.write("El navegador se abrirá automáticamente.")
            opener = threading.Timer(0.8, self.open_url, args=(url,))
            opener.daemon = True
            opener.start()
        self.stdout.write(
            self.style.SUCCESS("=" * 62)
        )
