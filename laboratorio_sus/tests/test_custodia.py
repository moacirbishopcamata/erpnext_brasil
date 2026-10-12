# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

import dataclasses
import unittest

from laboratorio_sus.puro.custodia import GENESE, encadear, verificar


def _cadeia(n=4, tubo="0000000011"):
	cadeia = []

	for i in range(n):
		cadeia.append(
			encadear(
				cadeia,
				tubo=tubo,
				tipo=f"etapa{i}",
				usuario="ana",
				local="UBS 1",
				instante=f"2026-10-12T10:0{i}:00-03:00",
				dados={"i": i},
			)
		)

	return cadeia


class TestCustodia(unittest.TestCase):
	def test_cadeia_integra(self):
		self.assertEqual(verificar(_cadeia()), [])

	def test_primeiro_evento_aponta_para_a_genese(self):
		self.assertEqual(_cadeia(1)[0].hash_anterior, GENESE)

	def test_encadear_nao_altera_a_cadeia_recebida(self):
		cadeia = _cadeia(2)
		antes = list(cadeia)
		encadear(cadeia, tubo="0000000011", tipo="x", usuario="u", local="l", instante="t")
		self.assertEqual(cadeia, antes)

	def test_evento_alterado_e_detectado(self):
		cadeia = _cadeia()
		cadeia[1] = dataclasses.replace(cadeia[1], usuario="outro")
		quebras = verificar(cadeia)
		self.assertTrue(quebras)
		self.assertEqual(quebras[0].posicao, 1)

	def test_dados_aninhados_alterados_sao_detectados(self):
		cadeia = _cadeia()
		cadeia[2] = dataclasses.replace(cadeia[2], dados={"i": 99})
		self.assertTrue(verificar(cadeia))

	def test_evento_removido_e_detectado(self):
		cadeia = _cadeia()
		del cadeia[1]
		self.assertTrue(verificar(cadeia))

	def test_removido_o_primeiro_e_detectado(self):
		cadeia = _cadeia()
		self.assertTrue(verificar(cadeia[1:]))

	def test_reordenado_e_detectado(self):
		cadeia = _cadeia()
		cadeia[1], cadeia[2] = cadeia[2], cadeia[1]
		self.assertTrue(verificar(cadeia))

	def test_adulterar_e_recalcular_so_o_proprio_hash_ainda_quebra_o_seguinte(self):
		cadeia = _cadeia()
		forjado = encadear(
			cadeia[:1], tubo="0000000011", tipo="forjado", usuario="mallory", local="x", instante="t"
		)
		cadeia[1] = forjado
		self.assertTrue(verificar(cadeia), "o evento seguinte apontava para o hash original")

	def test_cadeia_de_outro_tubo_e_recusada_ao_encadear(self):
		with self.assertRaises(ValueError):
			encadear(_cadeia(1), tubo="outro", tipo="x", usuario="u", local="l", instante="t")

	def test_evento_de_outro_tubo_misturado_e_detectado(self):
		cadeia = _cadeia(2)
		intruso = encadear(cadeia[:1], tubo="0000000011", tipo="x", usuario="u", local="l", instante="t")
		cadeia[1] = dataclasses.replace(intruso, tubo="9999999999")
		self.assertTrue(verificar(cadeia))

	def test_acentos_e_ordem_das_chaves_nao_mudam_o_hash(self):
		a = encadear(
			[],
			tubo="1",
			tipo="coleta",
			usuario="José",
			local="São Paulo",
			instante="t",
			dados={"a": 1, "b": 2},
		)
		b = encadear(
			[],
			tubo="1",
			tipo="coleta",
			usuario="José",
			local="São Paulo",
			instante="t",
			dados={"b": 2, "a": 1},
		)
		self.assertEqual(a.hash, b.hash)


if __name__ == "__main__":
	unittest.main()
