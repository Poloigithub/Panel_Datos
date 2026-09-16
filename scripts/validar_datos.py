"""Comprueba los datos publicados antes de que lleguen al repositorio.

Se ejecuta después de descargar y antes de commitear: si algo no cuadra, el
workflow se para y no se publica nada.

Busca cuatro cosas distintas:

- **Estructura**: que cada fichero diga lo que dice su índice.
- **Identidades contables**: donde dos series están ligadas por definición
  -activos = ocupados + parados-, tienen que cumplirse.
- **Rangos plausibles**: una esperanza de vida de tres años significa que la
  búsqueda acabó en otra serie. Ya pasó.
- **Cobertura**: ningún indicador puede perder periodos respecto a la última
  descarga. Esto es lo que delata que el INE ha renombrado una serie y el
  descargador ha dejado de encontrarla, que es el fallo silencioso peligroso.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data"
COBERTURA = DATOS / "cobertura.json"

# Rangos plausibles por indicador, comunes a todos los ámbitos. La clave es el
# nombre del indicador tal y como aparece en los ficheros de datos.
RANGOS = {
    # mercado laboral (miles de personas y porcentajes)
    "ocupados": (1, 50_000),
    "parados": (0, 20_000),
    "activos": (1, 60_000),
    "tasa_actividad": (20, 90),
    "tasa_paro": (0, 70),
    "tasa_empleo": (10, 90),
    # población
    "poblacion": (10_000, 100_000_000),
    "edad_media": (20, 60),
    "mayores_70": (0, 50),
    "espanoles": (0, 100),
    "crecimiento": (-100, 100),
    # demografía
    "mortalidad_infantil": (0, 100),
    "edad_maternidad": (20, 45),
    "saldo_migratorio": (-100, 100),
    "nacidos_por_defuncion": (0, 5_000),
    # renta
    "renta_persona": (1_000, 100_000),
    "renta_hogar": (1_000, 200_000),
    "renta_uc": (1_000, 150_000),
    "gini": (0, 100),
    "p80p20": (0, 50),
    "bajo_60": (0, 100),
    "tamano_hogar": (1, 10),
    "hogares_unipersonales": (0, 100),
    "renta_persona_real": (1_000, 200_000),
    "renta_hogar_real": (1_000, 400_000),
    "renta_uc_real": (1_000, 300_000),
    # precios
    "ipc_general": (50, 200),
    "ipc_variacion": (-30, 60),
    "ipc_alimentos": (-30, 60),
    "ipc_transporte": (-40, 60),
}

# Relaciones que se cumplen por definición, con la holgura del redondeo del
# INE: (nombre, función sobre las series, tolerancia absoluta).
IDENTIDADES = [
    ("activos = ocupados + parados",
     ("activos", "ocupados", "parados"),
     lambda a, o, p: abs(a - (o + p)),
     0.35),
    ("tasa de paro = parados / activos",
     ("tasa_paro", "parados", "activos"),
     lambda t, p, a: abs(t - (p / a * 100)) if a else 0.0,
     0.1),
    ("tasa de empleo = tasa de actividad × (1 − tasa de paro)",
     ("tasa_empleo", "tasa_actividad", "tasa_paro"),
     lambda te, ta, tp: abs(te - ta * (1 - tp / 100)),
     0.15),
]


class Informe:
    def __init__(self) -> None:
        self.errores: list[str] = []
        self.avisos: list[str] = []

    def error(self, mensaje: str) -> None:
        self.errores.append(mensaje)

    def aviso(self, mensaje: str) -> None:
        self.avisos.append(mensaje)


def bloques() -> list[Path]:
    """Carpetas de datos que tienen índice, en orden estable."""
    return sorted(d for d in DATOS.iterdir() if d.is_dir() and (d / "index.json").exists())


def carga(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


def revisa_estructura(bloque: Path, indice: dict, informe: Informe) -> dict:
    """Comprueba el índice y devuelve el contenido de cada ámbito."""
    contenidos = {}
    for ambito in indice.get("ambitos", []):
        ruta = bloque / ambito["fichero"]
        if not ruta.exists():
            informe.error(f"{bloque.name}: falta el fichero {ambito['fichero']}")
            continue
        contenido = carga(ruta)
        periodos = contenido.get("periodos") or []
        if not periodos:
            informe.error(f"{bloque.name}/{ambito['id']}: no tiene periodos")
            continue
        for sexo, magnitudes in contenido.get("series", {}).items():
            for clave, valores in magnitudes.items():
                if len(valores) != len(periodos):
                    informe.error(
                        f"{bloque.name}/{ambito['id']}/{sexo}/{clave}: "
                        f"{len(valores)} valores para {len(periodos)} periodos"
                    )
        contenidos[ambito["id"]] = contenido
    return contenidos


def revisa_rangos(bloque: str, ambito: str, contenido: dict, informe: Informe) -> None:
    for sexo, magnitudes in contenido.get("series", {}).items():
        for clave, valores in magnitudes.items():
            rango = RANGOS.get(clave)
            if not rango:
                continue
            minimo, maximo = rango
            fuera = [v for v in valores if v is not None and not (minimo <= v <= maximo)]
            if fuera:
                informe.error(
                    f"{bloque}/{ambito}/{sexo}/{clave}: {len(fuera)} valores fuera "
                    f"del rango {rango}, por ejemplo {fuera[:3]}"
                )


def revisa_identidades(bloque: str, ambito: str, contenido: dict, informe: Informe) -> None:
    periodos = contenido["periodos"]
    for sexo, magnitudes in contenido.get("series", {}).items():
        for nombre, claves, calcula, tolerancia in IDENTIDADES:
            if not all(c in magnitudes for c in claves):
                continue
            peor, cuando = 0.0, None
            for i in range(len(periodos)):
                partes = [magnitudes[c][i] for c in claves]
                if any(v is None for v in partes):
                    continue
                desvio = calcula(*partes)
                if desvio > peor:
                    peor, cuando = desvio, periodos[i]
            if peor > tolerancia:
                informe.error(
                    f"{bloque}/{ambito}/{sexo}: no se cumple «{nombre}» "
                    f"(desviación {peor:.3f} en {cuando}, tolerancia {tolerancia})"
                )


def revisa_continuidad(bloque: str, ambito: str, contenido: dict, informe: Informe) -> None:
    """Un salto enorme entre dos periodos seguidos suele ser un empalme malo."""
    periodos = contenido["periodos"]
    for sexo, magnitudes in contenido.get("series", {}).items():
        for clave, valores in magnitudes.items():
            for i in range(1, len(valores)):
                anterior, actual = valores[i - 1], valores[i]
                # Con valores pequeños, o que cruzan el cero, la variación
                # relativa se dispara sin que signifique nada: la inflación
                # pasando de 0,2 % a 1 % no es un salto sospechoso.
                if anterior is None or actual is None or abs(anterior) < 5:
                    continue
                cambio = abs(actual - anterior) / abs(anterior)
                if cambio > 3:
                    informe.aviso(
                        f"{bloque}/{ambito}/{sexo}/{clave}: salto de "
                        f"{anterior} a {actual} entre {periodos[i-1]} y {periodos[i]}"
                    )


def cobertura_actual(bloque: str, ambito: str, contenido: dict) -> dict[str, int]:
    """Cuántos periodos con dato tiene cada serie."""
    resultado = {}
    for sexo, magnitudes in contenido.get("series", {}).items():
        for clave, valores in magnitudes.items():
            con_dato = sum(1 for v in valores if v is not None)
            resultado[f"{bloque}/{ambito}/{sexo}/{clave}"] = con_dato
    return resultado


def revisa_cobertura(actual: dict[str, int], informe: Informe) -> None:
    """Compara con la descarga anterior: nada puede encoger.

    Es la comprobación que detecta que el INE ha renombrado una serie y el
    descargador ha dejado de encontrarla, porque eso no produce ningún error:
    simplemente el indicador deja de estar.
    """
    if not COBERTURA.exists():
        print("  (no hay cobertura anterior con la que comparar; se crea ahora)")
        return

    anterior = carga(COBERTURA).get("series", {})
    for clave, periodos_antes in anterior.items():
        periodos_ahora = actual.get(clave)
        if periodos_ahora is None:
            informe.error(f"desaparecida: {clave} tenía {periodos_antes} periodos y ya no está")
        elif periodos_ahora < periodos_antes:
            informe.error(
                f"encogida: {clave} pasa de {periodos_antes} a {periodos_ahora} periodos"
            )

    nuevas = sorted(set(actual) - set(anterior))
    for clave in nuevas:
        print(f"  nueva serie: {clave} ({actual[clave]} periodos)")


def main() -> int:
    if not DATOS.exists():
        print("No hay carpeta data/; nada que validar.")
        return 1

    informe = Informe()
    cobertura: dict[str, int] = {}

    for bloque in bloques():
        indice = carga(bloque / "index.json")
        print(f"\n== {bloque.name} ==")
        contenidos = revisa_estructura(bloque, indice, informe)
        for ambito_id, contenido in contenidos.items():
            revisa_rangos(bloque.name, ambito_id, contenido, informe)
            revisa_identidades(bloque.name, ambito_id, contenido, informe)
            revisa_continuidad(bloque.name, ambito_id, contenido, informe)
            cobertura.update(cobertura_actual(bloque.name, ambito_id, contenido))
        series = sum(1 for k in cobertura if k.startswith(bloque.name + "/"))
        print(f"  {len(contenidos)} ámbitos · {series} series")

    print("\n== cobertura ==")
    revisa_cobertura(cobertura, informe)

    if informe.avisos:
        print(f"\n{len(informe.avisos)} avisos (no bloquean la publicación):")
        for aviso in informe.avisos[:15]:
            print(f"  · {aviso}")
        if len(informe.avisos) > 15:
            print(f"  · … y {len(informe.avisos) - 15} más")

    if informe.errores:
        print(f"\n{len(informe.errores)} ERRORES; no se publica nada:")
        for error in informe.errores:
            print(f"  ✗ {error}")
        return 1

    COBERTURA.write_text(
        json.dumps({"series": dict(sorted(cobertura.items()))}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nTodo correcto: {len(cobertura)} series validadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
