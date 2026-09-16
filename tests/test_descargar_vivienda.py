"""Pruebas de los dos cálculos propios del bloque de vivienda.

Ni la hipoteca media ni el esfuerzo vienen del INE: se derivan aquí, así que
son justo lo que puede salir mal sin que nadie lo note.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import descargar_vivienda as vivienda  # noqa: E402


class HipotecaMedia(unittest.TestCase):
    def test_importe_en_miles_de_euros(self):
        """Lo que publica el INE: 1.200.000 miles de € en 8.000 hipotecas."""
        media, unidad = vivienda.hipoteca_media(
            {"2026M01": 1_200_000.0}, {"2026M01": 8_000.0})
        self.assertEqual(media, {"2026M01": 150_000.0})
        self.assertEqual(unidad, "miles de euros")

    def test_importe_ya_en_euros(self):
        """Si algún día lo publicara en euros, la media no se dispararía."""
        media, unidad = vivienda.hipoteca_media(
            {"2026M01": 1_200_000_000.0}, {"2026M01": 8_000.0})
        self.assertEqual(media, {"2026M01": 150_000.0})
        self.assertEqual(unidad, "euros")

    def test_una_media_imposible_no_se_publica(self):
        """Diez euros por hipoteca no es un problema de escala: es otra serie."""
        media, motivo = vivienda.hipoteca_media(
            {"2026M01": 80.0}, {"2026M01": 8_000.0})
        self.assertIsNone(media)
        self.assertIn("plausible", motivo)

    def test_sin_periodos_comunes_no_hay_media(self):
        media, motivo = vivienda.hipoteca_media(
            {"2026M01": 1_200_000.0}, {"2025M01": 8_000.0})
        self.assertIsNone(media)
        self.assertIn("comunes", motivo)

    def test_la_escala_se_elige_por_la_mediana_no_por_un_mes(self):
        """Un mes raro no debe decidir en qué unidad viene toda la serie."""
        importes = {f"2026M{mes:02d}": 1_200_000.0 for mes in range(1, 13)}
        importes["2026M07"] = 1.0
        numeros = {p: 8_000.0 for p in importes}
        media, unidad = vivienda.hipoteca_media(importes, numeros)
        self.assertEqual(unidad, "miles de euros")
        self.assertEqual(media["2026M07"], 0.12)  # 1.000 € entre 8.000 hipotecas


class MediaAnual(unittest.TestCase):
    def test_un_ano_completo(self):
        valores = {f"2025M{mes:02d}": float(mes) for mes in range(1, 13)}
        self.assertEqual(vivienda.media_anual(valores), {"2025": 6.5})

    def test_un_ano_a_medias_no_cuenta(self):
        """Comparar dos meses de 2026 con los doce de 2025 sería engañoso."""
        valores = {"2026M01": 10.0, "2026M02": 20.0}
        self.assertEqual(vivienda.media_anual(valores), {})


if __name__ == "__main__":
    unittest.main()
