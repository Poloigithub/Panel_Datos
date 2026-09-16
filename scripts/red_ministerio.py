"""Cómo hablar con el Ministerio de Trabajo sin bajar la guardia.

`www.mites.gob.es` entrega **sólo su propio certificado** y se deja el
intermedio, así que quien se conecta no puede enlazarlo con una raíz de
confianza y Python se planta con `unable to get local issuer certificate`. El
certificado es legítimo -FNMT-RCM, «AC Componentes Informáticos», a nombre del
Ministerio de Trabajo y Economía Social-; lo que falta es un eslabón.

La salida no es desactivar la verificación, que es lo que se encuentra escrito
por ahí y que dejaría el panel comiéndose lo que le sirviera cualquiera. La
salida es hacer lo mismo que hace un navegador: el propio certificado lleva
escrita dentro la dirección de su emisor -la extensión «Authority Information
Access»-, se baja de ahí y se completa la cadena.

Bajar ese intermedio por HTTP no abre ningún agujero: no se confía en él por
haberlo bajado, sino que se verifica contra las raíces del sistema como
cualquier otro. Un intermedio manipulado no verificaría y la conexión se
caería, que es justo lo que tiene que pasar.
"""

from __future__ import annotations

import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

CABECERAS = {"User-Agent": "Panel_Datos/1.0 (+https://github.com/Poloigithub/Panel_Datos)"}

# Dentro del DER, la dirección del emisor va como texto plano. Leer el campo
# como Dios manda pediría una dependencia para descifrar ASN.1, y el panel no
# tiene ninguna; buscar la cadena a pelo basta y se comprueba lo que se baja.
DIRECCION = re.compile(rb"http://[A-Za-z0-9./_%:-]+\.(?:crt|cer|p7c|p7b)", re.I)

# Lo que se espera encontrar. Si el ministerio cambia de emisor, esto deja de
# encajar y el sondeo lo dirá en vez de aceptar cualquier cosa en silencio.
EMISOR_ESPERADO = "cert.fnmt.es"

_contextos: dict[str, ssl.SSLContext] = {}


def _intermedio(maquina: str) -> tuple[str, str]:
    """El certificado que falta, bajado de donde el propio sitio dice."""
    pem = ssl.get_server_certificate((maquina, 443), timeout=30)
    der = ssl.PEM_cert_to_DER_cert(pem)
    for bruto in DIRECCION.findall(der):
        direccion = bruto.decode("ascii")
        if EMISOR_ESPERADO not in direccion:
            continue
        with urllib.request.urlopen(direccion, timeout=60) as respuesta:
            datos = respuesta.read(200_000)
        # Viene en DER; si algún día viniera ya en PEM, se usa tal cual.
        if datos[:1] == b"\x30":
            return ssl.DER_cert_to_PEM_cert(datos), direccion
        return datos.decode("ascii"), direccion
    raise RuntimeError(
        f"{maquina} no dice de quién es emisor, o ha cambiado de emisor: "
        f"se esperaba una dirección de {EMISOR_ESPERADO}")


def contexto(maquina: str) -> ssl.SSLContext:
    """Verificación completa, con el eslabón que el servidor no manda."""
    if maquina not in _contextos:
        pem, direccion = _intermedio(maquina)
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cadata=pem)
        _contextos[maquina] = ctx
        print(f"      cadena completada con {direccion}")
    return _contextos[maquina]


def abre(url: str, intentos: int = 4, limite: int = 40_000_000) -> tuple[int, str, bytes]:
    """Pide una dirección del ministerio verificando el certificado."""
    maquina = urllib.parse.urlsplit(url).netloc
    espera = 2
    for intento in range(intentos):
        try:
            peticion = urllib.request.Request(url, headers=CABECERAS)
            with urllib.request.urlopen(peticion, timeout=180,
                                        context=contexto(maquina)) as respuesta:
                return (respuesta.status,
                        respuesta.headers.get("Content-Type", "?"),
                        respuesta.read(limite))
        except urllib.error.HTTPError as exc:
            return exc.code, "-", str(exc.reason).encode()
        except Exception as exc:  # noqa: BLE001
            if intento == intentos - 1:
                return 0, "-", f"{type(exc).__name__}: {exc}".encode()
            time.sleep(espera)
            espera *= 2
    return 0, "-", b"sin intentos"
