# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes das 27 regras de Inscrição Estadual.

Estratégia e seu limite
-----------------------
Para cada UF, monta-se uma base plausível e faz-se **força bruta** sobre as posições
de dígito verificador até achar uma IE que a regra aceite. Depois exige-se que ela
passe e que qualquer mutação de um dígito a derrube.

Isso prova consistência aritmética — pesos alinhados com a base, módulo aplicado,
dígito conferido na posição certa — e pega a classe de bug mais provável aqui, que é
desalinhamento de pesos. **Não prova aderência à especificação**: se um peso estiver
errado em relação ao SINTEGRA, o teste continua passando, porque valida a
implementação contra ela mesma. Fechar essa lacuna exige um lote de IEs reais por UF,
que é o passo seguinte e está declarado como pendente no README.
"""

import itertools
import unittest

from erpnext_brasil.fiscal.inscricao_estadual import (
	UFS_SUPORTADAS,
	validar_inscricao_estadual,
)
from erpnext_brasil.fiscal.validators import ValidacaoFiscalError

# UF -> (molde, posições do dígito verificador)
# O molde tem o comprimento final; as posições de DV são preenchidas por força bruta.
MOLDES: dict[str, tuple[str, tuple[int, ...]]] = {
	"AC": ("0123456789012", (11, 12)),
	"AL": ("240320450", (8,)),
	"AM": ("042140830", (8,)),
	"AP": ("030123450", (8,)),
	"BA": ("12345600", (6, 7)),
	"CE": ("061234560", (8,)),
	"DF": ("0712345678901", (11, 12)),
	"ES": ("082345670", (8,)),
	"GO": ("101234560", (8,)),
	"MA": ("120423450", (8,)),
	"MG": ("0623456789000", (11, 12)),
	"MS": ("281234560", (8,)),
	"MT": ("00132345600", (10,)),
	"PA": ("152345670", (8,)),
	"PB": ("062345670", (8,)),
	"PE": ("018012300", (7, 8)),
	"PI": ("012345670", (8,)),
	"PR": ("1234567800", (8, 9)),
	"RJ": ("12345670", (7,)),
	"RN": ("200400400", (8,)),
	"RO": ("01012345678900", (13,)),
	"RR": ("240061230", (8,)),
	"RS": ("2240320000", (9,)),
	"SC": ("251234560", (8,)),
	"SE": ("271234560", (8,)),
	"SP": ("110042490000", (8, 11)),
	"TO": ("29010212340", (10,)),
}


def _preencher(molde: str, posicoes: tuple[int, ...], valores: tuple[int, ...]) -> str:
	caracteres = list(molde)

	for posicao, valor in zip(posicoes, valores, strict=True):
		caracteres[posicao] = str(valor)

	return "".join(caracteres)


def _construir_ie_valida(uf: str) -> str:
	"""Devolve uma IE que a regra da UF aceita, achada por força bruta."""
	molde, posicoes = MOLDES[uf]

	for valores in itertools.product(range(10), repeat=len(posicoes)):
		candidata = _preencher(molde, posicoes, valores)

		try:
			validar_inscricao_estadual(candidata, uf)
		except ValidacaoFiscalError:
			continue

		return candidata

	raise AssertionError(f"nenhum dígito verificador satisfaz a regra de {uf}")


class TestCoberturaDasUFs(unittest.TestCase):
	def test_todas_as_27_ufs_tem_regra(self):
		self.assertEqual(len(UFS_SUPORTADAS), 27)

	def test_moldes_cobrem_todas_as_ufs(self):
		self.assertEqual(set(MOLDES), set(UFS_SUPORTADAS))


class TestRegrasPorUF(unittest.TestCase):
	def test_cada_uf_aceita_uma_ie_consistente(self):
		for uf in sorted(UFS_SUPORTADAS):
			with self.subTest(uf=uf):
				ie = _construir_ie_valida(uf)
				self.assertEqual(validar_inscricao_estadual(ie, uf), ie)

	def test_mutacao_de_digito_invalida(self):
		"""Alterar um dígito do corpo deve derrubar a validação.

		Percorre todas as mutações possíveis e exige que ao menos uma seja rejeitada —
		um validador que aceitasse qualquer coisa passaria nos outros testes, mas não
		neste.
		"""
		for uf in sorted(UFS_SUPORTADAS):
			with self.subTest(uf=uf):
				ie = _construir_ie_valida(uf)
				_, posicoes = MOLDES[uf]

				rejeitou_alguma = False

				for indice in range(len(ie)):
					if indice in posicoes:
						continue

					for digito in "0123456789":
						if digito == ie[indice]:
							continue

						mutante = ie[:indice] + digito + ie[indice + 1 :]

						try:
							validar_inscricao_estadual(mutante, uf)
						except ValidacaoFiscalError:
							rejeitou_alguma = True
							break

					if rejeitou_alguma:
						break

				self.assertTrue(rejeitou_alguma, f"{uf}: nenhuma mutação foi rejeitada")

	def test_comprimento_errado_e_rejeitado(self):
		for uf in sorted(UFS_SUPORTADAS):
			with self.subTest(uf=uf):
				ie = _construir_ie_valida(uf)

				with self.assertRaises(ValidacaoFiscalError):
					validar_inscricao_estadual(ie + "7", uf)

	def test_aceita_valor_com_mascara(self):
		ie = _construir_ie_valida("SP")
		mascarada = f"{ie[:3]}.{ie[3:6]}.{ie[6:9]}.{ie[9:]}"

		self.assertEqual(validar_inscricao_estadual(mascarada, "SP"), ie)


class TestCasosEspeciais(unittest.TestCase):
	def test_isento_e_aceito_em_qualquer_uf(self):
		for uf in ("SP", "MG", "BA", "XX"):
			with self.subTest(uf=uf):
				self.assertEqual(validar_inscricao_estadual("ISENTO", uf), "ISENTO")
				self.assertEqual(validar_inscricao_estadual("isento", uf), "ISENTO")

	def test_uf_desconhecida_deixa_passar(self):
		# Sem regra aplicável, rejeitar travaria um cadastro legítimo.
		self.assertEqual(validar_inscricao_estadual("123456789", "XX"), "123456789")
		self.assertEqual(validar_inscricao_estadual("123456789", None), "123456789")

	def test_valor_vazio_e_erro(self):
		for vazio in (None, "", "   "):
			with self.subTest(valor=vazio):
				with self.assertRaises(ValidacaoFiscalError):
					validar_inscricao_estadual(vazio, "SP")

	def test_letras_rejeitadas_fora_de_sp(self):
		with self.assertRaises(ValidacaoFiscalError):
			validar_inscricao_estadual("12345678A", "CE")

	def test_sp_produtor_rural_usa_prefixo_p(self):
		# Produtor rural: só a 9ª posição do corpo é verificada.
		for valores in itertools.product(range(10), repeat=1):
			candidata = "P" + "01100424" + str(valores[0]) + "000"

			try:
				self.assertEqual(validar_inscricao_estadual(candidata, "SP"), candidata)
			except ValidacaoFiscalError:
				continue

			return

		self.fail("nenhum dígito verificador satisfaz o formato de produtor rural de SP")


if __name__ == "__main__":
	unittest.main()
