# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/cte_prestacao.py` — o corpo do CT-e e o orquestrador `montar_infcte`.

Teste-âncora: `test_ponta_a_ponta_monta_serializa_e_assina` — `montar_infcte` →
`montar_cte` → `para_xml` → `assinar_cte`, com a chave derivada do `ide` e o `cDV` do `ide`
saindo da **mesma** chave. É a costura entre este módulo e `fiscal/cte.py`, que nasceram
em incrementos diferentes.

Os achados do XSD que divergem da NF-e viram teste próprio: `rem`/`dest` opcionais, `emit`
com CPF, `vRec` distinto de `vTPrest`, `cUnid` fechado, `ICMS` só nas duas situações que a
apuração produz.
"""

import unittest
from datetime import datetime
from decimal import Decimal

from erpnext_brasil.fiscal.cte import (
	MODAL_RODOVIARIO,
	TIPO_SERVICO_NORMAL,
	TOMADOR_DESTINATARIO,
	CteInvalido,
	IdentificacaoCte,
	assinar_cte,
	montar_cte,
	montar_toma3,
)
from erpnext_brasil.fiscal.cte_prestacao import (
	UNIDADE_KG,
	EmitenteCte,
	ParteCte,
	QuantidadeCarga,
	montar_dest,
	montar_emit,
	montar_icms00,
	montar_icmssn,
	montar_imp,
	montar_infcarga,
	montar_infcte,
	montar_infcte_norm,
	montar_infmodal,
	montar_rem,
	montar_vprest,
)
from erpnext_brasil.fiscal.cte_rodoviario import montar_rodo
from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.documento.serializacao import para_xml

ENDERECO = {
	"xLgr": "Rua A",
	"nro": "10",
	"xBairro": "Centro",
	"cMun": "3550308",
	"xMun": "São Paulo",
	"CEP": "01001000",
	"UF": "SP",
}


def _identificacao(**kwargs) -> IdentificacaoCte:
	base = {
		"uf": "35",
		"cfop": "5352",
		"natureza_operacao": "Prestação de serviço de transporte",
		"serie": "1",
		"numero": "42",
		"codigo_numerico": "12345678",
		"emissao": datetime(2026, 8, 31, 12, 0, 0),
		"modal": MODAL_RODOVIARIO,
		"tipo_servico": TIPO_SERVICO_NORMAL,
		"municipio_inicio": "3550308",
		"municipio_inicio_nome": "São Paulo",
		"uf_inicio": "SP",
		"municipio_fim": "3304557",
		"municipio_fim_nome": "Rio de Janeiro",
		"uf_fim": "RJ",
		"municipio_envio": "3550308",
		"municipio_envio_nome": "São Paulo",
		"uf_envio": "SP",
		"indicador_ie_tomador": "1",
	}
	base.update(kwargs)
	return IdentificacaoCte(**base)


def _emitente(**kwargs) -> EmitenteCte:
	base = {
		"cnpj_cpf": "11.222.333/0001-81",
		"nome": "Transportadora Teste",
		"regime_tributario": "3",
		"endereco": ENDERECO,
		"inscricao_estadual": "123456789",
	}
	base.update(kwargs)
	return EmitenteCte(**base)


def _parte(**kwargs) -> ParteCte:
	base = {"nome": "Cliente Teste", "cnpj_cpf": "11.222.333/0001-81", "endereco": ENDERECO}
	base.update(kwargs)
	return ParteCte(**base)


def _infcte_norm() -> dict:
	return montar_infcte_norm(
		montar_infcarga("Peças", [QuantidadeCarga(UNIDADE_KG, "PESO BRUTO", Decimal("120.5"))]),
		montar_infmodal(MODAL_RODOVIARIO, montar_rodo("12345678")),
	)


def _montar(**kwargs):
	base = {
		"identificacao": _identificacao(),
		"tomador": montar_toma3(TOMADOR_DESTINATARIO),
		"emitente": _emitente(),
		"vprest": montar_vprest("150.00"),
		"imp": montar_imp(montar_icms00("150.00", "0.12")),
		"infcte_norm": _infcte_norm(),
		"remetente": _parte(),
		"destinatario": _parte(nome="Destinatário Teste"),
	}
	base.update(kwargs)
	return montar_infcte(**base)


class AssinadorFalso:
	def assinar(self, xml: bytes, id_elemento: str):
		from erpnext_brasil.fiscal.documento.assinatura import MaterialAssinatura

		return MaterialAssinatura(digest="ZGlnZXN0", assinatura="YXNzaW5hdHVyYQ==", certificado="Y2VydA==")


class TestEmit(unittest.TestCase):
	def test_ordem_e_campos_do_xsd(self):
		grupo = montar_emit(_emitente(nome_fantasia="TT"))
		self.assertEqual(list(grupo), ["CNPJ", "IE", "xNome", "xFant", "enderEmit", "CRT"])
		self.assertEqual(grupo["CNPJ"], "11222333000181")
		self.assertEqual(grupo["CRT"], "3")

	def test_aceita_cpf_do_transportador_autonomo(self):
		"""Diferente do emitente da NF-e — o XSD do CT-e tem `CNPJ|CPF` no `emit`."""
		grupo = montar_emit(_emitente(cnpj_cpf="529.982.247-25", inscricao_estadual=""))
		self.assertEqual(grupo["CPF"], "52998224725")
		self.assertNotIn("CNPJ", grupo)
		self.assertNotIn("IE", grupo)

	def test_sem_endereco_ou_crt_e_erro(self):
		with self.assertRaises(CteInvalido):
			montar_emit(_emitente(endereco={}))

		with self.assertRaises(CteInvalido):
			montar_emit(_emitente(regime_tributario=""))

	def test_cnpj_invalido_e_erro(self):
		with self.assertRaises(CteInvalido):
			montar_emit(_emitente(cnpj_cpf="11.222.333/0001-80"))


class TestRemDest(unittest.TestCase):
	def test_tag_de_endereco_muda_por_papel(self):
		self.assertIn("enderReme", montar_rem(_parte()))
		self.assertIn("enderDest", montar_dest(_parte()))

	def test_ordem_do_xsd(self):
		grupo = montar_dest(_parte(inscricao_estadual="123", email="a@b.c"))
		self.assertEqual(list(grupo), ["CNPJ", "IE", "xNome", "enderDest", "email"])

	def test_sem_endereco_e_erro(self):
		with self.assertRaises(CteInvalido):
			montar_rem(_parte(endereco={}))


class TestVPrest(unittest.TestCase):
	def test_vrec_cai_no_total_quando_nao_informado(self):
		self.assertEqual(montar_vprest("150.005"), {"vTPrest": "150.01", "vRec": "150.01"})

	def test_vrec_pode_ser_menor_que_o_total(self):
		grupo = montar_vprest("150", "100", {"FRETE": "150"})
		self.assertEqual(grupo["vRec"], "100.00")
		self.assertEqual(grupo["Comp"], [{"xNome": "FRETE", "vComp": "150.00"}])

	def test_total_nao_positivo_e_erro(self):
		for ruim in ("0", "-1"):
			with self.subTest(ruim=ruim), self.assertRaises(CteInvalido):
				montar_vprest(ruim)

	def test_vrec_fora_da_faixa_e_erro(self):
		with self.assertRaises(CteInvalido):
			montar_vprest("100", "101")


class TestImp(unittest.TestCase):
	def test_icms00_calcula_o_valor_e_converte_a_aliquota_em_percentual(self):
		grupo = montar_icms00("1000", "0.12")
		self.assertEqual(
			grupo, {"ICMS00": {"CST": "00", "vBC": "1000.00", "pICMS": "12.00", "vICMS": "120.00"}}
		)

	def test_aliquota_em_percentual_e_erro(self):
		"""`12` em vez de `0.12`: a classe de bug que o app elimina na entrada."""
		with self.assertRaises(CteInvalido):
			montar_icms00("1000", "12")

	def test_icmssn(self):
		self.assertEqual(montar_icmssn(), {"ICMSSN": {"CST": "90", "indSN": "1"}})

	def test_imp_so_aceita_as_duas_situacoes_modeladas(self):
		self.assertEqual(list(montar_imp(montar_icmssn())), ["ICMS"])

		with self.assertRaises(CteInvalido):
			montar_imp({"ICMS20": {}})

	def test_imp_com_icms_uf_fim(self):
		grupo = montar_imp(montar_icms00("1", "0.1"), {"vBCUFFim": "1.00"})
		self.assertEqual(list(grupo), ["ICMS", "ICMSUFFim"])


class TestInfCarga(unittest.TestCase):
	def test_ordem_e_formato(self):
		grupo = montar_infcarga(
			"Peças", [QuantidadeCarga(UNIDADE_KG, "PESO BRUTO", Decimal("120.5"))], "1000"
		)
		self.assertEqual(list(grupo), ["vCarga", "proPred", "infQ"])
		self.assertEqual(grupo["infQ"], [{"cUnid": "01", "tpMed": "PESO BRUTO", "qCarga": "120.5000"}])

	def test_vcarga_e_opcional(self):
		self.assertNotIn("vCarga", montar_infcarga("Peças", [QuantidadeCarga(UNIDADE_KG, "PESO", 1)]))

	def test_sem_quantidade_ou_unidade_fora_da_tabela_e_erro(self):
		with self.assertRaises(CteInvalido):
			montar_infcarga("Peças", [])

		with self.assertRaises(CteInvalido):
			montar_infcarga("Peças", [QuantidadeCarga("07", "PESO", 1)])

		with self.assertRaises(CteInvalido):
			montar_infcarga("Peças", [QuantidadeCarga(UNIDADE_KG, "PESO", 0)])


class TestInfModalEInfCteNorm(unittest.TestCase):
	def test_infmodal_leva_a_versao_e_o_modal(self):
		grupo = montar_infmodal(MODAL_RODOVIARIO, montar_rodo("ISENTO"))
		self.assertEqual(grupo["@versaoModal"], "4.00")
		self.assertEqual(grupo["rodo"], {"RNTRC": "ISENTO"})

	def test_infmodal_vazio_ou_modal_sem_montador_e_erro(self):
		with self.assertRaises(CteInvalido):
			montar_infmodal(MODAL_RODOVIARIO, {})

		with self.assertRaises(CteInvalido):
			montar_infmodal("02", montar_rodo("ISENTO"))

	def test_infcte_norm_na_ordem_do_xsd(self):
		grupo = montar_infcte_norm({"proPred": "x"}, {"@versaoModal": "4.00"}, {"infNFe": []})
		self.assertEqual(list(grupo), ["infCarga", "infDoc", "infModal"])

	def test_infdoc_e_opcional(self):
		self.assertNotIn("infDoc", _infcte_norm())


class TestMontarInfCte(unittest.TestCase):
	def test_ordem_dos_filhos_do_xsd(self):
		infcte, _ = _montar()
		self.assertEqual(list(infcte), ["@Id", "ide", "emit", "rem", "dest", "vPrest", "imp", "infCTeNorm"])

	def test_rem_e_dest_sao_opcionais(self):
		infcte, _ = _montar(remetente=None, destinatario=None)
		self.assertNotIn("rem", infcte)
		self.assertNotIn("dest", infcte)

	def test_a_chave_sai_do_ide_e_do_emitente_e_o_cdv_e_da_mesma_chave(self):
		"""Uma fonte só: número, série, código numérico e CNPJ do emitente → chave; o `cDV`
		do `ide` e o `@Id` saem dela — nunca informados em paralelo."""
		infcte, chave = _montar()
		decomposta = ler_chave(chave)
		self.assertEqual(decomposta.modelo, "57")
		self.assertEqual(decomposta.numero, "000000042")
		self.assertEqual(decomposta.cnpj, "11222333000181")
		self.assertEqual(infcte["@Id"], f"CTe{chave}")
		self.assertEqual(infcte["ide"]["cDV"], decomposta.dv)

	def test_mudar_o_numero_move_a_chave(self):
		_, chave_a = _montar(identificacao=_identificacao(numero="1"))
		_, chave_b = _montar(identificacao=_identificacao(numero="2"))
		self.assertNotEqual(chave_a, chave_b)

	def test_identificacao_invalida_e_recusada_antes_de_montar(self):
		with self.assertRaises(CteInvalido):
			_montar(identificacao=_identificacao(modal="9"))

	def test_ponta_a_ponta_monta_serializa_e_assina(self):
		"""Teste-âncora: as peças de incrementos diferentes se encaixam de verdade."""
		infcte, chave = _montar()
		cte = montar_cte(infcte, chave)
		xml = para_xml(cte)
		self.assertIn(f'Id="CTe{chave}"', xml)
		self.assertIn("<vTPrest>150.00</vTPrest>", xml)
		self.assertIn('<infModal versaoModal="4.00">', xml)
		self.assertIn("<RNTRC>12345678</RNTRC>", xml)

		assinado = assinar_cte(cte, AssinadorFalso())
		self.assertIn("Signature", assinado["CTe"])
		self.assertIn("<Signature", para_xml(assinado))


if __name__ == "__main__":
	unittest.main()
