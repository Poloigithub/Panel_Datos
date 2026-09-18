"""Bajas laborales, quinto sondeo: ¿hay provincia dentro de las hojas?

Ya está todo localizado. La Seguridad Social publica la incapacidad temporal
en hojas de cálculo, dos por ejercicio, con nombres que cambian de un año a
otro -«Publicación IT mcss 2026», «Publicacion_IT_SISTEMA_2026_Junio»,
«Publicacion_IT_mcss+inss+ism+2025»- y direcciones con UUID, así que hay que
leerlas del índice. Eso ya se sabe hacer.

Queda la única pregunta que decide la sección: **si dentro hay provincia**.

Las siglas dicen quién gestiona la baja: `mcss` son las mutuas colaboradoras,
`inss` el Instituto Nacional de la Seguridad Social e `ism` el Instituto Social
de la Marina. El fichero que las junta es el del sistema entero, y es además el
pequeño -1,6 MB frente a 13-, así que se empieza por ahí.
"""

from __future__ import annotations

import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import xls  # noqa: E402
import xlsx  # noqa: E402

SALIDA = RAIZ / "sondeos"
WCM = "https://www.seg-social.es/wps/wcm/connect/wss/"

FICHEROS = [
    ("2026 · sistema (mcss+inss+ism)",
     WCM + "5baca09c-341b-4922-8641-cb93bf1f47d8/"
     "Publicacion_IT_SISTEMA_2026_Junio.xlsx?MOD=AJPERES"),
    ("2025 · sistema (mcss+inss+ism)",
     WCM + "58bb210f-343b-4591-a923-e11217cff5d1/"
     "Publicacion_IT_mcss%2Binss%2Bism%2B2025_.xlsx?MOD=AJPERES"),
    ("2024 · cierre del sistema",
     WCM + "d5472386-388d-48c6-accd-ba8886d846b0/"
     "Publicaci%C3%B3n%2BIT%2Bcierre%2BSistema%2B2024_.xlsx?MOD=AJPERES"),
]

NAVEGADOR = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
}

PROVINCIAS_CLAVE = ("castell", "valencia", "alicante", "barcelona", "madrid")


def pide(url, intentos=3, limite=60_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(
                    peticion, timeout=180,
                    context=ssl.create_default_context()) as r:
                return (r.status, r.headers.get("Content-Type", "?"),
                        r.read(limite), "")
        except urllib.error.HTTPError as exc:
            return exc.code, "-", exc.read(400), ""
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(3 * numero)
    return 0, "-", b"", ultimo


def main() -> None:
    l = ["# Bajas laborales: ¿hay provincia dentro de las hojas?", "",
         "Es la única pregunta que queda. Si la hay, esta sección tendrá",
         "Castellón y será mejor que la encuesta del INE, que se queda en",
         "comunidad autónoma.", ""]

    for titulo, url in FICHEROS:
        l += [f"## {titulo}", "", f"`{url[:120]}…`", ""]
        estado, tipo, datos, fallo = pide(url)
        l.append(f"- {estado} ({tipo}), {len(datos):,} bytes"
                 + (f" · {fallo}" if fallo else ""))
        if estado != 200 or len(datos) < 2000:
            l.append("")
            continue
        if datos[:2] != b"PK" and datos[:8] != xls.FIRMA:
            l += [f"- no es una hoja de cálculo; empieza por {datos[:60]!r}", ""]
            continue

        try:
            libro = xlsx.Libro(datos) if datos[:2] == b"PK" else xls.Libro(datos)
        except Exception as exc:  # noqa: BLE001
            l += [f"- no se pudo abrir: {type(exc).__name__}: {exc}", ""]
            continue

        hojas = list(libro.hojas)
        l.append(f"- {len(hojas)} hojas:")
        for nombre in hojas:
            l.append(f"    · {nombre}")
        l.append("")

        # Qué hojas hablan de provincia, por su nombre.
        por_nombre = [h for h in hojas
                      if re.search(r"provinc", h, re.I)]
        l.append(f"- hojas cuyo **nombre** dice «provincia»: {por_nombre}")
        l.append("")

        # Y por su contenido, que es lo que manda: se miran todas hasta dar
        # con las que nombran provincias de verdad.
        encontradas = []
        for nombre in hojas:
            try:
                filas = list(libro.filas(nombre))
            except Exception:  # noqa: BLE001
                continue
            texto = " ".join(str(c) for f in filas[:400] for c in f[:12] if c)
            if any(p in texto.lower() for p in PROVINCIAS_CLAVE):
                encontradas.append((nombre, len(filas), filas))

        l.append(f"- hojas que **nombran provincias** en su contenido: "
                 f"{[n for n, _, _ in encontradas]}")
        l.append("")

        for nombre, cuantas, filas in encontradas[:3]:
            l += [f"### «{nombre}» · {cuantas} filas", ""]
            for fila in filas[:26]:
                celdas = [str(c)[:22] for c in fila[:10] if c not in (None, "")]
                if celdas:
                    l.append("    · " + " | ".join(celdas))
            # Y la fila de Castellón, que es la que importa aquí.
            for fila in filas:
                unido = " ".join(str(c) for c in fila[:4] if c)
                if re.search(r"castell", unido, re.I):
                    l.append("    → CASTELLÓN: " + " | ".join(
                        str(c)[:20] for c in fila[:12]))
                    break
            l.append("")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "bajas-v.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
