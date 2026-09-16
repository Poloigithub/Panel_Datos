"""Población de los municipios de Castellón, del INE.

Hace falta para que el mapa diga algo: un coroplético de paro en valores
absolutos sólo señala dónde vive más gente. Con la población se puede calcular
el paro por cada cien habitantes, que es lo comparable entre un pueblo de
doscientos vecinos y la capital.

El INE guarda los municipios en la variable 19. Se localizan los de la
provincia por su código -que en España coincide con el del INE- y se resuelve
la serie de población de cada uno con el mismo motor que el resto del panel.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ine_api  # noqa: E402
import ine_series as motor  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "data" / "municipios"

VAR_MUNICIPIOS = 19
PROVINCIA = "12"
# Operaciones donde buscar la población municipal, en orden de preferencia.
OPERACIONES = ["ECP", "DPOP", "CP"]


def municipios_de_la_provincia(operacion: str) -> list[dict]:
    """Los municipios de Castellón tal y como los nombra esta operación."""
    try:
        valores = ine_api.get("VALORES_VARIABLEOPERACION", f"{VAR_MUNICIPIOS}/{operacion}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {operacion}: no se han podido leer los municipios ({exc})")
        return []

    elegidos = []
    for valor in valores:
        codigo = str(valor.get("Codigo") or "").strip()
        if len(codigo) == 5 and codigo.startswith(PROVINCIA) and codigo.isdigit():
            elegidos.append({"id": valor.get("Id"), "codigo": codigo,
                             "nombre": (valor.get("Nombre") or "").strip()})
    print(f"  {operacion}: {len(elegidos)} municipios de la provincia "
          f"(de {len(valores)} en España)")
    return elegidos


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    print("Buscando los municipios de Castellón en el INE…")
    operacion, municipios = None, []
    for candidata in OPERACIONES:
        municipios = municipios_de_la_provincia(candidata)
        if len(municipios) > 100:
            operacion = candidata
            break

    if not operacion:
        print("Ninguna operación ofrece los municipios de la provincia.")
        return 1

    print(f"\nDescargando la población de {len(municipios)} municipios desde {operacion}…")
    series: dict[str, dict[str, float]] = {}
    nombres: dict[str, str] = {}
    sin_serie = []

    for i, municipio in enumerate(municipios, 1):
        indice = motor.indexa_por_segmentos(operacion, f"{VAR_MUNICIPIOS}:{municipio['id']}")
        etiqueta = f"{municipio['codigo']} {municipio['nombre']}"

        # En el padrón la magnitud se llama «Total habitantes», no «Población»,
        # y el nombre del municipio se parte en varios segmentos cuando lleva
        # artículo pospuesto («Pobla de Benifassà, la»). Esos trozos del nombre
        # se admiten como relleno junto a las muletillas de siempre.
        del_nombre = motor.segmentos(municipio["nombre"])
        extras = motor.EXTRAS_ADMITIDOS | del_nombre | {"personas", "habitantes"}
        intentos = [
            {"total habitantes", "total"},
            {"total habitantes", "ambos sexos"},
            {"total habitantes"},
            {"poblacion", "total"},
            {"poblacion"},
        ]
        valores = {}
        for obligatorio in intentos:
            valores, _ = motor.resuelve(indice, obligatorio, etiqueta,
                                        extras=extras, avisar=False)
            if valores:
                break

        if not valores:
            sin_serie.append(etiqueta)
            # Con los primeros basta para ver cómo se llaman de verdad.
            if len(sin_serie) <= 2:
                print(f"    {etiqueta}: {len(indice)} conjuntos de segmentos; ejemplos:")
                for segs in list(indice)[:6]:
                    print(f"      {sorted(segs)}")
            continue
        series[municipio["codigo"]] = valores
        nombres[municipio["codigo"]] = municipio["nombre"]
        if i % 25 == 0:
            print(f"  {i}/{len(municipios)}…")

    if not series:
        print("No se ha obtenido ninguna serie de población.")
        return 1

    periodos = sorted({p for valores in series.values() for p in valores},
                      key=motor.orden_periodo)
    contenido = {
        "ambito": {"id": "municipios-castellon", "nombre": "Municipios de Castellón",
                   "tipo": "Municipios"},
        "actualizado": ahora,
        "fuente": {"organismo": "Instituto Nacional de Estadística", "operacion": operacion},
        "periodos": periodos,
        "municipios": {
            codigo: {"nombre": nombres[codigo],
                     "poblacion": [series[codigo].get(p) for p in periodos]}
            for codigo in sorted(series)
        },
    }
    fichero = DESTINO / "poblacion-castellon.json"
    fichero.write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")

    print(f"\n{len(series)} municipios · {len(periodos)} periodos "
          f"({periodos[0]} … {periodos[-1]}) · {fichero.stat().st_size // 1024} KB")
    if sin_serie:
        print(f"Sin serie de población ({len(sin_serie)}): {', '.join(sin_serie[:8])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
