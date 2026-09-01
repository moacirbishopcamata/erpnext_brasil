# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/mdfe_rodoviario.py` — modal rodoviário do MDF-e (veículo/motorista)."""

import unittest

from erpnext_brasil.fiscal.cte_rodoviario import RntrcInvalido
from erpnext_brasil.fiscal.mdfe_rodoviario import (
	CARROCERIA_FECHADA_BAU,
	RODADO_CAVALO_MECANICO,
	Condutor,
	MdfeRodoviarioInvalido,
	Veiculo,
	montar_condutor,
	montar_rodo,
	montar_veiculo_reboque,
	montar_veiculo_tracao,
)

_CPF_VALIDO = "11144477735"


def _condutor(**kwargs) -> Condutor:
	base = {"nome": "João da Silva", "cpf": _CPF_VALIDO}
	base.update(kwargs)
	return Condutor(**base)


def _veiculo_tracao(**kwargs) -> Veiculo:
	base = {
		"placa": "ABC1234",
		"tara": "8500",
		"tipo_rodado": RODADO_CAVALO_MECANICO,
		"condutores": [_condutor()],
	}
	base.update(kwargs)
	return Veiculo(**base)


class TestMontarCondutor(unittest.TestCase):
	def test_campos_basicos(self):
		grupo = montar_condutor(_condutor())

		self.assertEqual(grupo, {"xNome": "João da Silva", "CPF": _CPF_VALIDO})

	def test_cpf_invalido_levanta_erro(self):
		with self.assertRaises(MdfeRodoviarioInvalido):
			montar_condutor(_condutor(cpf="123"))


class TestMontarVeiculoTracao(unittest.TestCase):
	def test_campos_obrigatorios(self):
		grupo = montar_veiculo_tracao(_veiculo_tracao())

		self.assertEqual(grupo["placa"], "ABC1234")
		self.assertEqual(grupo["tara"], "8500")
		self.assertEqual(grupo["tpRod"], RODADO_CAVALO_MECANICO)
		self.assertEqual(len(grupo["condutor"]), 1)

	def test_placa_e_normalizada_para_maiusculo(self):
		grupo = montar_veiculo_tracao(_veiculo_tracao(placa="abc1234"))

		self.assertEqual(grupo["placa"], "ABC1234")

	def test_sem_placa_levanta_erro(self):
		with self.assertRaises(MdfeRodoviarioInvalido):
			montar_veiculo_tracao(_veiculo_tracao(placa=""))

	def test_sem_condutor_levanta_erro(self):
		"""veicTracao precisa de ao menos um condutor -- não tem minOccurs=0 no XSD."""
		with self.assertRaises(MdfeRodoviarioInvalido):
			montar_veiculo_tracao(_veiculo_tracao(condutores=[]))

	def test_tipo_rodado_invalido_levanta_erro(self):
		with self.assertRaises(MdfeRodoviarioInvalido):
			montar_veiculo_tracao(_veiculo_tracao(tipo_rodado="99"))

	def test_tara_com_zero_a_esquerda_levanta_erro(self):
		with self.assertRaises(MdfeRodoviarioInvalido):
			montar_veiculo_tracao(_veiculo_tracao(tara="0850"))

	def test_tara_zero_e_valida(self):
		grupo = montar_veiculo_tracao(_veiculo_tracao(tara="0"))

		self.assertEqual(grupo["tara"], "0")

	def test_tipo_carroceria_opcional(self):
		sem_carroceria = montar_veiculo_tracao(_veiculo_tracao())
		com_carroceria = montar_veiculo_tracao(_veiculo_tracao(tipo_carroceria=CARROCERIA_FECHADA_BAU))

		self.assertNotIn("tpCar", sem_carroceria)
		self.assertEqual(com_carroceria["tpCar"], CARROCERIA_FECHADA_BAU)

	def test_varios_condutores(self):
		grupo = montar_veiculo_tracao(
			_veiculo_tracao(condutores=[_condutor(nome="A"), _condutor(nome="B")])
		)

		self.assertEqual(len(grupo["condutor"]), 2)


class TestMontarVeiculoReboque(unittest.TestCase):
	def test_sem_tprod_nem_condutor(self):
		"""veicReboque não tem tpRod nem condutor no XSD — diferente de veicTracao."""
		reboque = Veiculo(placa="XYZ9876", tara="2000")

		grupo = montar_veiculo_reboque(reboque)

		self.assertNotIn("tpRod", grupo)
		self.assertNotIn("condutor", grupo)
		self.assertEqual(grupo["placa"], "XYZ9876")


class TestMontarRodo(unittest.TestCase):
	def test_sem_reboque(self):
		grupo = montar_rodo("12345678", _veiculo_tracao())

		self.assertEqual(grupo["infANTT"], {"RNTRC": "12345678"})
		self.assertIn("veicTracao", grupo)
		self.assertNotIn("veicReboque", grupo)

	def test_com_reboque(self):
		reboque = Veiculo(placa="XYZ9876", tara="2000")

		grupo = montar_rodo("12345678", _veiculo_tracao(), veiculos_reboque=[reboque])

		self.assertEqual(len(grupo["veicReboque"]), 1)
		self.assertEqual(grupo["veicReboque"][0]["placa"], "XYZ9876")

	def test_rntrc_isento_e_aceito(self):
		"""Mesmo RNTRC do CT-e, mesma pegadinha -- ISENTO é valor legítimo."""
		grupo = montar_rodo("isento", _veiculo_tracao())

		self.assertEqual(grupo["infANTT"]["RNTRC"], "ISENTO")

	def test_rntrc_invalido_propaga_a_mesma_excecao_do_cte(self):
		with self.assertRaises(RntrcInvalido):
			montar_rodo("abc", _veiculo_tracao())


if __name__ == "__main__":
	unittest.main()
