"""Caza los nombres que no existen antes de que reviente la tarea de las seis.

Python no comprueba que un nombre exista hasta que pasa por esa línea. En un
panel de veintitantos scripts que se ejecutan una vez al día, eso significa que
una función a la que sólo se entra en cierta rama puede llevar rota una semana
sin que nadie lo sepa. Pasó: al extraer el motor de bloques, `deflacta` y
`descarga_deflactor` se mudaron a `bloques_ine.py`, pero en el sitio donde se
llamaban se quedaron sin el módulo delante. Ni `py_compile` ni las pruebas ni
la validación de datos lo vieron, porque ninguno ejecuta esa línea. La tarea
diaria murió tres días seguidos.

Esto lo habría cazado en un segundo. Recorre el árbol de cada script y avisa de
los nombres que se **leen** sin estar definidos en ninguna parte del fichero ni
ser de Python.

**Lo que caza y lo que no.** A propósito es un comprobador flojo: no distingue
ámbitos, así que si una función usa una variable local de otra, no se entera.
Eso deja pasar algún fallo, pero a cambio **no da ni un aviso falso**, y un
comprobador que grita en falso se acaba ignorando, que es peor que no tenerlo.
"""

from __future__ import annotations

import ast
import builtins
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Nombres que Python define solo dentro de un módulo o de una clase.
PROPIOS = {"__name__", "__file__", "__doc__", "__package__", "__spec__",
           "__loader__", "__builtins__", "__all__", "__class__",
           "__annotations__", "__debug__", "__dict__", "__module__",
           "__qualname__"}


def definidos(arbol: ast.AST) -> set[str]:
    """Todo nombre que el fichero ata en algún sitio, sin mirar ámbitos."""
    nombres: set[str] = set()

    def ata(destino) -> None:
        if isinstance(destino, ast.Name):
            nombres.add(destino.id)
        elif isinstance(destino, (ast.Tuple, ast.List)):
            for trozo in destino.elts:
                ata(trozo)
        elif isinstance(destino, ast.Starred):
            ata(destino.value)

    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nombres.add(nodo.name)
        elif isinstance(nodo, (ast.Import, ast.ImportFrom)):
            for alias in nodo.names:
                nombres.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(nodo, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            destinos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
            for destino in destinos:
                ata(destino)
        elif isinstance(nodo, (ast.For, ast.AsyncFor, ast.comprehension)):
            ata(nodo.target)
        elif isinstance(nodo, ast.withitem):
            if nodo.optional_vars is not None:
                ata(nodo.optional_vars)
        elif isinstance(nodo, ast.ExceptHandler):
            if nodo.name:
                nombres.add(nodo.name)
        elif isinstance(nodo, (ast.Global, ast.Nonlocal)):
            nombres.update(nodo.names)
        elif isinstance(nodo, ast.NamedExpr):
            ata(nodo.target)
        elif isinstance(nodo, ast.MatchAs) and nodo.name:
            nombres.add(nodo.name)
        elif isinstance(nodo, ast.arguments):
            for grupo in (nodo.posonlyargs, nodo.args, nodo.kwonlyargs):
                for argumento in grupo:
                    nombres.add(argumento.arg)
            for suelto in (nodo.vararg, nodo.kwarg):
                if suelto is not None:
                    nombres.add(suelto.arg)

    return nombres


def huerfanos(ruta: Path) -> list[tuple[int, str]]:
    """Los nombres que ese fichero lee sin que existan."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    conocidos = definidos(arbol) | set(dir(builtins)) | PROPIOS
    fallos = {}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Load):
            if nodo.id not in conocidos:
                fallos.setdefault(nodo.id, nodo.lineno)
    return sorted((linea, nombre) for nombre, linea in fallos.items())


def revisa(rutas) -> dict[str, list[tuple[int, str]]]:
    return {str(r.relative_to(RAIZ)): fallos
            for r in rutas if (fallos := huerfanos(r))}


def main() -> int:
    rutas = sorted((RAIZ / "scripts").glob("*.py")) + \
        sorted((RAIZ / "tests").glob("*.py"))
    problemas = revisa(rutas)
    if not problemas:
        print(f"{len(rutas)} ficheros revisados: ningún nombre sin definir.")
        return 0
    print(f"Nombres que se usan y no existen en {len(problemas)} ficheros:\n")
    for fichero, fallos in sorted(problemas.items()):
        for linea, nombre in fallos:
            print(f"  {fichero}:{linea}: «{nombre}» no está definido")
    return 1


if __name__ == "__main__":
    sys.exit(main())
