"""La comprobación que cierra el asunto: provincia a provincia.

Ya se sabe que la duración media de España en 2025 son **42,3 días**, y que sale
de dividir los días de baja entre los procesos terminados agregando la tabla
mensual: sus procesos suman 9.590.619, exactamente los que la fuente publica
como terminados en España. Y que en contingencias comunes son 41,3 días en
hombres y 42,2 en mujeres, que es la cifra que se cita habitualmente.

Falta lo que preguntaba la duda: si Castellón, con 59,8 días, es un dato bueno o
un error de lectura. Se comprueba por el mismo camino, provincia a provincia:
lo que dice la tabla anual con el nombre escrito tiene que salir de agregar la
mensual por los dos códigos ya demostrados, el 20 -días- y el 19 -terminados-.

Si coinciden en las cincuenta y dos, no hay error: lo que hay es una dispersión
grande entre provincias, y eso es un hallazgo, no un fallo.
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
SISTEMA_2025 = ("https://www.seg-social.es/wps/wcm/connect/wss/"
                "58bb210f-343b-4591-a923-e11217cff5d1/"
                "Publicacion_IT_mcss%2Binss%2Bism%2B2025_.xlsx?MOD=AJPERES")

NAVEGADOR = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0 Safari/537.36"), "Accept": "*/*"}


def normaliza(texto) -> str:
    crudo = str(texto or "")
    tildes = str.maketrans("áéíóúÁÉÍÓÚ", "aeiouAEIOU")
    return re.sub(r"\s+", " ", crudo.translate(tildes)).strip().lower()


def pide(url, intentos=3, limite=60_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            p = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(
                    p, timeout=300, context=ssl.create_default_context()) as r:
                return r.status, r.read(limite), ""
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(400), ""
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(4 * numero)
    return 0, b"", ultimo


def main() -> None:
    l = ["# ¿Es buena la duración de Castellón? Provincia a provincia", ""]
    estado, datos, fallo = pide(SISTEMA_2025)
    l.append(f"- descarga: {estado} · {fallo or f'{len(datos):,} bytes'}")
    if estado != 200 or datos[:2] != b"PK":
        (SALIDA / "duracion-ii.md").write_text("\n".join(l) + "\n", encoding="utf-8")
        return
    libro = xlsx.Libro(datos)

    # Lo que dice la tabla anual, con el nombre escrito.
    anual: dict[str, tuple[float, float]] = {}
    filas = list(libro.filas("Estadística"))
    cabecera_n = next(n for n, f in enumerate(filas[:40])
                      if any("comunidad autonoma" in normaliza(c) for c in f))
    cab = filas[cabecera_n]
    c_prov = next(i for i, c in enumerate(cab) if normaliza(c) == "provincia")
    c_dur = next(i for i, c in enumerate(cab) if "duracion media" in normaliza(c))
    c_fin = next(i for i, c in enumerate(cab) if "numero de procesos finalizados" in normaliza(c))
    for fila in filas[cabecera_n + 1:]:
        if max(c_prov, c_dur, c_fin) >= len(fila):
            continue
        prov = normaliza(fila[c_prov])
        if prov and prov not in ("total", "total general") and \
                isinstance(fila[c_dur], (int, float)):
            anual[prov] = (float(fila[c_dur]),
                           float(fila[c_fin]) if isinstance(fila[c_fin], (int, float)) else 0)

    # Lo que sale de agregar la mensual por los códigos demostrados.
    mensual: dict[str, dict[str, float]] = collections.defaultdict(
        lambda: {"dias": 0.0, "fin": 0.0})
    filas_m = list(libro.filas("Datos mensuales"))
    cabm = [str(c or "").strip() for c in filas_m[0]]
    col = {n: i for i, n in enumerate(cabm)}
    for fila in filas_m[1:]:
        def celda(nombre):
            i = col.get(nombre)
            return fila[i] if i is not None and i < len(fila) else None
        codigo = str(celda("Indicador") or "")
        cantidad = celda("Suma de Cantidad")
        if codigo not in ("19", "20") or not isinstance(cantidad, (int, float)):
            continue
        prov = normaliza(celda("Provincia"))
        mensual[prov]["dias" if codigo == "20" else "fin"] += cantidad

    comunes = sorted(set(anual) & set(mensual))
    l.append(f"- provincias en las dos tablas: {len(comunes)}")
    l.append("")

    casan = fallan = 0
    peores = []
    for prov in comunes:
        publicada, _ = anual[prov]
        m = mensual[prov]
        if not m["fin"]:
            continue
        calculada = m["dias"] / m["fin"]
        diferencia = abs(calculada - publicada)
        if diferencia < 0.01:
            casan += 1
        else:
            fallan += 1
            peores.append((diferencia, prov, publicada, calculada))

    l.append(f"- **coinciden en {casan} provincias**, discrepan en {fallan}")
    for dif, prov, pub, calc in sorted(peores, reverse=True)[:5]:
        l.append(f"    · {prov}: publicada {pub:.2f} · calculada {calc:.2f} "
                 f"({dif:+.2f})")
    l.append("")

    # El reparto: dónde cae Castellón entre las cincuenta y dos.
    orden = sorted(((v[0], p) for p, v in anual.items()), reverse=True)
    l.append("- las diez provincias con la baja más larga:")
    for valor, prov in orden[:10]:
        l.append(f"    · {prov}: {valor:.1f} días")
    l.append("- las cinco con la más corta:")
    for valor, prov in orden[-5:]:
        l.append(f"    · {prov}: {valor:.1f} días")
    puesto = next((i for i, (_, p) in enumerate(orden, 1) if "castell" in p), None)
    if puesto:
        l.append(f"- **Castellón está en el puesto {puesto} de {len(orden)}** "
                 f"por duración")
    l.append("")

    # Y la media de España, ponderada como debe ser.
    total_dias = sum(m["dias"] for m in mensual.values())
    total_fin = sum(m["fin"] for m in mensual.values())
    if total_fin:
        l.append(f"- España, agregando todo: {total_dias:,.0f} días / "
                 f"{total_fin:,.0f} procesos = **{total_dias/total_fin:.2f} días**")
        simple = sum(v[0] for v in anual.values()) / len(anual)
        l.append(f"- promedio simple de las {len(anual)} provincias, sin "
                 f"ponderar: {simple:.2f} días")
        l.append("")
        l.append("  La diferencia entre las dos cifras es el aviso: las")
        l.append("  provincias pequeñas tienen bajas largas y las grandes,")
        l.append("  cortas. Promediar provincias sin ponderar da un número que")
        l.append("  no es el de nadie.")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "duracion-ii.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
