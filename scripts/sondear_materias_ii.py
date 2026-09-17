"""Segundo sondeo de materias primas: atar los dos cabos que quedaron sueltos.

El primero dejó dos cosas claras y dos a medias:

- El **Pink Sheet del Banco Mundial** contesta y trae lo que hace falta: Brent,
  gas, carbón, oro, cobre, trigo... desde 1960, mes a mes. Pero la URL que se
  probó lleva dentro un identificador de versión (`-0050012025-`) y el fichero
  que sirve se queda en diciembre de 2025. Es decir: esa dirección está
  congelada. Hay que sacar la buena de la página del Banco Mundial, igual que
  con las huelgas se sacan las direcciones de la página del ministerio.
- Los **carburantes del ministerio** cortaron la conexión. Puede ser un cortafuegos
  que no quiere el agente por defecto, puede ser el host. Se reintenta con
  paciencia, con cabeceras de navegador y por las dos puertas conocidas.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

SALIDA = RAIZ / "sondeos"

NAVEGADOR = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9",
}

PAGINA_BANCO_MUNDIAL = "https://www.worldbank.org/en/research/commodity-markets"

CARBURANTES = [
    ("REST por provincia (Castellón)",
     "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
     "PreciosCarburantes/EstacionesTerrestres/FiltroProvincia/12"),
    ("REST · listado de provincias",
     "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
     "PreciosCarburantes/Listados/Provincias/"),
    ("Geoportal · misma API, otro host",
     "https://geoportalgasolineras.es/resources/files/preciosEESS_es.xls"),
]


def pide(url: str, intentos: int = 4, limite: int = 12_000_000):
    """Pedir con reintentos: un `connection reset` no siempre es un no."""
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(peticion, timeout=120) as respuesta:
                return (respuesta.status,
                        respuesta.headers.get("Content-Type", "?"),
                        respuesta.read(limite), numero)
        except urllib.error.HTTPError as exc:
            return exc.code, "-", exc.read(600), numero
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(2 ** numero)
    return 0, "-", ultimo.encode(), intentos


def enlaces_del_banco_mundial(html: str) -> list[str]:
    """Las direcciones a hojas de cálculo que la página publica hoy."""
    crudos = re.findall(r'href="([^"]+\.xlsx?)"', html, re.I)
    vistos, salida = set(), []
    for crudo in crudos:
        direccion = crudo if crudo.startswith("http") else \
            "https://www.worldbank.org" + crudo
        if direccion not in vistos:
            vistos.add(direccion)
            salida.append(direccion)
    return salida


def main() -> None:
    lineas = ["# Materias primas, segundo sondeo", ""]

    lineas.append("## Banco Mundial · qué dirección publica hoy la página")
    lineas.append("")
    estado, tipo, datos, intento = pide(PAGINA_BANCO_MUNDIAL)
    lineas.append(f"- `{PAGINA_BANCO_MUNDIAL}`")
    lineas.append(f"- {estado} ({tipo}), {len(datos)} bytes, intento {intento}")
    hojas = []
    if estado == 200:
        hojas = enlaces_del_banco_mundial(datos.decode("utf-8", "replace"))
        lineas.append(f"- hojas de cálculo enlazadas: {len(hojas)}")
        for direccion in hojas[:20]:
            lineas.append(f"    · {direccion}")
    else:
        lineas.append(f"    · {datos[:300]!r}")
    lineas.append("")

    mensual = [d for d in hojas if "Historical-Data-Monthly" in d]
    if mensual:
        lineas.append("### La mensual, descargada de esa dirección")
        lineas.append("")
        for direccion in mensual[:2]:
            estado, tipo, datos, intento = pide(direccion)
            lineas.append(f"- `{direccion}`")
            lineas.append(f"- {estado} ({tipo}), {len(datos)} bytes")
            if estado == 200 and datos[:2] == b"PK":
                import xlsx
                libro = xlsx.Libro(datos)
                lineas.append(f"    - hojas: {list(libro.hojas)}")
                filas = list(libro.filas("Monthly Prices"))
                lineas.append(f"    - «Monthly Prices», {len(filas)} filas")
                for fila in filas[:6]:
                    lineas.append("        · " + " | ".join(
                        str(c) for c in fila[:12] if c not in (None, "")))
                for fila in filas[-3:]:
                    lineas.append("        · última: " + " | ".join(
                        str(c) for c in fila[:8]))
                # ¿Cuántas columnas y cómo se llaman todas?
                if len(filas) > 5:
                    cabecera = filas[4]
                    lineas.append(f"    - {len(cabecera)} columnas; nombres:")
                    for trozo in range(0, len(cabecera), 8):
                        lineas.append("        · " + " | ".join(
                            str(c or "") for c in cabecera[trozo:trozo + 8]))
                    unidades = filas[5]
                    lineas.append("    - unidades:")
                    for trozo in range(0, len(unidades), 8):
                        lineas.append("        · " + " | ".join(
                            str(c or "") for c in unidades[trozo:trozo + 8]))
            lineas.append("")

    lineas.append("## Ministerio · carburantes, con reintentos")
    lineas.append("")
    for titulo, direccion in CARBURANTES:
        estado, tipo, datos, intento = pide(direccion)
        lineas.append(f"### {titulo}")
        lineas.append("")
        lineas.append(f"`{direccion}`")
        lineas.append("")
        lineas.append(f"- {estado} ({tipo}), {len(datos)} bytes, intento {intento}")
        if estado == 200 and datos[:1] in (b"{", b"["):
            try:
                cuerpo = json.loads(datos.decode("utf-8-sig", "replace"))
            except Exception as exc:  # noqa: BLE001
                lineas.append(f"    · no es JSON legible: {exc}")
            else:
                if isinstance(cuerpo, dict):
                    lineas.append(f"    - claves: {list(cuerpo)[:12]}")
                    lista = next((v for v in cuerpo.values()
                                  if isinstance(v, list)), [])
                else:
                    lista = cuerpo
                lineas.append(f"    - {len(lista)} elementos")
                if lista:
                    lineas.append("    - primero:")
                    for clave, valor in list(lista[0].items())[:30]:
                        lineas.append(f"        · {clave}: {valor!r}")
        elif estado == 200:
            lineas.append(f"    · empieza por {datos[:16]!r}")
        else:
            lineas.append(f"    · {datos[:300]!r}")
        lineas.append("")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "materias-ii.md").write_text("\n".join(lineas) + "\n",
                                           encoding="utf-8")
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
