"""El validador: que un rango de bloque gane al rango general.

Dos bloques pueden llamar igual a cosas distintas. El azúcar de la cesta de
la compra es un índice del IPC con base 100; el de materias primas son
dólares por kilo. Con un único diccionario de rangos por nombre, el rango de
uno declaraba inválido al otro, que es exactamente lo que pasó al publicar
las materias primas.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import validar_datos as validador  # noqa: E402


class RangosPorBloque(unittest.TestCase):
    def setUp(self) -> None:
        self.originales = dict(validador.RANGOS)
        validador.RANGOS.clear()
        validador.RANGOS.update({
            "azucar": (30, 400),            # el índice del IPC
            "materias/azucar": (0.01, 5),   # dólares por kilo
            "tasa_paro": (0, 70),           # sin bloque: vale para todos
        })

    def tearDown(self) -> None:
        validador.RANGOS.clear()
        validador.RANGOS.update(self.originales)

    def _revisa(self, bloque: str, clave: str, valores: list[float]):
        informe = validador.Informe()
        contenido = {"series": {"ambos": {clave: valores}}}
        validador.revisa_rangos(bloque, "espana", contenido, informe)
        return informe

    def test_el_rango_del_bloque_manda_sobre_el_general(self) -> None:
        """0,12 $/kg es azúcar correcto aunque el rango general pida 30-400."""
        informe = self._revisa("materias", "azucar", [0.12, 0.78, 0.41])
        self.assertEqual(informe.errores, [])

    def test_el_rango_general_sigue_valiendo_donde_no_hay_uno_de_bloque(self) -> None:
        informe = self._revisa("cesta", "azucar", [95.4, 101.2])
        self.assertEqual(informe.errores, [])

        informe = self._revisa("cesta", "azucar", [0.12])
        self.assertEqual(len(informe.errores), 1)
        self.assertIn("cesta/espana/ambos/azucar", informe.errores[0])

    def test_el_rango_del_bloque_tambien_puede_fallar(self) -> None:
        """No es un permiso para todo: fuera de su propio rango sigue siendo error."""
        informe = self._revisa("materias", "azucar", [0.4, 912.0])
        self.assertEqual(len(informe.errores), 1)
        self.assertIn("912.0", informe.errores[0])

    def test_un_indicador_sin_rango_declarado_no_se_revisa(self) -> None:
        informe = self._revisa("materias", "platino", [-5.0, 99999.0])
        self.assertEqual(informe.errores, [])

    def test_los_huecos_no_cuentan_como_valores_fuera_de_rango(self) -> None:
        """El panel no interpola: un None es un hueco, no un dato inválido."""
        informe = self._revisa("epa", "tasa_paro", [12.3, None, 14.1])
        self.assertEqual(informe.errores, [])


if __name__ == "__main__":
    unittest.main()
