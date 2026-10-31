"""Busca imágenes libres en Wikimedia Commons y las integra como Base64.

Este script se usa durante el desarrollo; la aplicación no realiza solicitudes
externas en tiempo de ejecución. Requiere Pillow para normalizar las imágenes.
"""

from __future__ import annotations

import base64
import html
import io
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "CrisSteelAcademic/1.0 (TI3041 educational image sourcing)"
OUTPUT_MODULE = ROOT / "catalogo" / "imagenes_productos.py"
OUTPUT_SOURCES = ROOT / "docs" / "fuentes_imagenes.md"
OUTPUT_CONTACT = ROOT / "docs" / "evidencias" / "06-productos-base64-contacto.jpg"
CACHE_DIR = ROOT / "scripts" / ".cache_commons"
MIN_API_INTERVAL_SECONDS = 2.6
LAST_API_REQUEST = 0.0

IMAGE_QUERIES = {
    1: "hammer drill",
    2: "angle grinder",
    3: "circular saw",
    4: "orbital sander",
    5: "rotary hammer drill",
    6: "cordless screwdriver",
    7: "claw hammer",
    8: "screwdriver set",
    9: "combination pliers",
    10: "adjustable wrench",
    11: "hand saw",
    12: "spirit level",
    13: "tape measure",
    14: "combination wrench set",
    15: "drywall screws",
    16: "nylon wall plugs",
    17: "steel nails",
    18: "hex bolts nuts washers",
    19: "construction adhesive cartridge",
    20: "silicone sealant cartridge",
    21: "enamel paint can",
    22: "wall paint can",
    23: "wood varnish",
    24: "paint brush",
    25: "paint roller",
    26: "paint thinner bottle",
    27: "yellow hard hat safety",
    28: "clear safety glasses",
    29: "leather work gloves",
    30: "hearing protection earmuffs",
    31: "dust mask respirator",
    32: "metal cutting disc",
    33: "cement bag construction",
    34: "tile adhesive bag",
    35: "putty knife",
    36: "electric extension cord",
    37: "black electrical tape",
    38: "LED light bulb",
    39: "brass ball valve",
    40: "braided flexible water hose",
}

PREFERRED_FILES = {
    19: "Kitchen renovation 9a construction adhesive on bricks before placing mantle board on top.JPG",
    20: "Silicone-Sealant-1001U 43333-480x360 (4817475284).jpg",
    21: "Paint-can.jpg",
    31: "Dust mask.jpg",
    32: "Winkelschleifer Trennscheibe Metall.jpg",
    33: "Cement bags.jpg",
    34: "NMCB 11 Community Relations in Rota, Spain (8429706).jpg",
    39: "Brass-Ball-Valve MF Butterfly 12592-360x480 (4999932531).jpg",
    40: "Flexible Toilet Hose - Metal Plumbing.jpg",
}

