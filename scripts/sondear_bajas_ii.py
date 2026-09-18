"""Bajas laborales, segundo sondeo: las dos puertas que probé mal.

El primero dejó una cosa clara y dos a medias.

**Clara**: el INE publica en la Encuesta Trimestral de Coste Laboral las «horas
no trabajadas por I.T.», y las publica para España y para la Comunitat
Valenciana. Para Castellón **no hay ninguna serie**: esa encuesta no baja a
provincia, igual que pasa con los salarios.

**A medias, por culpa mía**:

- El **anuario del ministerio** no falló: lo probé con el contexto TLS por
  defecto y devolvió `CERTIFICATE_VERIFY_FAILED`. Eso no es que no haya nada,
  es que `mites.gob.es` sirve sólo su certificado de hoja y omite el
  intermedio. Para eso existe `red_ministerio.py`, que este panel escribió hace
  tiempo y que aquí no usé. Se repite con él.

- La **Seguridad Social** contestó y su página de estadísticas tiene un título
  «Incapacidad Temporal», pero no enlaza ningún fichero de datos directamente:
  hay que entrar. Aquí se sigue ese enlace para ver qué hay detrás.

Y de paso se fijan los nombres exactos de las series de la ETCL, que es lo que
hace falta para escribir el descargador sin adivinar.
"""

from __future__ import annotations

import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import ine_series as motor  # noqa: E402
import red_ministerio  # noqa: E402

SALIDA = RAIZ / "sondeos"
ANUARIO = "https://www.mites.gob.es/ficheros/ministerio/estadisticas/anuarios"

NAVEGADOR = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9",
}

SS_ESTADISTICAS = ("https://www.seg-social.es/wps/portal/wss/internet/"
                   "EstadisticasPresupuestosEstudios/Estadisticas/EST45")

AMBITOS = [("España", "349:16473"), ("Comunitat Valenciana", "70:9006")]


def pide(url, intentos=3, limite=20_000_000):
    ultimo = ""
    for numero in range(1, intentos + 1):
        try:
            peticion = urllib.request.Request(url, headers=NAVEGADOR)
            with urllib.request.urlopen(
                    peticion, timeout=90,
                    context=ssl.create_default_context()) as r:
                return r.status, r.read(limite), ""
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(400), ""
        except Exception as exc:  # noqa: BLE001
            ultimo = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * numero)
    return 0, b"", ultimo


def puerta_anuario(l):
    """Ahora sí, con la cadena de certificados completada."""
    l += ["## 1. El anuario del ministerio, esta vez con el TLS arreglado", ""]
    for anyo in (2024, 2023):
        for nombre in ("index.htm", "indice.htm", ""):
            url = f"{ANUARIO}/{anyo}/{nombre}"
            try:
                estado, tipo, datos = red_ministerio.abre(url, intentos=2,
                                                          limite=6_000_000)
            except Exception as exc:  # noqa: BLE001
                l.append(f"- `{url}` → reventó: {type(exc).__name__}: {exc}")
                continue
            l.append(f"- `{url}` → {estado} ({tipo}), {len(datos)} bytes")
            # El ministerio contesta 200 con su portal cuando el fichero no
            # existe, así que no basta el código: hay que mirar lo que trae.
            if estado != 200 or len(datos) < 800:
                continue
            html = datos.decode("utf-8", "replace")
            carpetas = sorted(set(re.findall(
                r'href="\.?/?([A-Z][A-Za-z0-9_-]{1,10})/', html)))
            if carpetas:
                l.append(f"    · capítulos enlazados: {carpetas}")
            # Los títulos de los capítulos dicen de qué va cada uno.
            titulos = [re.sub(r"\s+", " ", t).strip()
                       for t in re.findall(r">([^<>]{8,90})<", html)]
            pistas = ("incapacidad", "prestacion", "seguridad social",
                      "temporal", "baja")
            suenan = sorted({t for t in titulos
                             if any(p in t.lower() for p in pistas)})
            l.append(f"    · títulos que suenan a esto ({len(suenan)}): {suenan[:12]}")
            l.append("")
            return
    l.append("")


