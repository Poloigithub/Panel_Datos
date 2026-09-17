"""Carburantes, segundo sondeo: el apretón de manos y el histórico europeo.

El primero dejó dos cosas:

- **La API del ministerio va y viene.** `FiltroProvincia/12` contestó a la
  primera en un sondeo y, en el siguiente, tanto ésa como el listado de
  provincias murieron con `connection reset` tras cuatro intentos. Eso no
  parece carga: parece el apretón de manos TLS. El script del repositorio de
  gasolinas que ya funciona lo resuelve relajando los cifrados **y** apagando
  la verificación del certificado. Lo segundo aquí no se hace nunca, así que se
  prueba sólo lo primero: bajar el nivel de seguridad de los cifrados
  aceptados, que es lo que necesitan los servidores viejos, manteniendo intacta
  la comprobación del certificado y del nombre del servidor.

- **La Comisión Europea sí publica histórico.** Su boletín petrolero semanal
  enlaza un fichero de «prices history» con nombre de esos que no se adivinan.
  Si dentro está España, esta sección empieza hace años en vez de hoy.
"""

from __future__ import annotations

import json
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

NAVEGADOR = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-ES,es;q=0.9",
}

BASE = ("https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/"
        "PreciosCarburantes/")

BOLETIN = "https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en"


def contexto_estricto() -> ssl.SSLContext:
    return ssl.create_default_context()


def contexto_cifrados_viejos() -> ssl.SSLContext:
    """Cifrados de nivel bajo, **verificación intacta**.

    `SECLEVEL=1` permite firmas y claves que OpenSSL 3 rechaza por defecto, que
    es lo que suelen servir las máquinas de la administración. No toca
    `verify_mode` ni `check_hostname`: si el certificado no vale, sigue sin
    valer.
    """
    ctx = ssl.create_default_context()
    ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True
    return ctx


def pide(url, ctx, intentos=3, limite=60_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=NAVEGADOR)
            inicio = time.time()
            with urllib.request.urlopen(peticion, timeout=240,
                                        context=ctx) as respuesta:
                datos = respuesta.read(limite)
            return (respuesta.status, len(datos), datos, numero,
                    time.time() - inicio, "")
        except urllib.error.HTTPError as exc:
            return exc.code, 0, exc.read(400), numero, 0.0, ""
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(3 * numero)
    return 0, 0, b"", intentos, 0.0, ultimo


def main() -> None:
    l = ["# Carburantes, segundo sondeo", ""]

    # ------------------------------------------- 1. el apretón de manos
    l += ["## ¿Es el TLS? Mismas direcciones, dos contextos", ""]
    pruebas = [
        ("provincias", BASE + "Listados/Provincias/"),
        ("Castellón", BASE + "EstacionesTerrestres/FiltroProvincia/12"),
        ("toda España", BASE + "EstacionesTerrestres/"),
    ]
    contextos = [("por defecto", contexto_estricto()),
                 ("cifrados viejos, verificación intacta", contexto_cifrados_viejos())]

    ganador = None
    for nombre_ctx, ctx in contextos:
        l += [f"### Contexto: {nombre_ctx}", ""]
        for nombre, url in pruebas:
            estado, tam, datos, intento, tardanza, fallo = pide(url, ctx)
            if estado == 200:
                l.append(f"- **{nombre}**: 200, {tam:,} bytes, "
                         f"intento {intento}, {tardanza:.1f} s")
                if nombre == "toda España" and ganador is None:
                    ganador = (nombre_ctx, datos)
            else:
                l.append(f"- **{nombre}**: {estado} · {fallo or datos[:120]!r}")
        l.append("")

    # --------------------------------- 2. campos de una estación cualquiera
    if ganador:
        nombre_ctx, datos = ganador
        l += [f"## Qué trae cada estación (con «{nombre_ctx}»)", ""]
        cuerpo = json.loads(datos.decode("utf-8-sig", "replace"))
        lista = cuerpo.get("ListaEESSPrecio", [])
        l += [f"- fecha declarada: {cuerpo.get('Fecha')!r}",
              f"- {len(lista):,} estaciones", "- campos de la primera:"]
        for clave, valor in lista[0].items():
            l.append(f"    · {clave}: {valor!r}")
        campos = [c for c in lista[0] if "provinc" in c.lower()]
        l += ["", f"- campos de provincia: {campos}"]
        for campo in campos:
            cuenta = {}
            for e in lista:
                cuenta[str(e.get(campo, ""))] = cuenta.get(str(e.get(campo, "")), 0) + 1
            l.append(f"    · {campo}: {len(cuenta)} valores distintos")
            muestra = {k: v for k, v in sorted(cuenta.items())[:4]}
            l.append(f"      primeros: {muestra}")
        for campo in ("Precio Gasolina 95 E5", "Precio Gasoleo A",
                      "Precio Gasolina 98 E5", "Precio Gasoleo Premium",
                      "Precio Gases licuados del petróleo"):
            con = sum(1 for e in lista if str(e.get(campo, "")).strip())
            l.append(f"    · publican «{campo}»: {con:,} de {len(lista):,}")
        l.append("")

    # ------------------------------------------- 3. el histórico europeo
    l += ["## El histórico del boletín petrolero europeo", ""]
    ctx = contexto_estricto()
    estado, tam, datos, intento, tardanza, fallo = pide(BOLETIN, ctx,
                                                        limite=4_000_000)
    enlaces = []
    if estado == 200:
        html = datos.decode("utf-8", "replace")
        for crudo in re.findall(r'href="([^"]+\.xlsx[^"]*)"', html, re.I):
            entero = crudo if crudo.startswith("http") else \
                "https://energy.ec.europa.eu" + crudo
            enlaces.append(entero.replace("&amp;", "&"))
    historico = [e for e in enlaces if "history" in e.lower()]
    l.append(f"- enlaces con «history»: {len(historico)}")
    for e in historico[:3]:
        l.append(f"    · {e}")
    l.append("")

    for direccion in historico[:1]:
        estado, tam, datos, intento, tardanza, fallo = pide(direccion, ctx,
                                                            limite=40_000_000)
        l += [f"- descarga: {estado}, {tam:,} bytes"]
        if estado == 200 and (datos[:2] == b"PK" or datos[:8] == xls.FIRMA):
            libro = xlsx.Libro(datos) if datos[:2] == b"PK" else xls.Libro(datos)
            hojas = list(libro.hojas)
            l.append(f"- {len(hojas)} hojas: {hojas[:15]}")
            for nombre_hoja in hojas[:3]:
                filas = list(libro.filas(nombre_hoja))
                l.append(f"- «{nombre_hoja}», {len(filas)} filas:")
                for fila in filas[:10]:
                    l.append("    · " + " | ".join(
                        str(c or "")[:28] for c in fila[:9]))
                # ¿Aparece España?
                espanyas = [i for i, f in enumerate(filas)
                            if any("spain" in str(c or "").lower() or
                                   "españa" in str(c or "").lower()
                                   for c in f[:4])]
                l.append(f"    filas que nombran a España: {len(espanyas)}"
                         f" (primeras {espanyas[:5]})")
                for i in espanyas[:4]:
                    l.append("      → " + " | ".join(
                        str(c or "")[:24] for c in filas[i][:9]))
        else:
            l.append(f"    · {fallo or datos[:200]!r}")
        l.append("")

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "carburantes-ii.md").write_text("\n".join(l) + "\n",
                                              encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