BAD_TITLE_TERMS = {
    "advertisement",
    "banner",
    "diagram",
    "drawing",
    "flag",
    "icon",
    "logo",
    "map",
    "poster",
    "sign",
    "symbol",
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFD", value)
    value = "".join(character for character in value if unicodedata.category(character) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def plain_text(value: str | None) -> str:
    if not value:
        return "Autor no informado"
    text = re.sub(r"<[^>]+>", "", value)
    return html.unescape(text).strip() or "Autor no informado"


def request_json(params: dict[str, str | int]) -> dict:
    global LAST_API_REQUEST

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(5):
        elapsed = time.monotonic() - LAST_API_REQUEST
        if elapsed < MIN_API_INTERVAL_SECONDS:
            time.sleep(MIN_API_INTERVAL_SECONDS - elapsed)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                LAST_API_REQUEST = time.monotonic()
                return json.load(response)
        except HTTPError as error:
            LAST_API_REQUEST = time.monotonic()
            if error.code != 429 or attempt == 4:
                raise
            retry_after = int(error.headers.get("Retry-After", "20"))
            time.sleep(max(retry_after, 20 + attempt * 10))
    raise RuntimeError("La API de Wikimedia Commons no respondió.")


def search_candidates(query: str) -> list[dict]:
    payload = request_json(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"{query} filetype:bitmap",
            "gsrnamespace": 6,
            "gsrlimit": 10,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size",
            "iiurlwidth": 330,
            "format": "json",
            "formatversion": 2,
            "origin": "*",
        }
    )
    candidates = []
    query_tokens = set(normalize(query).split()) - {"tool", "hardware", "construction"}

    for page in payload.get("query", {}).get("pages", []):
        image_info = (page.get("imageinfo") or [{}])[0]
        mime = image_info.get("mime", "")
        if not mime.startswith("image/") or mime in {"image/svg+xml", "image/tiff"}:
            continue
        metadata = image_info.get("extmetadata", {})
        license_name = metadata.get("LicenseShortName", {}).get("value")
        if not license_name:
            continue
        normalized_title = normalize(page.get("title", ""))
        score = sum(3 for token in query_tokens if token in normalized_title)
        score -= sum(7 for term in BAD_TITLE_TERMS if term in normalized_title)
        candidates.append(
            {
                "title": page.get("title", "").removeprefix("File:"),
                "download_url": image_info.get("thumburl") or image_info.get("url"),
                "source_url": image_info.get("descriptionurl")
                or f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(page.get('title', ''))}",
                "artist": plain_text(metadata.get("Artist", {}).get("value")),
                "license": plain_text(license_name),
                "license_url": metadata.get("LicenseUrl", {}).get("value", ""),
                "score": score,
            }
        )

    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def get_preferred_candidate(filename: str) -> dict:
    payload = request_json(
        {
            "action": "query",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size",
            "iiurlwidth": 330,
            "format": "json",
            "formatversion": 2,
            "origin": "*",
        }
    )
    page = payload.get("query", {}).get("pages", [{}])[0]
    image_info = (page.get("imageinfo") or [{}])[0]
    metadata = image_info.get("extmetadata", {})
    if not image_info.get("url") or not metadata.get("LicenseShortName", {}).get("value"):
        raise RuntimeError(f"El archivo preferido no está disponible: {filename}")
    return {
        "title": page.get("title", "").removeprefix("File:"),
        "download_url": image_info.get("thumburl") or image_info.get("url"),
        "source_url": image_info.get("descriptionurl"),
        "artist": plain_text(metadata.get("Artist", {}).get("value")),
        "license": plain_text(metadata.get("LicenseShortName", {}).get("value")),
        "license_url": metadata.get("LicenseUrl", {}).get("value", ""),
        "score": 100,
    }


def download_image(url: str) -> Image.Image:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                raw_image = response.read()
            break
        except HTTPError as error:
            if error.code != 429 or attempt == 4:
                raise
            retry_after = int(error.headers.get("Retry-After", "20"))
            time.sleep(max(retry_after, 20 + attempt * 10))
    image = Image.open(io.BytesIO(raw_image))
    return ImageOps.exif_transpose(image).convert("RGB")


