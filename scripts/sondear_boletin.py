"""El boletín petrolero europeo: ¿está España dentro?

El sondeo anterior bajó el fichero histórico -4,5 MB, siete hojas- pero al
asomarse a las nueve primeras columnas sólo se veían filas `EU_`, el agregado
de la Unión. La pinta es la de un fichero **ancho**: un bloque de columnas por
país, uno detrás de otro, y España estaría más a la derecha de donde se miró.

Si está, la sección de carburantes empieza hace veinte años en vez de hoy.
"""

from __future__ import annotations

import datetime as dt
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
FICHERO = ("https://energy.ec.europa.eu/document/download/"
           "906e60ca-8b6a-44e7-8589-652854d2fd3f_en"
           "?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx")

NAVEGADOR = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0 Safari/537.36"),
             "Accept": "*/*"}

# Excel cuenta los días desde el 30 de diciembre de 1899 y se salta el bulo del
# año bisiesto de 1900, que es por lo que la fecha base es esa y no el 1 de
# enero de 1900.
EPOCA = dt.date(1899, 12, 30)


def main() -> None:
    l = ["# El boletín petrolero europeo: ¿está España?", ""]
    peticion = urllib.request.Request(FICHERO, headers=NAVEGADOR)
    with urllib.request.urlopen(peticion, timeout=240,
                                context=ssl.create_default_context()) as r:
        datos = r.read(40_000_000)
    l.append(f"- {len(datos):,} bytes")

    libro = xlsx.Libro(datos)
    for hoja in ["Prices with taxes", "Prices wo taxes"]:
        if hoja not in libro.hojas:
            l.append(f"- no hay hoja «{hoja}»")
            continue
        filas = list(libro.filas(hoja))
        l += ["", f"## «{hoja}»", "", f"- {len(filas)} filas"]
        anchos = [len(f) for f in filas[:40]]
        l.append(f"- anchura de las primeras filas: {sorted(set(anchos))}")

        cabecera = filas[0]
        l.append(f"- {len(cabecera)} columnas en la primera fila")
        # Los nombres de columna llevan el país delante: EU_, AT_, ES_...
        paises = {}
        for i, celda in enumerate(cabecera):
            texto = str(celda or "")
            if "_" in texto:
                paises.setdefault(texto.split("_")[0], []).append(i)
        l.append(f"- prefijos encontrados ({len(paises)}): {sorted(paises)}")
        for clave in ("ES", "EU"):
            if clave in paises:
                l.append(f"    · {clave} ocupa las columnas {paises[clave]}")
                for i in paises[clave]:
                    l.append(f"        col {i}: {cabecera[i]!r} · "
                             f"{filas[1][i] if i < len(filas[1]) else ''!r} · "
                             f"unidad {filas[2][i] if i < len(filas[2]) else ''!r}")

        # La columna de códigos de país, por si el país va en filas y no en
        # columnas: en la muestra anterior la segunda columna decía «EU_».
        codigos = {}
        for fila in filas[3:]:
            if len(fila) > 1 and fila[1]:
                codigos[str(fila[1])] = codigos.get(str(fila[1]), 0) + 1
        if codigos:
            l.append(f"- códigos en la columna 1 ({len(codigos)}): "
                     f"{sorted(codigos)[:40]}")

        # Fechas: son seriales de Excel y van de más nueva a más vieja.
        seriales = [f[0] for f in filas[3:] if isinstance(f[0], (int, float))]
        if seriales:
            fechas = [EPOCA + dt.timedelta(days=int(s)) for s in seriales]
            l.append(f"- {len(seriales)} fechas, de {min(fechas)} a {max(fechas)}")

        # Y una muestra de una fila de datos entera, para verlo de verdad.
        for fila in filas[3:5]:
            l.append(f"- fila de ejemplo ({len(fila)} celdas):")
            for trozo in range(0, min(len(fila), 64), 8):
                l.append("    · " + " | ".join(
                    str(c or "")[:16] for c in fila[trozo:trozo + 8]))

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "boletin.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
