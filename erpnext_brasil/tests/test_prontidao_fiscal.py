# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `contabil/prontidao_fiscal.py` — o que falta para gerar a EFD."""

import unittest

from erpnext_brasil.contabil.prontidao_fiscal import (
	GRAVIDADE_ATENCAO,
	verificar_empresa,
	verificar_item,
)


def _empresa_completa(**overrides) -> dict:
	base = {
		"tax_id": "11.222.333/0001-81",
		"inscricao_estadual": "00000000",
		"br_efd_perfil": "A",
		"br_efd_atividade": "Industrial ou equiparado a industrial",
		"br_efd_versao_leiaute": "017",
		"codigo_municipio_ibge": "1100205",
		"state": "RO",
	}
	base.update(overrides)

	return base


def _item_completo(**overrides) -> dict:
	base = {
		"item_code": "PROD001",
		"stock_uom": "UN",
		"ncm": "84713019",
		"br_efd_tipo_item": "04 - Produto Acabado",
	}
	base.update(overrides)

	return base


class TestEmpresaCompleta(unittest.TestCase):
	def test_cadastro_completo_nao_tem_pendencia(self):
		self.assertEqual(verificar_empresa(_empresa_completa()), [])


class TestEmpresaIncompleta(unittest.TestCase):
	def _campos_pendentes(self, **overrides) -> set[str]:
		return {p.campo for p in verificar_empresa(_empresa_completa(**overrides))}

	def test_sem_cnpj(self):
		self.assertIn("CNPJ", self._campos_pendentes(tax_id=""))

	def test_sem_inscricao_estadual(self):
		self.assertIn("Inscrição Estadual", self._campos_pendentes(inscricao_estadual=""))

	def test_sem_perfil(self):
		self.assertIn("Perfil de Apresentação", self._campos_pendentes(br_efd_perfil=""))

	def test_perfil_invalido_tambem_e_pendencia(self):
		"""Preenchido com valor fora do domínio é tão bloqueante quanto vazio."""
		self.assertIn("Perfil de Apresentação", self._campos_pendentes(br_efd_perfil="D"))

	def test_sem_versao_do_leiaute(self):
		self.assertIn("Versão do Leiaute", self._campos_pendentes(br_efd_versao_leiaute=""))

	def test_sem_codigo_de_municipio(self):
		self.assertIn("Código do Município (IBGE)", self._campos_pendentes(codigo_municipio_ibge=""))

	def test_codigo_de_municipio_com_tamanho_errado(self):
		self.assertIn("Código do Município (IBGE)", self._campos_pendentes(codigo_municipio_ibge="110020"))

	def test_sem_uf(self):
		self.assertIn("UF", self._campos_pendentes(state=""))

	def test_cadastro_vazio_lista_tudo_de_uma_vez(self):
		"""O ponto da verificação: não descobrir um problema por rodada."""
		pendencias = verificar_empresa({})

		self.assertGreaterEqual(len(pendencias), 7)
		self.assertTrue(all(p.bloqueia for p in pendencias))

	def test_a_pendencia_diz_onde_resolver(self):
		"""Quem lê o alerta precisa saber para onde ir na tela."""
		pendencia = verificar_empresa(_empresa_completa(br_efd_perfil=""))[0]

		self.assertIn("Empresa", pendencia.onde)
		self.assertIn("EFD", pendencia.onde)


class TestItem(unittest.TestCase):
	def _campos_pendentes(self, **overrides) -> set[str]:
		return {p.campo for p in verificar_item(_item_completo(**overrides))}

	def test_item_completo_nao_tem_pendencia(self):
		self.assertEqual(verificar_item(_item_completo()), [])

	def test_sem_tipo_de_item(self):
		self.assertIn("Tipo do Item (EFD)", self._campos_pendentes(br_efd_tipo_item=""))

	def test_tipo_de_item_fora_da_tabela(self):
		"""`50` não existe na tabela — diferente de `99`, que é "Outras" e é válido."""
		self.assertIn("Tipo do Item (EFD)", self._campos_pendentes(br_efd_tipo_item="50 - Inventado"))

	def test_o_codigo_99_outras_e_valido(self):
		self.assertEqual(verificar_item(_item_completo(br_efd_tipo_item="99 - Outras")), [])

	def test_aceita_o_tipo_no_formato_do_select(self):
		"""O Select guarda 'código - descrição'; a verificação lê só o código."""
		self.assertEqual(verificar_item(_item_completo(br_efd_tipo_item="00 - Mercadoria para Revenda")), [])

	def test_sem_unidade(self):
		self.assertIn("Unidade de Medida", self._campos_pendentes(stock_uom=""))

	def test_ncm_com_tamanho_errado_bloqueia(self):
		pendencia = next(p for p in verificar_item(_item_completo(ncm="123")) if p.campo == "NCM")

		self.assertTrue(pendencia.bloqueia)

	def test_ncm_ausente_e_atencao_nao_bloqueio(self):
		"""O layout exige NCM de indústria e equiparada, não de todo mundo — tratar
		como bloqueio recusaria cadastro que o Fisco aceita."""
		pendencia = next(p for p in verificar_item(_item_completo(ncm="")) if p.campo == "NCM")

		self.assertFalse(pendencia.bloqueia)
		self.assertEqual(pendencia.gravidade, GRAVIDADE_ATENCAO)

	def test_ncm_com_mascara_e_aceito(self):
		self.assertEqual(verificar_item(_item_completo(ncm="8471.30.19")), [])

	def test_a_pendencia_identifica_o_item(self):
		pendencia = verificar_item(_item_completo(item_code="XYZ", stock_uom=""))[0]

		self.assertIn("XYZ", pendencia.onde)


if __name__ == "__main__":
	unittest.main()
