"""El comprobador de nombres: que cace lo que tiene que cazar y calle lo demás.

Nació de un fallo real. Al extraer el motor de bloques, dos funciones se
mudaron de módulo y en el sitio donde se llamaban se quedaron sin el módulo
delante. Python no se queja de eso hasta que pasa por la línea, y por esa línea
sólo se pasa al descargar la renta, así que la tarea diaria murió tres días
seguidos sin que ninguna prueba, ni la validación de datos, ni `py_compile` lo
vieran.

Lo importante de estas pruebas no es que el comprobador encuentre cosas, sino
que **no encuentre las que no son**: un comprobador que avisa en falso se
ignora, y entonces no sirve de nada.
"""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import revisar_nombres  # noqa: E402


def huerfanos_de(codigo: str) -> list[str]:
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "prueba.py"
        ruta.write_text(codigo, encoding="utf-8")
        return [nombre for _linea, nombre in revisar_nombres.huerfanos(ruta)]


class CazaLoQueDebe(unittest.TestCase):
    def test_el_fallo_que_lo_motivo(self) -> None:
        """Una función que se mudó de módulo y se quedó sin él delante."""
        self.assertEqual(huerfanos_de(
            "import bloques_ine as bloques\n"
            "def posproceso(ambito, series, origen):\n"
            "    return deflacta(series, descarga_deflactor(ambito), origen)\n"
        ), ["deflacta", "descarga_deflactor"])

    def test_una_errata_en_un_nombre(self) -> None:
        self.assertEqual(huerfanos_de(
            "TOPE = 3\n"
            "def mira(x):\n"
            "    return x > TOEP\n"
        ), ["TOEP"])

    def test_cada_nombre_se_avisa_una_vez(self) -> None:
        """Con su primera línea, para no llenar la pantalla del mismo."""
        self.assertEqual(huerfanos_de(
            "def a():\n    return perdido\n"
            "def b():\n    return perdido\n"
        ), ["perdido"])


class CallaCuandoDebe(unittest.TestCase):
    """Lo que de verdad decide si esto vale: que no grite en falso."""

    def test_lo_importado_existe(self) -> None:
        for codigo in ("import json\nprint(json.dumps({}))\n",
                       "from pathlib import Path\nprint(Path('.'))\n",
                       "import datetime as dt\nprint(dt.date.today())\n",
                       "from os import path as p\nprint(p.join('a'))\n"):
            self.assertEqual(huerfanos_de(codigo), [], codigo)

    def test_los_parametros_existen(self) -> None:
        self.assertEqual(huerfanos_de(
            "def f(a, b=2, *resto, c, **otros):\n"
            "    return a + b + c + len(resto) + len(otros)\n"
        ), [])

    def test_lo_que_ata_un_bucle_o_un_with_existe(self) -> None:
        self.assertEqual(huerfanos_de(
            "import json\n"
            "for numero, letra in []:\n    print(numero, letra)\n"
            "with open('x') as fichero:\n    print(fichero)\n"
            "try:\n    pass\n"
            "except ValueError as exc:\n    print(exc)\n"
        ), [])

    def test_las_comprensiones_y_el_morsa(self) -> None:
        self.assertEqual(huerfanos_de(
            "datos = [1, 2]\n"
            "print([x * 2 for x in datos])\n"
            "print({k: v for k, v in zip(datos, datos)})\n"
            "if (n := len(datos)) > 1:\n    print(n)\n"
        ), [])

    def test_las_funciones_de_python_no_son_huerfanas(self) -> None:
        self.assertEqual(huerfanos_de(
            "print(sorted(set(range(3))), isinstance(1, int), round(1.5))\n"
            "raise RuntimeError('x')\n"
        ), [])

    def test_el_desempaquetado_con_estrella(self) -> None:
        self.assertEqual(huerfanos_de(
            "primero, *resto = [1, 2, 3]\n"
            "print(primero, resto)\n"
        ), [])

    def test_las_clases_y_sus_metodos(self) -> None:
        self.assertEqual(huerfanos_de(
            "class Cosa:\n"
            "    def __init__(self):\n        self.x = 1\n"
            "    def dime(self):\n        return self.x\n"
            "print(Cosa().dime())\n"
        ), [])


class ElPanelEstaLimpio(unittest.TestCase):
    def test_ningun_script_usa_un_nombre_que_no_existe(self) -> None:
        """La prueba que evita que esto vuelva a pasar."""
        rutas = sorted((RAIZ / "scripts").glob("*.py")) + \
            sorted((RAIZ / "tests").glob("*.py"))
        problemas = revisar_nombres.revisa(rutas)
        self.assertEqual(problemas, {}, f"nombres sin definir: {problemas}")


if __name__ == "__main__":
    unittest.main()
