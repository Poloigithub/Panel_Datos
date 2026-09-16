"""La cesta de la compra: cuánto ha subido cada cosa, producto a producto.

El panel ya tenía el grupo entero de alimentos, que sirve para decir «la comida
ha subido un tanto» y poco más. Esto baja al detalle: aceite de oliva, huevos,
leche, pan, carne, pescado, fruta, verdura y patatas, cada uno con su índice.

Lo que hay, según el sondeo (`sondeos/cesta.md`):

- **España**: 125 productos distintos, hasta el nivel de subclase.
- **Comunitat Valenciana**: 73, algo menos fino pero con lo importante.
- **Castellón**: sólo el grupo «alimentos y bebidas no alcohólicas». Por debajo
  de eso, el INE no publica IPC provincial. La página lo dice.

Se guarda el **índice**, no la variación, y por un motivo concreto: el IPC está
en base 2021 = 100, así que el propio número responde a la pregunta. Un 143 en
el aceite de oliva significa que cuesta un 43 % más que en 2021.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bloques_ine as bloques  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "config"

# Índices en otra base conviven con los vigentes y valen cualquier cosa; el
# rango los descarta y el corte en 2002 deja sólo el enlace de la base actual.
RANGO = (30, 400)

# Cada producto, tal y como el INE lo nombra. El orden es el de la página.
PRODUCTOS = [
    ("alimentos", "Alimentos y bebidas no alcohólicas",
     {"alimentos y bebidas no alcoholicas"}, True),
    ("aceite_oliva", "Aceite de oliva", {"aceite de oliva"}, False),
    ("leche", "Leche", {"leche"}, False),
    ("huevos", "Huevos", {"huevos"}, False),
    ("pan", "Pan", {"pan"}, False),
    ("cereales", "Cereales y derivados", {"cereales y derivados"}, False),
    ("carne_vacuno", "Carne de vacuno", {"carne de vacuno"}, False),
    ("carne_ave", "Carne de ave", {"carne de ave"}, False),
    ("carne_porcino", "Carne de porcino", {"carne de porcino"}, False),
    ("pescado", "Pescado fresco y congelado", {"pescado fresco y congelado"}, False),
    ("frutas", "Frutas frescas", {"frutas frescas o refrigeradas"}, False),
    ("hortalizas", "Legumbres y hortalizas frescas",
     {"legumbres y hortalizas frescas"}, False),
    ("patatas", "Patatas y sus preparados", {"patatas y sus preparados"}, False),
    ("cafe", "Café, cacao e infusiones", {"cafe", "cacao e infusiones"}, False),
    ("agua", "Agua mineral", {"agua mineral"}, False),
]

AVISO_PROVINCIA = ("El INE no publica el IPC de productos sueltos por "
                   "provincia: de Castellón sólo existe el grupo entero de "
                   "alimentos.")


def indicador(clave: str, titulo: str, segmentos: set[str], hay_provincia: bool) -> dict:
    ficha = {
        "titulo": titulo, "unidad": "índice", "decimales": 3,
        "unidad_texto": "índice, base 2021 = 100",
        "rango": RANGO, "operacion": "IPC",
        "busquedas": [segmentos | {"indice"}],
        "por_sexo": False,
    }
    if not hay_provincia:
        ficha["sin_ambitos"] = ("castellon",)
        ficha["nota"] = AVISO_PROVINCIA
    return ficha


BLOQUE = {
    "titulo": "La cesta de la compra",
    "operaciones": ["IPC"],
    # Antes de 2002 el índice vive en otra base y sus valores no son
    # comparables con los de hoy.
    "desde": 2002,
    "indicadores": {clave: indicador(clave, titulo, segmentos, provincia)
                    for clave, titulo, segmentos, provincia in PRODUCTOS},
}


def main() -> int:
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    CONFIG.mkdir(parents=True, exist_ok=True)
    print("\n=== La cesta de la compra ===")
    por_ambito, procedencias, faltantes = bloques.descarga_bloque("cesta", BLOQUE)
    bloques.escribe_bloque("cesta", BLOQUE, por_ambito, ahora, RAIZ)

    (CONFIG / "series-cesta.json").write_text(
        json.dumps(procedencias, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Lo interesante en una línea: qué ha subido más desde la base.
    base = por_ambito.get("espana", {}).get("ambos", {})
    subidas = []
    for clave, valores in base.items():
        if not valores:
            continue
        ultimo = max(valores, key=lambda p: (p[:4], p[5:]))
        subidas.append((valores[ultimo] - 100, clave, ultimo))
    for subida, clave, ultimo in sorted(subidas, reverse=True)[:6]:
        print(f"  {clave}: {subida:+.1f} % desde 2021 ({ultimo})")

    if faltantes:
        print(f"\nNo se ha encontrado serie para {len(faltantes)} combinaciones:")
        for f in faltantes:
            print(f"  - {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
