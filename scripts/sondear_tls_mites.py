"""Por qué no se puede hablar con el ministerio, y si tiene arreglo.

El sondeo anterior se estrelló contra un `CERTIFICATE_VERIFY_FAILED: unable to
get local issuer certificate` en `www.mites.gob.es`, mientras el INE y
datos.gob.es contestaban sin problema. Ese error casi nunca significa que el
certificado sea malo: significa que el servidor **no manda el certificado
intermedio**, así que quien se conecta no puede enlazar el del sitio con una
raíz de confianza. Los navegadores lo disimulan yendo a buscar el intermedio
por su cuenta; Python no.

Aquí se comprueba eso y sólo eso:

1. Se mira la cadena que el servidor manda de verdad, sin verificar nada
   -mirar no es fiarse: por esa conexión no se descarga ningún dato-.
2. Se busca en el certificado del sitio la dirección del intermedio, que va
   escrita dentro, en la extensión «Authority Information Access».
3. Se baja ese intermedio y se vuelve a pedir la página **verificando de
   verdad**, ahora con el eslabón que faltaba.

Si el punto 3 sale bien, el ministerio es alcanzable sin bajar la guardia: lo
único que se ha hecho es completar la cadena, que es exactamente lo que hace
un navegador.
"""

from __future__ import annotations

import re
import socket
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "sondeos"
CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

MAQUINA = "www.mites.gob.es"
PRUEBA = f"https://{MAQUINA}/estadisticas/eat/welcome.htm"

# Dentro del DER, la dirección del intermedio va como texto plano detrás del
# identificador de «Authority Information Access». Buscar la cadena a pelo es
# tosco, pero no hay que meter una dependencia para leer un campo.
DIRECCION = re.compile(rb"http://[A-Za-z0-9./_%:-]+\.(?:crt|cer|p7c|p7b)", re.I)


def cadena_que_manda(maquina: str) -> tuple[list[bytes], list[str]]:
    """El certificado del sitio, tal y como lo sirve. Mirar no es fiarse.

    Leer la cadena entera hace falta Python 3.13; con 3.12 sólo se puede coger
    el del sitio, que es de donde hay que sacar la dirección del intermedio,
    así que da igual. Por esta conexión no se descarga ningún dato.
    """
    pem = ssl.get_server_certificate((maquina, 443), timeout=30)
    notas = [f"- el servidor entrega {pem.count('BEGIN CERTIFICATE')} "
             f"certificado(s) al pedirlo suelto"]
    return [ssl.PEM_cert_to_DER_cert(pem)], notas


def describe(der: bytes) -> str:
    """El nombre común del sujeto y el del emisor, sacados a ojo del DER."""
    textos = re.findall(rb"[\x20-\x7e]{6,}", der)
    legibles = [t.decode("ascii") for t in textos]
    return " · ".join(legibles[:8])


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    lineas = ["# ¿Se puede hablar con el ministerio?", "",
              "El error era `unable to get local issuer certificate`, que casi",
              "siempre significa que el servidor no manda el certificado",
              "intermedio. Esto lo comprueba y busca el eslabón que falta.", ""]

    print("=== Cadena que manda el ministerio ===")
    try:
        certificados, notas = cadena_que_manda(MAQUINA)
    except Exception as exc:  # noqa: BLE001
        lineas.append(f"No se ha podido ni mirar: {type(exc).__name__}: {exc}")
        (SALIDA / "tls-mites.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
        print(lineas[-1])
        return 1

    lineas += notas
    for i, der in enumerate(certificados):
        lineas.append(f"    {i}. {describe(der)[:200]}")
        print(f"  {i}. {describe(der)[:160]}")

    hojas = certificados[0] if certificados else b""
    direcciones = [d.decode("ascii") for d in DIRECCION.findall(hojas)]
    lineas += ["", "## Direcciones escritas dentro del certificado", ""]
    for d in dict.fromkeys(direcciones):
        lineas.append(f"- `{d}`")
    print(f"  direcciones dentro del certificado: {direcciones}")

    # Intentarlo con cada una: la primera que complete la cadena vale.
    lineas += ["", "## Con el eslabón que faltaba", ""]
    for direccion in dict.fromkeys(direcciones):
        try:
            with urllib.request.urlopen(direccion, timeout=60) as respuesta:
                intermedio = respuesta.read(200_000)
        except Exception as exc:  # noqa: BLE001
            lineas.append(f"- `{direccion}` → no se ha podido bajar: "
                          f"{type(exc).__name__}: {exc}")
            continue

        pem = ssl.DER_cert_to_PEM_cert(intermedio) if intermedio[:1] == b"\x30" \
            else intermedio.decode("ascii", "replace")
        contexto = ssl.create_default_context()
        try:
            contexto.load_verify_locations(cadata=pem)
        except Exception as exc:  # noqa: BLE001
            lineas.append(f"- `{direccion}` → no es un certificado utilizable: "
                          f"{type(exc).__name__}: {exc}")
            continue

        try:
            peticion = urllib.request.Request(PRUEBA, headers=CABECERAS)
            with urllib.request.urlopen(peticion, timeout=60, context=contexto) as r:
                cuerpo = r.read(4000)
            lineas.append(f"- `{direccion}` → **sirve**: {r.status}, "
                          f"{len(cuerpo)} bytes con verificación completa")
            print(f"  SIRVE {direccion}: {r.status}")
        except Exception as exc:  # noqa: BLE001
            lineas.append(f"- `{direccion}` → sigue sin verificar: "
                          f"{type(exc).__name__}: {exc}")
            print(f"  no sirve {direccion}: {exc}")

    (SALIDA / "tls-mites.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"escrito sondeos/tls-mites.md ({len(lineas)} líneas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
