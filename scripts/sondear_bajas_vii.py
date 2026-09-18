"""Bajas laborales, séptimo sondeo: atar cada código a su magnitud.

El anterior encontró la leyenda, pero suelta: cinco frases al pie de la hoja
-duración media, incidencia, prevalencia, procesos en vigor, trabajadores
protegidos- y seis códigos en la tabla mensual (19, 20, 21, 22, 25 y 33), sin
decir cuál es cuál.

Se podría deducir por el tamaño de las cifras. No se hace: en este panel, un
indicador que no se puede identificar con certeza se queda fuera, y «parece que
el número grande son los trabajadores» no es identificar.

Así que se identifica con aritmética. La hoja «Estadística» da, por provincia y
con el nombre escrito, la duración media, la incidencia media mensual y el
número de procesos iniciados. La hoja «Datos mensuales» da, por provincia y
código, las cifras de cada mes. Agregando la segunda y comparándola con la
primera, cada código tiene que casar con una y sólo una magnitud. El que no
case, no entra.
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
import xlsx  # noqa: E402

SALIDA = RAIZ / "sondeos"
SISTEMA_2026 = ("https://www.seg-social.es/wps/wcm/connect/wss/"
                "5baca09c-341b-4922-8641-cb93bf1f47d8/"
                "Publicacion_IT_SISTEMA_2026_Junio.xlsx?MOD=AJPERES")

NAVEGADOR = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0 Safari/537.36"),
             "Accept": "*/*"}

# Provincias con las que contrastar: una grande, una mediana y la que importa.
CONTRASTE = ("CASTELLÓN", "ALBACETE", "ZARAGOZA")


def pide(url, intentos=3, limite=60_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            p = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(
                    p, timeout=240, context=ssl.create_default_context()) as r:
                return r.status, r.read(limite), ""
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(400), ""
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(3 * numero)
    return 0, b"", ultimo


def main() -> None:
    l = ["# Atar cada código de indicador a su magnitud", "",
         "Cinco frases de leyenda y seis códigos. En vez de deducirlo por el",
         "tamaño de las cifras, se identifica con aritmética: lo que la hoja",
         "anual dice con el nombre escrito tiene que salir de agregar la hoja",
         "mensual.", ""]

    estado, datos, fallo = pide(SISTEMA_2026)
    l.append(f"- descarga: {estado}" + (f" · {fallo}" if fallo else
                                        f" · {len(datos):,} bytes"))
    if estado != 200 or datos[:2] != b"PK":
        (SALIDA / "bajas-vii.md").write_text("\n".join(l) + "\n", encoding="utf-8")
        print("\n".join(l))
        return
    libro = xlsx.Libro(datos)

    # ---------------------------------------- la hoja anual, sin aplastar
    l += ["", "## «Estadística» con las celdas en su sitio", ""]
    est = list(libro.filas("Estadística"))
    l.append(f"- {len(est)} filas. Las 8 primeras, con el índice de cada celda:")
    for numero, fila in enumerate(est[:8]):
        l.append(f"    fila {numero}: " + " ;; ".join(
            f"[{i}]{str(c)[:46]}" for i, c in enumerate(fila) if c not in (None, "")))
    l.append("")
    l.append("- las 18 últimas, igual (es donde estaba la leyenda):")
    for numero, fila in enumerate(est[-18:], start=len(est) - 18):
        l.append(f"    fila {numero}: " + " ;; ".join(
            f"[{i}]{str(c)[:70]}" for i, c in enumerate(fila) if c not in (None, "")))
    l.append("")

    # La fila de cada provincia de contraste, con su nombre de columna.
    l += ["## Lo que dice la hoja anual de las provincias de contraste", ""]
    anuales: dict[str, list] = {}
    for fila in est:
        texto = " ".join(str(c) for c in fila[:3] if c)
        for provincia in CONTRASTE:
            if re.search(provincia, texto, re.I):
                anuales.setdefault(provincia, fila)
    for provincia, fila in anuales.items():
        l.append(f"- **{provincia}**: " + " | ".join(
            f"[{i}]{str(c)[:24]}" for i, c in enumerate(fila) if c not in (None, "")))
    l.append("")

    # ---------------------------------------- agregar la hoja mensual
    l += ["## Lo que sale de agregar la hoja mensual, código a código", ""]
    filas = list(libro.filas("Datos mensuales"))
    cabecera = [str(c or "").strip() for c in filas[0]]
    col = {nombre: i for i, nombre in enumerate(cabecera)}
    l.append(f"- columnas: {cabecera}")

    def celda(fila, nombre):
        i = col.get(nombre)
        return fila[i] if i is not None and i < len(fila) else None

    # Meses presentes, para saber sobre cuántos se agrega.
    meses = sorted({str(celda(f, "Mes")) for f in filas[1:] if celda(f, "Mes")})
    l.append(f"- meses en el fichero ({len(meses)}): {meses}")
    l.append("")

    for provincia in CONTRASTE:
        suma = collections.defaultdict(float)
        ultimo_mes = collections.defaultdict(dict)
        for fila in filas[1:]:
            nombre = str(celda(fila, "Provincia") or "")
            if not re.search(provincia, nombre, re.I):
                continue
            codigo = str(celda(fila, "Indicador") or "")
            cantidad = celda(fila, "Suma de Cantidad")
            if not codigo or not isinstance(cantidad, (int, float)):
                continue
            suma[codigo] += cantidad
            mes = str(celda(fila, "Mes") or "")
            ultimo_mes[codigo][mes] = ultimo_mes[codigo].get(mes, 0) + cantidad

        l.append(f"### {provincia}")
        l.append("")
        for codigo in sorted(suma, key=lambda c: int(c) if c.isdigit() else 0):
            porcentaje = ultimo_mes[codigo]
            ultimo = porcentaje.get(meses[-1]) if meses else None
            l.append(f"- código **{codigo}**: suma de todos los meses = "
                     f"{suma[codigo]:,.0f} · último mes ({meses[-1] if meses else '?'}) "
                     f"= {ultimo:,.0f}" if ultimo is not None else
                     f"- código **{codigo}**: suma = {suma[codigo]:,.0f}")
        l.append("")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "bajas-vii.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print(f"escrito sondeos/bajas-vii.md ({len(l)} líneas)")


if __name__ == "__main__":
    main()