def puerta_seguridad_social(l):
    """Entrar en la página de Incapacidad Temporal, no quedarse en la puerta."""
    l += ["## 2. La Seguridad Social, un nivel más adentro", ""]
    estado, datos, fallo = pide(SS_ESTADISTICAS, limite=6_000_000)
    l.append(f"- portada de estadísticas → {estado}"
             + (f" · {fallo}" if fallo else f" · {len(datos)} bytes"))
    if estado != 200:
        l.append("")
        return

    html = datos.decode("utf-8", "replace")
    # Enlaces con su texto, para poder seguir el que dice «Incapacidad Temporal».
    enlaces = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html,
                         re.I | re.S)
    candidatos = []
    for href, texto in enlaces:
        limpio = re.sub(r"<[^>]+>", " ", texto)
        limpio = re.sub(r"\s+", " ", limpio).strip()
        if re.search(r"incapacidad|temporal", limpio, re.I):
            candidatos.append((limpio, href))
    l.append(f"- enlaces que hablan de incapacidad temporal: {len(candidatos)}")
    for texto, href in candidatos[:6]:
        l.append(f"    · «{texto[:60]}» → {href[:120]}")
    l.append("")

    for texto, href in candidatos[:2]:
        destino = urllib.parse.urljoin(SS_ESTADISTICAS, href)
        estado, datos, fallo = pide(destino, intentos=2, limite=8_000_000)
        l.append(f"### Siguiendo «{texto[:50]}»")
        l.append("")
        l.append(f"`{destino[:120]}`")
        l.append(f"- {estado}" + (f" · {fallo}" if fallo else f" · {len(datos)} bytes"))
        if estado != 200:
            l.append("")
            continue
        dentro = datos.decode("utf-8", "replace")
        ficheros = re.findall(r'href="([^"]+\.(?:xlsx?|csv|pdf))"', dentro, re.I)
        l.append(f"- ficheros enlazados: {len(ficheros)}")
        for f in sorted(set(ficheros))[:14]:
            l.append(f"    · {f[:130]}")
        # ¿Se nombra la provincia en algún sitio?
        provincia = len(re.findall(r"provincia", dentro, re.I))
        l.append(f"- la palabra «provincia» aparece {provincia} veces")
        l.append("")


def puerta_etcl(l):
    """Los nombres exactos de las series de horas no trabajadas por IT."""
    l += ["## 3. ETCL: los nombres exactos que hacen falta", ""]
    for nombre_ambito, filtro in AMBITOS:
        l += [f"### {nombre_ambito}", ""]
        try:
            indice = motor.indexa_por_segmentos("ETCL", filtro)
        except Exception as exc:  # noqa: BLE001
            l += [f"- no se pudo indexar: {exc}", ""]
            continue
        todas = [s for grupo in indice.values() for s in grupo]
        # Sólo lo que mide incapacidad temporal, no todo el tiempo de trabajo.
        casan = [s for s in todas
                 if re.search(r"\bI\.?\s?T\.?\b|incapacidad",
                              s.get("Nombre", ""), re.I)]
        l.append(f"- {len(todas)} series en total, {len(casan)} de incapacidad temporal")
        for s in casan[:40]:
            l.append(f"    · {s.get('COD')} · {s.get('Nombre')}")
        if len(casan) > 40:
            l.append(f"    · … y {len(casan) - 40} más")
        l.append("")


def main():
    l = ["# Bajas laborales, segundo sondeo", "",
         "El primero dejó claro que la ETCL del INE tiene «horas no trabajadas",
         "por I.T.» para España y la Comunitat, y ninguna serie para Castellón.",
         "Lo que quedó mal probado fue el anuario del ministerio -lo pedí con el",
         "TLS por defecto y por eso falló- y la Seguridad Social, donde me quedé",
         "en la puerta.", ""]
    for puerta in (puerta_anuario, puerta_seguridad_social, puerta_etcl):
        try:
            puerta(l)
        except Exception as exc:  # noqa: BLE001
            l += [f"- **la puerta reventó**: {type(exc).__name__}: {exc}", ""]

    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "bajas-ii.md").write_text("\n".join(l) + "\n", encoding="utf-8")
    print("\n".join(l))


if __name__ == "__main__":
    main()
