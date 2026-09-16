"""Pruebas del motor de bloques que no necesitan red.

La base de un índice es lo que más fácil se queda viejo: el INE rebasa el IPC
cada pocos años y una etiqueta escrita a mano sobrevive al cambio sin que nadie
lo note. Por eso se deduce, y por eso conviene fijarlo con pruebas.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import bloques_ine as bloques  # noqa: E402


def serie(valores_por_anyo):
    """Doce meses por año con el valor dado."""
    serie = {}
    for anyo, valor in valores_por_anyo.items():
        for mes in range(1, 13):
            serie[f"{anyo}M{mes:02d}"] = valor
    return serie


class BaseDelIndice(unittest.TestCase):
    def test_la_base_es_el_ano_que_vale_cien(self):
        self.assertEqual(
            bloques.base_del_indice(serie({"2023": 92.6, "2025": 100.0, "2026": 104.6})),
            "2025")

    def test_un_ano_que_ronda_cien_sin_serlo_no_es_la_base(self):
        """99,2 de media no es una base: es un año que pasó cerca."""
        self.assertIsNone(
            bloques.base_del_indice(serie({"2024": 99.2, "2025": 101.4})))

    def test_un_ano_con_pocos_meses_no_decide(self):
        valores = serie({"2023": 92.6, "2025": 103.0})
        valores.update({"2026M01": 100.0, "2026M02": 100.0})
        self.assertIsNone(bloques.base_del_indice(valores))

    def test_sin_datos_no_se_inventa_una_base(self):
        self.assertIsNone(bloques.base_del_indice({}))


if __name__ == "__main__":
    unittest.main()
