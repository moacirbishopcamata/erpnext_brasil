# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da montagem do CT-e a partir de dados já extraídos (`fiscal/cte_montagem.py`).

Tarefa 2.2 de `fechar-laco-cte-mdfe`, escrita **antes** do código: o esqueleto anterior de
`integracao/cte_documento.py` tinha `cNF` fixo, `infCTeNorm` vazio e `imp` de mentira, e
nenhum teste o alcançava porque ele importa `frappe`. A montagem pura existe para que a
suíte consiga travar exatamente isso.

A estrutura esperada (ordem do `xs:sequence`, `vRec` obrigatório, `CRT` no emitente,
`infCarga`/`infModal` no corpo) foi lida do `cteTiposBasico_v4.00.xsd` do `sped-cte`
(`PL_CTe_400`), não suposta por analogia com a NF-e.
"""

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from erpnext_brasil.fiscal.cte import CteInvalido, IdentificacaoCte, TomadorOutros
from erpnext_brasil.fiscal.cte_montagem import (
	CargaCte,
	DadosCte,
	EmitenteCte,
	IcmsCte,
	ParteCte,
	QuantidadeCarga,
	montar_cte_de_dados,
)
from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.documento.serializacao import para_xml

ENDERECO = {
	"xLgr": "Rua A",
	"nro": "10",
	"xBairro": "Centro",
	"cMun": "1100205",
	"xMun": "Porto Velho",
	"CEP": "76800000",
	"UF": "RO",
}


def _emitente(**mudancas) -> EmitenteCte:
	base = dict(
		cnpj="11222333000181",
		nome="Transportadora Teste Ltda",
		inscricao_estadual="123456789",
		regime_tributario="3",
		endereco=ENDERECO,
	)
	return EmitenteCte(**{**base, **mudancas})


def _parte(documento: str, nome: str, **mudancas) -> ParteCte:
	return ParteCte(documento=documento, nome=nome, endereco=ENDERECO, **mudancas)


def _carga(**mudancas) -> CargaCte:
	base = dict(
		produto_predominante="Grãos",
		quantidades=(QuantidadeCarga(unidade="01", tipo_medida="PESO BRUTO", quantidade=Decimal("1000")),),
		valor=Decimal("5000"),
	)
	return CargaCte(**{**base, **mudancas})


def _dados(**mudancas) -> DadosCte:
	base = dict(
		emitente=_emitente(),
		remetente=_parte("11444777000161", "Remetente SA", inscricao_estadual="987654321"),
		destinatario=_parte("52998224725", "Destinatario Pessoa"),
		tomador_papel="3",
		tomador_outros=None,
		indicador_ie_tomador="9",
		cfop="5353",
		natureza_operacao="Prestação de serviço de transporte",
		serie="1",
		numero="42",
		emissao=datetime(2026, 10, 3, 9, 30, 0, tzinfo=timezone(timedelta(hours=-4))),
		ambiente="2",
		modal="01",
		tipo_servico="0",
		municipio_inicio=("1100205", "Porto Velho", "RO"),
		municipio_fim=("1100122", "Ji-Paraná", "RO"),
		valor_prestacao=Decimal("1500.00"),
		icms=IcmsCte(cst="00", aliquota=Decimal("17")),
		carga=_carga(),
		rntrc="12345678",
	)
	return DadosCte(**{**base, **mudancas})


def _sorteio_fixo(_numero):
	return "12345678"


def _montar(**mudancas):
	return montar_cte_de_dados(_dados(**mudancas), sortear=_sorteio_fixo)


def _info(**mudancas) -> dict:
	arvore, _ = _montar(**mudancas)
	return arvore["CTe"]["infCte"]


class TestMontagemValida(unittest.TestCase):
	def test_os_grupos_saem_na_ordem_do_leiaute(self):
		grupos = [k for k in _info() if not k.startswith("@")]

		self.assertEqual(grupos, ["ide", "emit", "rem", "dest", "vPrest", "imp", "infCTeNorm"])

	def test_o_numero_alocado_entra_na_chave_e_no_ide(self):
		arvore, chave = _montar(numero="42")
		decomposta = ler_chave(chave)

		self.assertEqual(decomposta.modelo, "57")
		self.assertEqual(int(decomposta.numero), 42)
		self.assertEqual(arvore["CTe"]["infCte"]["ide"]["nCT"], "42")

	def test_o_id_e_derivado_da_chave(self):
		arvore, chave = _montar()

		self.assertEqual(arvore["CTe"]["infCte"]["@Id"], f"CTe{chave}")

	def test_o_codigo_numerico_vem_do_sorteio_e_nao_e_fixo(self):
		ide = _info()["ide"]

		self.assertEqual(ide["cCT"], "12345678")
		self.assertNotEqual(ide["cCT"], "00000000")

	def test_o_codigo_numerico_do_sorteio_real_nao_repete_o_numero(self):
		arvore, _ = montar_cte_de_dados(_dados(numero="87654321"))
		ide = arvore["CTe"]["infCte"]["ide"]

		self.assertNotEqual(ide["cCT"].lstrip("0"), ide["nCT"].lstrip("0"))
		self.assertGreater(len(set(ide["cCT"])), 1)

	def test_o_emitente_leva_o_crt(self):
		self.assertEqual(_info()["emit"]["CRT"], "3")

	def test_o_valor_a_receber_acompanha_o_valor_da_prestacao(self):
		v_prest = _info()["vPrest"]

		self.assertEqual(v_prest["vTPrest"], "1500.00")
		self.assertEqual(v_prest["vRec"], "1500.00")

	def test_o_corpo_normal_tem_carga_e_modal_rodoviario(self):
		corpo = _info()["infCTeNorm"]

		self.assertEqual(corpo["infCarga"]["proPred"], "Grãos")
		self.assertEqual(corpo["infCarga"]["vCarga"], "5000.00")
		self.assertEqual(corpo["infModal"]["@versaoModal"], "4.00")
		self.assertEqual(corpo["infModal"]["rodo"]["RNTRC"], "12345678")

	def test_cada_quantidade_da_carga_vira_um_infq(self):
		quantidades = (
			QuantidadeCarga(unidade="01", tipo_medida="PESO BRUTO", quantidade=Decimal("1000")),
			QuantidadeCarga(unidade="03", tipo_medida="CAIXAS", quantidade=Decimal("20.5")),
		)
		infq = _info(carga=_carga(quantidades=quantidades))["infCTeNorm"]["infCarga"]["infQ"]

		self.assertEqual([q["cUnid"] for q in infq], ["01", "03"])
		self.assertEqual(infq[1]["qCarga"], "20.5000")

	def test_a_carga_sem_valor_omite_vcarga(self):
		carga = _info(carga=_carga(valor=None))["infCTeNorm"]["infCarga"]

		self.assertNotIn("vCarga", carga)

	def test_o_infcte_declara_a_versao_do_leiaute(self):
		"""`infCte/@versao` é obrigatório no XSD — a validação contra o schema oficial o apontou."""
		self.assertEqual(_info()["@versao"], "4.00")

	def test_a_data_de_emissao_sai_com_fuso(self):
		"""`dhEmi` exige o deslocamento (`-04:00`); sem ele o XSD recusa o padrão."""
		self.assertEqual(_info()["ide"]["dhEmi"], "2026-10-03T09:30:00-04:00")

	def test_a_arvore_serializa_em_xml(self):
		arvore, _ = _montar()
		xml = para_xml(arvore)

		self.assertEqual(xml.count("<infQ>"), 1)
		self.assertIn("<RNTRC>12345678</RNTRC>", xml)


class TestTomador(unittest.TestCase):
	def test_destinatario_como_tomador_usa_toma3_codigo_3(self):
		ide = _info(tomador_papel="3")["ide"]

		self.assertEqual(ide["toma3"], {"toma": "3"})

	def test_remetente_como_tomador_usa_toma3_codigo_0(self):
		ide = _info(tomador_papel="0")["ide"]

		self.assertEqual(ide["toma3"], {"toma": "0"})

	def test_outros_usa_toma4_com_o_cadastro_completo(self):
		outros = TomadorOutros(nome="Pagador SA", cnpj_cpf="11444777000161", endereco=ENDERECO)
		ide = _info(tomador_papel="4", tomador_outros=outros)["ide"]

		self.assertNotIn("toma3", ide)
		self.assertEqual(ide["toma4"]["toma"], "4")
		self.assertEqual(ide["toma4"]["CNPJ"], "11444777000161")

	def test_outros_sem_cadastro_do_tomador_recusa(self):
		with self.assertRaises(CteInvalido) as erro:
			_montar(tomador_papel="4", tomador_outros=None)

		self.assertEqual(erro.exception.campo, "tomador")

	def test_o_indicador_de_ie_do_tomador_vai_para_o_ide(self):
		self.assertEqual(_info(indicador_ie_tomador="1")["ide"]["indIEToma"], "1")

	def test_papel_desconhecido_recusa(self):
		with self.assertRaises(CteInvalido) as erro:
			_montar(tomador_papel="7")

		self.assertEqual(erro.exception.campo, "tomador")


class TestIcms(unittest.TestCase):
	def _icms(self, **mudancas) -> dict:
		return _info(**mudancas)["imp"]["ICMS"]

	def test_cst_00_calcula_base_e_imposto_sobre_o_valor_da_prestacao(self):
		icms = self._icms(icms=IcmsCte(cst="00", aliquota=Decimal("17")))

		self.assertEqual(
			icms, {"ICMS00": {"CST": "00", "vBC": "1500.00", "pICMS": "17.00", "vICMS": "255.00"}}
		)

	def test_cst_20_aplica_a_reducao_da_base(self):
		icms = self._icms(icms=IcmsCte(cst="20", aliquota=Decimal("12"), reducao_base=Decimal("40")))
		grupo = icms["ICMS20"]

		self.assertEqual(grupo["pRedBC"], "40.00")
		self.assertEqual(grupo["vBC"], "900.00")
		self.assertEqual(grupo["vICMS"], "108.00")

	def test_cst_20_sem_reducao_recusa(self):
		with self.assertRaises(CteInvalido) as erro:
			_montar(icms=IcmsCte(cst="20", aliquota=Decimal("12")))

		self.assertEqual(erro.exception.campo, "icms")

	def test_cst_de_isencao_nao_leva_valores(self):
		for cst in ("40", "41", "51"):
			with self.subTest(cst=cst):
				self.assertEqual(self._icms(icms=IcmsCte(cst=cst)), {"ICMS45": {"CST": cst}})

	def test_cst_90_leva_base_e_imposto(self):
		grupo = self._icms(icms=IcmsCte(cst="90", aliquota=Decimal("7")))["ICMS90"]

		self.assertEqual((grupo["CST"], grupo["vBC"], grupo["vICMS"]), ("90", "1500.00", "105.00"))

	def test_simples_nacional_usa_icmssn(self):
		self.assertEqual(self._icms(icms=IcmsCte(cst="SN")), {"ICMSSN": {"CST": "90", "indSN": "1"}})

	def test_o_imposto_arredonda_meio_para_cima_em_centavos(self):
		icms = self._icms(valor_prestacao=Decimal("100.05"), icms=IcmsCte(cst="00", aliquota=Decimal("12.5")))

		self.assertEqual(icms["ICMS00"]["vICMS"], "12.51")

	def test_cst_nao_suportado_recusa_nomeando_o_cst(self):
		for cst in ("60", "99", ""):
			with self.subTest(cst=cst), self.assertRaises(CteInvalido) as erro:
				_montar(icms=IcmsCte(cst=cst, aliquota=Decimal("12")))

			self.assertEqual(erro.exception.campo, "icms")

	def test_aliquota_fora_de_0_a_100_recusa(self):
		for aliquota in (Decimal("-1"), Decimal("100.01")):
			with self.subTest(aliquota=aliquota), self.assertRaises(CteInvalido):
				_montar(icms=IcmsCte(cst="00", aliquota=aliquota))


class TestRecusas(unittest.TestCase):
	"""Cada ausência nomeia o dado — a mensagem manda a pessoa ao lugar certo."""

	def _recusa(self, **mudancas) -> CteInvalido:
		with self.assertRaises(CteInvalido) as erro:
			_montar(**mudancas)

		return erro.exception

	def test_sem_remetente(self):
		self.assertEqual(self._recusa(remetente=None).campo, "remetente")

	def test_sem_destinatario(self):
		self.assertEqual(self._recusa(destinatario=None).campo, "destinatario")

	def test_documento_do_remetente_invalido(self):
		erro = self._recusa(remetente=_parte("11444777000162", "Remetente SA"))

		self.assertEqual(erro.campo, "remetente")

	def test_valor_da_prestacao_zerado(self):
		self.assertEqual(self._recusa(valor_prestacao=Decimal("0")).campo, "valor_prestacao")

	def test_carga_sem_produto_predominante(self):
		self.assertEqual(self._recusa(carga=_carga(produto_predominante=" ")).campo, "carga")

	def test_carga_sem_nenhuma_quantidade(self):
		self.assertEqual(self._recusa(carga=_carga(quantidades=())).campo, "carga")

	def test_unidade_de_carga_fora_do_dominio(self):
		quantidade = QuantidadeCarga(unidade="09", tipo_medida="PESO BRUTO", quantidade=Decimal("1"))

		self.assertEqual(self._recusa(carga=_carga(quantidades=(quantidade,))).campo, "carga")

	def test_quantidade_de_carga_nao_positiva(self):
		quantidade = QuantidadeCarga(unidade="01", tipo_medida="PESO BRUTO", quantidade=Decimal("0"))

		self.assertEqual(self._recusa(carga=_carga(quantidades=(quantidade,))).campo, "carga")

	def test_rntrc_invalido_nomeia_o_rntrc(self):
		self.assertEqual(self._recusa(rntrc="123").campo, "rntrc")

	def test_sem_regime_tributario_do_emitente(self):
		self.assertEqual(self._recusa(emitente=_emitente(regime_tributario="")).campo, "emitente")

	def test_sem_inscricao_estadual_do_emitente(self):
		self.assertEqual(self._recusa(emitente=_emitente(inscricao_estadual="")).campo, "emitente")

	def test_a_recusa_nao_produz_arvore_parcial(self):
		"""Falha antes de devolver qualquer coisa — não há CT-e pela metade para transmitir."""
		with self.assertRaises(CteInvalido):
			montar_cte_de_dados(_dados(remetente=None), sortear=_sorteio_fixo)


class TestEmissaoSemFuso(unittest.TestCase):
	def test_data_sem_fuso_recusa_nomeando_a_emissao(self):
		with self.assertRaises(CteInvalido) as erro:
			_montar(emissao=datetime(2026, 10, 3, 9, 30, 0))

		self.assertEqual(erro.exception.campo, "emissao")


class TestIdentificacaoReaproveitada(unittest.TestCase):
	"""A montagem usa `IdentificacaoCte` (já validada em `fiscal/cte.py`), não um `ide` paralelo."""

	def test_modal_invalido_recusa_pela_validacao_existente(self):
		with self.assertRaises(CteInvalido) as erro:
			_montar(modal="99")

		self.assertEqual(erro.exception.campo, "modal")

	def test_o_tipo_importado_e_o_do_leiaute(self):
		self.assertTrue(hasattr(IdentificacaoCte, "validar"))


if __name__ == "__main__":
	unittest.main()
