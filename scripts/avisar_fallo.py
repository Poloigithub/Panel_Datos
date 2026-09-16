"""Abre un aviso en el repositorio cuando la actualización falla.

Una tarea que corre sola de madrugada no sirve de nada si nadie se entera de
que ha dejado de funcionar. GitHub manda su propio correo cuando un workflow
programado falla, pero ese correo dice poco más que «ha fallado»: no dice qué
paso, ni desde cuándo, ni deja rastro que se pueda consultar después.

Esto abre una incidencia en el propio repositorio con el paso que ha fallado y
el enlace al registro. Si ya hay una abierta por lo mismo, comenta en ella en
vez de abrir otra: una tarea que lleva rota una semana debe ser una incidencia
con siete comentarios, no siete incidencias.

Al abrirse una incidencia, GitHub avisa por correo a quien sigue el
repositorio, que es su dueño por defecto. No hacen falta contraseñas ni
servidores de correo: basta el token que la propia Action ya tiene.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"
# Con esto se reconocen las incidencias abiertas por esta misma tarea.
MARCA = "[actualización]"


def peticion(metodo: str, ruta: str, cuerpo: dict | None = None):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("no hay GITHUB_TOKEN; la Action no puede avisar")
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(
        ruta if ruta.startswith("http") else API + ruta,
        data=datos, method=metodo,
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "Panel_Datos/1.0",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=60) as respuesta:
        return json.loads(respuesta.read().decode() or "{}")


def pasos_fallidos(repo: str, run_id: str) -> list[str]:
    """Qué paso ha fallado, que es lo que uno quiere saber de un vistazo."""
    try:
        jobs = peticion("GET", f"/repos/{repo}/actions/runs/{run_id}/jobs")
    except Exception as exc:  # noqa: BLE001
        print(f"no se han podido leer los pasos: {exc}")
        return []
    fallidos = []
    for job in jobs.get("jobs", []):
        for paso in job.get("steps", []):
            if paso.get("conclusion") in ("failure", "timed_out", "cancelled"):
                fallidos.append(f"{paso.get('name')} ({paso.get('conclusion')})")
    return fallidos


def compone(tarea: str, repo: str, run_id: str, servidor: str,
            pasos: list[str], fecha: str) -> tuple[str, str]:
    """El título y el cuerpo del aviso. Sin red, para poder probarlo."""
    titulo = f"{MARCA} «{tarea}» ha fallado"
    enlace = f"{servidor}/{repo}/actions/runs/{run_id}"
    lineas = [
        f"La tarea **{tarea}** no ha terminado bien el {fecha}.",
        "",
        "**Qué ha fallado**",
    ]
    if pasos:
        lineas += [f"- {paso}" for paso in pasos]
    else:
        lineas.append("- no se ha podido determinar el paso; está en el registro")
    lineas += [
        "",
        f"[Ver el registro completo]({enlace})",
        "",
        "**Qué significa**",
        "",
        "Los datos publicados siguen siendo los de la última actualización que sí",
        "funcionó: la tarea valida antes de publicar, así que un fallo deja el panel",
        "como estaba, no lo deja a medias. Lo que no habrá es dato nuevo hasta que",
        "esto se arregle.",
        "",
        "Las causas habituales, por orden de frecuencia: el organismo ha renombrado",
        "una serie y el descargador ha dejado de encontrarla; el INE está limitando",
        "el ritmo y la descarga no termina; o una cifra no ha pasado la validación",
        "-un valor fuera de rango, una identidad contable que no cuadra- y la tarea",
        "ha parado a propósito para no publicar algo mal.",
        "",
        "Esta incidencia se cierra sola cuando alguien la cierra: la tarea no la",
        "reabre ni la cierra por su cuenta. Si vuelve a fallar mañana, lo dirá aquí",
        "mismo en un comentario.",
    ]
    return titulo, "\n".join(lineas)


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    servidor = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    tarea = os.environ.get("TAREA") or os.environ.get("GITHUB_WORKFLOW", "la actualización")
    fecha = os.environ.get("FECHA", "")
    if not repo or not run_id:
        print("faltan datos del entorno de la Action; no se avisa")
        return 0

    titulo, cuerpo = compone(tarea, repo, run_id, servidor,
                             pasos_fallidos(repo, run_id), fecha)

    # ¿Hay ya una incidencia abierta por lo mismo? Se comenta en ella.
    consulta = urllib.parse.quote(f'repo:{repo} is:issue is:open in:title "{MARCA}"')
    try:
        encontradas = peticion("GET", f"/search/issues?q={consulta}")
        abiertas = [i for i in encontradas.get("items", []) if i.get("title") == titulo]
    except Exception as exc:  # noqa: BLE001
        print(f"no se ha podido buscar incidencias abiertas: {exc}")
        abiertas = []

    if abiertas:
        numero = abiertas[0]["number"]
        peticion("POST", f"/repos/{repo}/issues/{numero}/comments", {"body": cuerpo})
        print(f"comentado en la incidencia #{numero}")
        return 0

    creada = peticion("POST", f"/repos/{repo}/issues", {"title": titulo, "body": cuerpo})
    print(f"abierta la incidencia #{creada.get('number')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
