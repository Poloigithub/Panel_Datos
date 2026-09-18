"""Bajas laborales, sexto sondeo: qué significa la columna «Indicador».

Todo lo demás está resuelto. La Seguridad Social publica, por ejercicio y en
hoja de cálculo, dos tablas:

- **«Estadística»**: comunidad, provincia, duración media de los procesos,
  incidencia media mensual y número de procesos iniciados. Anual y provincial,
  con los nombres escritos en claro.
- **«Datos mensuales»**: ejercicio, mes, organismo, régimen, contingencia,
  **sexo**, **provincia**, indicador y cantidad. Mensual, provincial y por sexo,
  que es justo lo que este panel publica siempre que existe.

Pero el indicador viene como un número -19, 20, 21, 22, 25- y sin él no se
puede publicar nada de esa segunda tabla: una cifra cuyo significado no se sabe
no es un dato, es un número.

Se busca la leyenda en tres sitios: los valores distintos que toma la columna
por si alguno viene escrito, las hojas del fichero grande de las mutuas por si
trae una hoja de notas, y el resto de la hoja «Estadística», que es una tabla
dinámica y suele llevar la explicación al pie.
"""

from __future__ import annotations

import collections
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

SISTEMA_2026 = (WCM + "5baca09c-341b-4922-8641-cb93bf1f47d8/"
                "Publicacion_IT_SISTEMA_2026_Junio.xlsx?MOD=AJPERES")
MUTUAS_2026 = (WCM + "1813c6e0-ceae-4730-b97f-a42238338b5b/"
               "Publicaci%C3%B3n%2BIT%2Bmcss%2B%2B2026.xlsx?MOD=AJPERES")

NAVEGADOR = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
}


def pide(url, intentos=3, limite=60_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(peticion, timeout=240,
                                        context=ssl.create_default_context()) as r:
                return r.status, r.read(limite), ""
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(400), ""
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(3 * numero)
    return 0, b"", ultimo


def main() -> None:
    l = ["# ¿Qué significa la columna «Indicador»?", "",
         "Sin la leyenda, la tabla mensual -que trae provincia y sexo- no se",
         "puede publicar: una cifra cuyo significado no se sabe no es un dato.", ""]

    # --------------------------------------------- el fichero del sistema
    estado, datos, fallo = pide(SISTEMA_2026)
    l.append(f"## El fichero del sistema, 2026 → {estado}"
             + (f" · {fallo}" if fallo else f" · {len(datos):,} bytes"))
    l.append("")
    if estado == 200 and datos[:2] == b"PK":
        libro = xlsx.Libro(datos)
        filas = list(libro.filas("Datos mensuales"))
        cabecera = [str(c or "").strip() for c in filas[0]]
        l.append(f"- cabecera: {cabecera}")
        try:
            donde = cabecera.index("Indicador")
        except ValueError:
            donde = 7
        cuenta = collections.Counter()
        ejemplo = {}
        for fila in filas[1:]:
            if donde >= len(fila):
                continue
            valor = fila[donde]
            if valor in (None, ""):
                continue
            cuenta[str(valor)] += 1
            ejemplo.setdefault(str(valor), fila)
        l.append(f"- la columna «Indicador» toma {len(cuenta)} valores distintos:")
        for valor, veces in sorted(cuenta.items(),
                                   key=lambda kv: -kv[1]):
            fila = ejemplo[valor]
            l.append(f"    · **{valor}** · {veces:,} filas · ejemplo: "
                     + " | ".join(str(c)[:20] for c in fila[:10]))
        l.append("")

        # La hoja «Estadística» entera: es una tabla dinámica y la leyenda
        # suele estar al pie, fuera de la tabla.
        est = list(libro.filas("Estadística"))
        l.append(f"- «Estadística», {len(est)} filas · las 3 primeras y las 25 últimas:")
        for fila in est[:3]:
            l.append("    · " + " | ".join(str(c)[:40] for c in fila[:8] if c))
        l.append("    …")
        for fila in est[-25:]:
            celdas = [str(c)[:60] for c in fila[:8] if c not in (None, "")]
            if celdas:
                l.append("    · " + " | ".join(celdas))
        l.append("")

        # Y cualquier celda larga de cualquier hoja: las notas viven ahí.
        l.append("- celdas de texto largo (posibles notas al pie):")
        for nombre in libro.hojas:
            for fila in libro.filas(nombre):
                for celda in fila:
                    texto = str(celda or "").strip()
                    if len(texto) > 45 and not texto.replace(".", "").isdigit():
                        l.append(f"    · [{nombre}] {texto[:190]}")
        l.append("")

    # --------------------------------------------- el fichero de las mutuas
    estado, datos, fallo = pide(MUTUAS_2026)
    l.append(f"## El fichero de las mutuas, 2026 → {estado}"
             + (f" · {fallo}" if fallo else f" · {len(datos):,} bytes"))
    l.append("")
    if estado == 200 and datos[:2] == b"PK":
        libro = xlsx.Libro(datos)
        hojas = list(libro.hojas)
        l.append(f"- {len(hojas)} hojas: {hojas}")
        for nombre in hojas:
            filas = list(libro.filas(nombre))
            l.append(f"- «{nombre}», {len(filas)} filas · primeras:")
            for fila in filas[:12]:
                celdas = [str(c)[:34] for c in fila[:9] if c not in (None, "")]
                if celdas:
                    l.append("    · " + " | ".join(celdas))
        l.append("")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "bajas-vi.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print(f"escrito sondeos/bajas-vi.md ({len(l)} líneas)")


if __name__ == "__main__":
    main()