def prepare_webp(image: Image.Image) -> tuple[str, Image.Image, bytes]:
    fitted = ImageOps.fit(
        image,
        (480, 320),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    buffer = io.BytesIO()
    fitted.save(buffer, format="WEBP", quality=72, method=6)
    webp_bytes = buffer.getvalue()
    encoded = base64.b64encode(webp_bytes).decode("ascii")
    return f"data:image/webp;base64,{encoded}", fitted, webp_bytes


def write_module(images: dict[int, str]) -> None:
    lines = [
        '"""Imágenes autocontenidas generadas desde Wikimedia Commons."""',
        "",
        "# No se realizan solicitudes externas al mostrar el sitio.",
        "PRODUCT_IMAGE_DATA = {",
    ]
    for product_id, data_uri in images.items():
        lines.append(f"    {product_id}: (")
        for index in range(0, len(data_uri), 100):
            lines.append(f"        {data_uri[index:index + 100]!r}")
        lines.append("    ),")
    lines.extend(["}", ""])
    OUTPUT_MODULE.write_text("\n".join(lines), encoding="utf-8")


def write_sources(sources: list[dict]) -> None:
    lines = [
        "# Fuentes de imágenes de productos",
        "",
        "Las imágenes se obtuvieron mediante la API de Wikimedia Commons, se recortaron a 480 × 320 px, se comprimieron como WebP y se integraron en Base64. Por eso el sitio no carga recursos visuales desde servidores externos.",
        "",
        "| ID | Producto buscado | Archivo original | Autor | Licencia |",
        "|---:|---|---|---|---|",
    ]
    for source in sources:
        license_text = source["license"]
        if source["license_url"]:
            license_text = f"[{license_text}]({source['license_url']})"
        lines.append(
            f"| {source['id']} | {source['query']} | "
            f"[{source['title']}]({source['source_url']}) | "
            f"{source['artist'].replace('|', '/')} | {license_text} |"
        )
    lines.extend(
        [
            "",
            "La información de autoría y licencia corresponde a los metadatos publicados por cada archivo en Wikimedia Commons.",
            "",
        ]
    )
    OUTPUT_SOURCES.write_text("\n".join(lines), encoding="utf-8")


def write_contact_sheet(previews: dict[int, Image.Image]) -> None:
    tile_width, tile_height = 240, 190
    sheet = Image.new("RGB", (tile_width * 5, tile_height * 8), "#171a1f")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=16)
    for index, (product_id, image) in enumerate(previews.items()):
        x = (index % 5) * tile_width
        y = (index // 5) * tile_height
        thumbnail = ImageOps.fit(image, (220, 147), method=Image.Resampling.LANCZOS)
        sheet.paste(thumbnail, (x + 10, y + 10))
        draw.rounded_rectangle((x + 16, y + 16, x + 50, y + 45), radius=8, fill="#f2b12c")
        draw.text((x + 25, y + 23), f"{product_id:02d}", fill="#171a1f", font=font)
    OUTPUT_CONTACT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUTPUT_CONTACT, format="JPEG", quality=88, optimize=True)


def main() -> None:
    images: dict[int, str] = {}
    sources: list[dict] = []
    previews: dict[int, Image.Image] = {}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    for product_id, query in IMAGE_QUERIES.items():
        cache_metadata = CACHE_DIR / f"{product_id:02d}.json"
        cache_image = CACHE_DIR / f"{product_id:02d}.webp"

        cached_candidate = (
            json.loads(cache_metadata.read_text(encoding="utf-8"))
            if cache_metadata.exists() and cache_image.exists()
            else None
        )
        preferred_file = PREFERRED_FILES.get(product_id)
        cache_is_current = cached_candidate and (
            preferred_file is None or cached_candidate.get("title") == preferred_file
        )

        if cache_is_current:
            candidate = cached_candidate
            webp_bytes = cache_image.read_bytes()
            preview = Image.open(io.BytesIO(webp_bytes)).convert("RGB")
            data_uri = f"data:image/webp;base64,{base64.b64encode(webp_bytes).decode('ascii')}"
        else:
            candidates = (
                [get_preferred_candidate(preferred_file)]
                if preferred_file
                else search_candidates(query)
            )
            if not candidates:
                raise RuntimeError(f"No se encontraron imágenes para el producto {product_id}: {query}")

            last_error: Exception | None = None
            for candidate in candidates:
                try:
                    original = download_image(candidate["download_url"])
                    data_uri, preview, webp_bytes = prepare_webp(original)
                    break
                except Exception as error:  # prueba el siguiente resultado disponible
                    last_error = error
            else:
                raise RuntimeError(f"No fue posible descargar una imagen para {query}") from last_error

            cache_metadata.write_text(
                json.dumps(candidate, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            cache_image.write_bytes(webp_bytes)

        images[product_id] = data_uri
        previews[product_id] = preview
        sources.append({"id": product_id, "query": query, **candidate})
        print(f"{product_id:02d}/40 · {candidate['title']} · {candidate['license']}")
        time.sleep(0.2)

    write_module(images)
    write_sources(sources)
    write_contact_sheet(previews)
    print(f"\nGeneradas {len(images)} imágenes Base64 en {OUTPUT_MODULE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
