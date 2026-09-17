"""La estadística mensual de autónomos, y dónde está la afiliación total.

Dos hallazgos del sondeo anterior:

- El ministerio publica **cada mes** una «Estadística de personas trabajadoras
  por cuenta propia afiliadas a la Seguridad Social», en XLSX y con el mismo
  patrón de nombre que la de accidentes: `AUT/AUT_MM_AAAA.xlsx`. Si alguna de
  sus 34 hojas baja a provincia, los autónomos pasan de una serie anual
  cortada en 2023 a una mensual con dos meses de retraso.
- La afiliación **total** mensual no la publica el ministerio: su propia página
  remite a la Seguridad Social. Hay que ver si ese sitio se deja leer.

Esto mira el índice del fichero de autónomos -que es como se ha aprendido a
navegar estos libros- y llama a la puerta de la Seguridad Social.
"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import red_ministerio as red  # noqa: E402
from xlsx import Libro  # noqa: E402

SALIDA = RAIZ / "sondeos"
AUT = "https://www.mites.gob.es/estadisticas/AUT/AUT_07_2026.xlsx"

CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

# La Seguridad Social tiene su propio sitio y su propio portal de datos; se
# prueban las dos puertas que su ministerio enlaza.
SEGURIDAD_SOCIAL = [
    "https://www.seg-social.es/wps/portal/wss/internet/EstadisticasPresupuestos"
    "Estudios/Estadisticas/EST8",
    "https://www.seg-social.es/",
    "https://datos.gob.es/es/catalogo?q=afiliaci%C3%B3n+seguridad+social",
]


def normaliza(texto: str) -> str:
    plano = (texto or "").strip().lower()
    for viejo, nuevo in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"),
                         ("ú", "u"), ("ñ", "n")):
        plano = plano.replace(viejo, nuevo)
    return " ".join(plano.split())


def puerta(url: str) -> str:
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=60) as respuesta:
            cuerpo = respuesta.read(2000)
            return f"{respuesta.status} ({respuesta.headers.get('Content-Type', '?').split(';')[0]}), {len(cuerpo)} bytes leídos"
    except urllib.error.HTTPError as exc:
        return f"{exc.code} {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Autónomos mes a mes, y la afiliación total", "",
              "Lo que decide si los autónomos pasan de una serie anual cortada",
              "en 2023 a una mensual: que alguna hoja baje a provincia.", ""]

    print("=== La estadística mensual de autónomos ===")
    estado, _, datos = red.abre(AUT)
    lineas += [f"## `{AUT}` → {estado}, {len(datos)} bytes", ""]
    if estado == 200 and datos[:2] == b"PK":
        libro = Libro(datos)
        hojas = list(libro.hojas)
        indice = next((h for h in hojas if normaliza(h).startswith("indice")), None)
        if indice:
            lineas += ["### Lo que dice su índice", "```"]
            for fila in libro.filas(indice):
                celdas = [str(c) for c in fila if c not in (None, "")]
                if celdas:
                    lineas.append(" | ".join(celdas))
            lineas += ["```", ""]

        # La hoja que nombre provincias, venga de donde venga.
        candidatas = []
        if indice:
            for fila in libro.filas(indice):
                texto = normaliza(" ".join(str(c) for c in fila if c not in (None, "")))
                if "provincia" in texto:
                    codigo = normaliza(str(fila[0] or "")).rstrip(". ").replace(" ", "")
                    for nombre in hojas:
                        if normaliza(nombre).replace(" ", "") == codigo:
                            candidatas.append((nombre, texto))
        print(f"    {len(candidatas)} hojas con provincia")
        for nombre, que in candidatas[:3]:
            lineas += [f"### Hoja «{nombre}»", f"*{que[:160]}*", "```"]
            for i, fila in enumerate(libro.filas(nombre)[:45]):
                celdas = [("" if c is None else str(c)) for c in fila[:10]]
                while celdas and celdas[-1] == "":
                    celdas.pop()
                if celdas:
                    lineas.append(f"{i:>3} | " + " | ".join(celdas))
            lineas += ["```", ""]
        if not candidatas:
            lineas.append("*Ninguna hoja baja a provincia.*")
            lineas.append("")

    print("=== La Seguridad Social ===")
    lineas += ["## ¿Se deja leer la Seguridad Social?", ""]
    for url in SEGURIDAD_SOCIAL:
        resultado = puerta(url)
        print(f"    {resultado} · {url[:70]}")
        lineas.append(f"- `{url}` → {resultado}")
    lineas.append("")

    (SALIDA / "aut-mensual.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/aut-mensual.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
