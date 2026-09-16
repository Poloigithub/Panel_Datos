"""Renta por municipio de la provincia de Castellón, del Atlas del INE.

El Atlas de Distribución de Renta de los Hogares (ADRH) es la única fuente que
da renta por debajo de la provincia -llega incluso a sección censal-, y es lo
que permite que el mapa municipal diga algo más que dónde hay más paro.

Mismo camino que la población municipal: los municipios viven en la variable 19
del INE y se localizan por su código, que empieza por el de la provincia. La
serie de cada uno se resuelve con el motor de siempre, admitiendo como relleno
los trozos del propio nombre del municipio, que el INE parte por las comas
(«Pobla de Benifassà, la»).
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
OPERACION = "ADRH"

INDICADORES = {
    "renta_persona": {
        "titulo": "Renta neta media por persona",
        "busquedas": [{"renta neta media por persona"}],
        "rango": (1_000, 100_000),
    },
    "renta_hogar": {
        "titulo": "Renta neta media por hogar",
        "busquedas": [{"renta neta media por hogar"}],
        "rango": (1_000, 200_000),
    },
}


def municipios_de_la_provincia() -> list[dict]:
    """Los municipios de Castellón tal y como los nombra el Atlas."""
    valores = ine_api.get("VALORES_VARIABLEOPERACION", f"{VAR_MUNICIPIOS}/{OPERACION}")
    elegidos = []
    for valor in valores:
        codigo = str(valor.get("Codigo") or "").strip()
        if len(codigo) == 5 and codigo.startswith(PROVINCIA) and codigo.isdigit():
            elegidos.append({"id": valor.get("Id"), "codigo": codigo,
                             "nombre": (valor.get("Nombre") or "").strip()})
    print(f"{len(elegidos)} municipios de la provincia (de {len(valores)} en España)")
    return elegidos


def acepta_rango(rango):
    minimo, maximo = rango
    return lambda valores: all(minimo <= v <= maximo for v in valores.values())


def serie_del_municipio(indice, municipio, clave, indicador):
    """Busca la serie de un indicador en un municipio, con el nombre como relleno."""
    del_nombre = motor.segmentos(municipio["nombre"])
    extras = motor.EXTRAS_ADMITIDOS | del_nombre
    etiqueta = f"{municipio['codigo']} {municipio['nombre']}/{clave}"
    for busqueda in indicador["busquedas"]:
        valores, _ = motor.resuelve(indice, set(busqueda), etiqueta, extras=extras,
                                    avisar=False, acepta=acepta_rango(indicador["rango"]))
        if valores:
            return valores
    return {}


def comprueba_contra_la_provincia(series: dict, periodos: list[str]) -> None:
    """La renta municipal tiene que parecerse a la provincial que ya se publica.

    No son la misma cifra -la provincial no es la media de las municipales sin
    ponderar-, pero si el orden de magnitud no coincide es que la búsqueda ha
    acabado en otra serie.
    """
    ruta = RAIZ / "data" / "renta" / "castellon.json"
    if not ruta.exists():
        return
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    provincial = (contenido.get("series", {}).get("ambos", {}) or {}).get("renta_persona")
    if not provincial:
        return
    referencia = {p: v for p, v in zip(contenido["periodos"], provincial) if v is not None}
    for periodo in periodos[-1:]:
        municipales = [s["renta_persona"][periodo] for s in series.values()
                       if s.get("renta_persona", {}).get(periodo)]
        if not municipales or periodo not in referencia:
            continue
        media = sum(municipales) / len(municipales)
        print(f"\n{periodo}: media simple de los municipios {media:,.0f} € · "
              f"provincia {referencia[periodo]:,.0f} €")
        if not 0.6 <= media / referencia[periodo] <= 1.4:
            print("  ! la diferencia es demasiado grande; revisar qué serie se ha cogido")


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

    municipios = municipios_de_la_provincia()
    if len(municipios) < 100:
        print("El Atlas no ofrece los municipios de la provincia.")
        return 1

    series: dict[str, dict[str, dict[str, float]]] = {}
    nombres: dict[str, str] = {}
    sin_serie: list[str] = []

    for i, municipio in enumerate(municipios, 1):
        indice = motor.indexa_por_segmentos(OPERACION, f"{VAR_MUNICIPIOS}:{municipio['id']}")
        encontradas = {}
        for clave, indicador in INDICADORES.items():
            valores = serie_del_municipio(indice, municipio, clave, indicador)
            if valores:
                encontradas[clave] = valores

        if not encontradas:
            sin_serie.append(f"{municipio['codigo']} {municipio['nombre']}")
            # Con los primeros basta para ver cómo se llaman de verdad.
            if len(sin_serie) <= 2:
                print(f"  {municipio['nombre']}: {len(indice)} conjuntos de segmentos; ejemplos:")
                for segs in list(indice)[:6]:
                    print(f"    {sorted(segs)}")
            continue
        series[municipio["codigo"]] = encontradas
        nombres[municipio["codigo"]] = municipio["nombre"]
        if i % 25 == 0:
            print(f"  {i}/{len(municipios)}…")

    if not series:
        print("No se ha obtenido ninguna serie de renta municipal.")
        return 1

    periodos = sorted({p for indicadores in series.values()
                       for valores in indicadores.values() for p in valores},
                      key=motor.orden_periodo)
    contenido = {
        "ambito": {"id": "municipios-castellon", "nombre": "Municipios de Castellón",
                   "tipo": "Municipios"},
        "actualizado": ahora,
        "fuente": {"organismo": "Instituto Nacional de Estadística",
                   "operacion": OPERACION,
                   "nombre": "Atlas de Distribución de Renta de los Hogares"},
        "indicadores": {clave: {"titulo": ind["titulo"], "unidad": "euros", "decimales": 0}
                        for clave, ind in INDICADORES.items()},
        "periodos": periodos,
        "municipios": {
            codigo: dict({"nombre": nombres[codigo]},
                         **{clave: [series[codigo].get(clave, {}).get(p) for p in periodos]
                            for clave in INDICADORES})
            for codigo in sorted(series)
        },
    }
    fichero = DESTINO / "renta-castellon.json"
    fichero.write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")

    print(f"\n{len(series)} municipios · {len(periodos)} periodos "
          f"({periodos[0]} … {periodos[-1]}) · {fichero.stat().st_size // 1024} KB")
    if sin_serie:
        print(f"Sin renta ({len(sin_serie)}): {', '.join(sin_serie[:8])}")
    comprueba_contra_la_provincia(series, periodos)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
