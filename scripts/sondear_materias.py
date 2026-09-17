"""Brent y otras materias primas: qué fuente aguanta un panel.

La pregunta de partida era si esto se puede sacar de Yahoo Finance. Se puede
intentar, pero conviene decir antes lo que es: Yahoo **no tiene API pública**.
Lo que se usa es un endpoint interno de su web, sin documentar, sin compromiso
de estabilidad y con límites que cambian sin avisar. Un panel que se actualiza
solo todos los días y que presume de que cada cifra viene de una fuente oficial
no debería colgar de ahí sin haber mirado antes lo que sí es oficial.

Así que se prueban cuatro puertas a la vez:

1. **Yahoo Finance**, para saber si siquiera contesta desde aquí.
2. **El Pink Sheet del Banco Mundial**, que es la referencia mundial de precios
   de materias primas: mensual, con Brent, gas, carbón, oro, cobre, trigo y
   cuarenta más, desde 1960, en una hoja de cálculo. Oficial y documentado.
3. **Los carburantes del Ministerio para la Transición Ecológica**, que tiene
   API oficial y -esto es lo importante para este panel- **dato por provincia**:
   lo que cuesta llenar el depósito en Castellón.
4. **El Banco Central Europeo**, por si hiciera falta convertir dólares a euros,
   que es la mitad del trabajo de una sección de materias primas.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import xls  # noqa: E402
import xlsx  # noqa: E402

SALIDA = RAIZ / "sondeos"
CABECERAS = {
    "User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)",
    "Accept": "*/*",
}

PUERTAS = [
    ("Yahoo Finance · Brent por meses",
     "https://query1.finance.yahoo.com/v8/finance/chart/BZ=F"
     "?range=5y&interval=1mo"),
    ("Banco Mundial · Pink Sheet mensual",
     "https://thedocs.worldbank.org/en/doc/"
     "18675f1d1639c7a34d463f59263ba0a2-0050012025/related/"
     "CMO-Historical-Data-Monthly.xlsx"),
    ("Ministerio · carburantes de Castellón",
     "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
     "PreciosCarburantes/EstacionesTerrestres/FiltroProvincia/12"),
    ("BCE · dólar por euro",
     "https://data-api.ecb.europa.eu/service/data/EXR/M.USD.EUR.SP00.A"
     "?format=csvdata&startPeriod=2020-01"),
]


def pide(url: str, limite: int = 12_000_000) -> tuple[int, str, bytes]:
    try:
        peticion = urllib.request.Request(url, headers=CABECERAS)
        with urllib.request.urlopen(peticion, timeout=120) as respuesta:
            return (respuesta.status, respuesta.headers.get("Content-Type", "?"),
                    respuesta.read(limite))
    except urllib.error.HTTPError as exc:
        cuerpo = b""
        try:
            cuerpo = exc.read(600)
        except Exception:  # noqa: BLE001
            pass
        return exc.code, "-", cuerpo
    except Exception as exc:  # noqa: BLE001
        return 0, "-", f"{type(exc).__name__}: {exc}".encode()


def describe(lineas: list[str], tipo: str, datos: bytes) -> None:
    """Enseñar lo que ha llegado, sea del formato que sea."""
    if datos[:2] == b"PK" or datos[:8] == xls.FIRMA:
        libro = xlsx.Libro(datos) if datos[:2] == b"PK" else xls.Libro(datos)
        hojas = list(libro.hojas)
        lineas.append(f"    - hoja de cálculo con {len(hojas)} hojas: "
                      + ", ".join(f"«{h}»" for h in hojas[:12]))
        for hoja in hojas[:2]:
            filas = libro.filas(hoja)
            lineas.append(f"    - «{hoja}», {len(filas)} filas:")
            for fila in filas[:8]:
                celdas = [("" if c is None else str(c)) for c in fila[:12]]
                while celdas and celdas[-1] == "":
                    celdas.pop()
                if celdas:
                    lineas.append(f"        · {' | '.join(celdas)}")
            # Y la última fila, que dice hasta cuándo llega.
            if filas:
                ultima = [str(c) for c in filas[-1][:8] if c not in (None, "")]
                lineas.append(f"        · última fila: {' | '.join(ultima)}")
        return

    texto = datos.decode("utf-8", "replace")
    if "json" in tipo.lower() or texto.lstrip()[:1] in "[{":
        try:
            ficha = json.loads(texto)
        except json.JSONDecodeError:
            lineas.append(f"    - decía ser JSON y no lo es: {texto[:200]}")
            return
        if isinstance(ficha, list):
            lineas.append(f"    - lista de {len(ficha)} elementos")
            if ficha:
                lineas.append(f"        · claves del primero: {list(ficha[0])[:14]}")
                lineas.append(f"        · el primero: "
                              f"{json.dumps(ficha[0], ensure_ascii=False)[:400]}")
        else:
            lineas.append(f"    - claves: {list(ficha)[:10]}")
            lineas.append(f"        · {json.dumps(ficha, ensure_ascii=False)[:600]}")
        return

    lineas.append("    - texto:")
    for renglon in texto.splitlines()[:6]:
        lineas.append(f"        · {renglon[:200]}")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# Brent y materias primas: qué fuente aguanta un panel", "",
              "Yahoo no tiene API pública: lo que se usa es un endpoint interno",
              "de su web. Aquí se prueba junto a tres fuentes que sí son",
              "oficiales, para poder decidir con datos delante.", ""]

    for etiqueta, url in PUERTAS:
        estado, tipo, datos = pide(url)
        print(f"  {estado} · {etiqueta}")
        lineas += [f"## {etiqueta}", "", f"`{url}`", "",
                   f"- {estado} ({tipo.split(';')[0]}), {len(datos)} bytes"]
        if estado == 200 and datos:
            try:
                describe(lineas, tipo, datos)
            except Exception as exc:  # noqa: BLE001
                lineas.append(f"    - no se ha podido leer: "
                              f"{type(exc).__name__}: {exc}")
        else:
            lineas.append(f"    - {datos[:400].decode('utf-8', 'replace')}")
        lineas.append("")

    (SALIDA / "materias.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/materias.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
