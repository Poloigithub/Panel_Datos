"""Pruebas del aviso de fallo.

Lo que se prueba es el mensaje, que es lo que va a leer alguien a las ocho de
la mañana cuando le llegue el correo: tiene que decir qué falló, dónde mirar y
si el panel se ha quedado a medias.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import avisar_fallo  # noqa: E402


class Mensaje(unittest.TestCase):
    def compone(self, pasos):
        return avisar_fallo.compone(
            "Actualizar datos", "Poloigithub/Panel_Datos", "42",
            "https://github.com", pasos, "17/09/2026 a las 05:40 UTC")

    def test_el_titulo_permite_reconocer_avisos_repetidos(self):
        """Dos fallos seguidos deben poder juntarse en la misma incidencia."""
        primero, _ = self.compone(["Validar los datos descargados (failure)"])
        segundo, _ = self.compone(["Descargar series de la EPA (failure)"])
        self.assertEqual(primero, segundo)
        self.assertIn(avisar_fallo.MARCA, primero)

    def test_dice_qué_paso_ha_fallado(self):
        _, cuerpo = self.compone(["Validar los datos descargados (failure)"])
        self.assertIn("Validar los datos descargados (failure)", cuerpo)

    def test_sin_pasos_no_se_inventa_ninguno(self):
        _, cuerpo = self.compone([])
        self.assertIn("no se ha podido determinar el paso", cuerpo)

    def test_lleva_el_enlace_al_registro(self):
        _, cuerpo = self.compone([])
        self.assertIn("https://github.com/Poloigithub/Panel_Datos/actions/runs/42", cuerpo)

    def test_tranquiliza_sobre_lo_publicado(self):
        """Un fallo no deja el panel a medias, y el aviso tiene que decirlo."""
        _, cuerpo = self.compone([])
        self.assertIn("siguen siendo los de la última actualización", cuerpo)


if __name__ == "__main__":
    unittest.main()
