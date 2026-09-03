# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da montagem do documento NF-e.

O teste que mais importa é `TestChaveDerivadaDoIde`: a chave repete oito dados que também
vivem no grupo `ide`, e duas fontes para o mesmo dado é onde divergência silenciosa
nasce. Aqui a chave é derivada, nunca informada em paralelo — e o teste prova que mexer
no `ide` move a chave junto.
"""

import unittest
from datetime import datetime

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave, validar_chave
from erpnext_brasil.fiscal.documento.nfe import (
	MODELO_NFCE,
	NAMESPACE_NFE,
	TIPO_EMISSAO_SVCAN,
	TIPO_EMISSAO_SVCRS,
	Destinatario,
	Emitente,
	Identificacao,
	NFeInvalida,
	assinar_nfe,
	ativar_contingencia_svc,
	montar_dest,
	montar_emit,
	montar_ide,
	montar_infnfe,
	montar_nfe,
)
from erpnext_brasil.fiscal.documento.serializacao import para_xml

EMISSAO = datetime(2026, 8, 24, 14, 30, 0)


def identificacao(**ajustes) -> Identificacao:
	valores = {
		"uf": "35",
		"municipio_fato_gerador": "3550308",
		"natureza_operacao": "Venda de mercadoria",
		"serie": "1",
		"numero": "42",
		"codigo_numerico": "12345678",
		"emissao": EMISSAO,
	}
	valores.update(ajustes)

	return Identificacao(**valores)


def emitente(**ajustes) -> Emitente:
	valores = {
		"cnpj": "11.222.333/0001-81",
		"nome": "Empresa Exemplo Ltda",
		"inscricao_estadual": "110042490114",
		"regime_tributario": "3",
		"endereco": {"xLgr": "Rua Um", "nro": "100", "cMun": "3550308", "UF": "SP"},
	}
	valores.update(ajustes)

	return Emitente(**valores)


def destinatario(**ajustes) -> Destinatario:
	valores = {
		"nome": "Cliente Exemplo Ltda",
		"indicador_ie": "1",
		"cnpj_cpf": "11.444.777/0001-61",
		"inscricao_estadual": "110042490114",
	}
	valores.update(ajustes)

	return Destinatario(**valores)


def documento(**ajustes):
	from erpnext_brasil.fiscal.documento.pagamento import montar_pag
	from erpnext_brasil.fiscal.documento.transporte import montar_transp

	return montar_infnfe(
		identificacao=ajustes.get("ide", identificacao()),
		emitente=ajustes.get("emit", emitente()),
		destinatario=ajustes.get("dest", destinatario()),
		itens=ajustes.get("itens", [{"prod": {"cProd": "1"}}]),
		totais=ajustes.get("totais", {"ICMSTot": {}}),
		transp=ajustes.get("transp", montar_transp("9")["transp"]),
		pag=ajustes.get("pag", montar_pag([{"forma": "90", "valor": None}])["pag"]),
		cobr=ajustes.get("cobr"),
		infadic=ajustes.get("infadic"),
	)


class TestCobrancaNaNfe(unittest.TestCase):
	"""O grupo `cobr` entra entre `transp` e `pag` — a ordem do `xs:sequence`.

	Ordem errada produz XML que outras ferramentas leem e o validador da SEFAZ
	rejeita: o pior tipo de erro, porque parece certo até a transmissão.
	"""

	def _cobr(self):
		from datetime import date
		from decimal import Decimal

		from erpnext_brasil.fiscal.documento.cobranca import Duplicata, Fatura, montar_cobr

		return montar_cobr(
			Fatura(original=Decimal("600.00")),
			[
				Duplicata(vencimento=date(2026, 10, 10), valor=Decimal("300.00"), numero="001"),
				Duplicata(vencimento=date(2026, 11, 10), valor=Decimal("300.00"), numero="002"),
			],
		)["cobr"]

	def test_cobr_entra_entre_transp_e_pag(self):
		campos = list(documento(cobr=self._cobr())["infNFe"])

		self.assertLess(campos.index("transp"), campos.index("cobr"))
		self.assertLess(campos.index("cobr"), campos.index("pag"))

	def test_venda_a_vista_nao_declara_duplicata(self):
		"""Sem parcelamento o grupo não aparece — inventar uma duplicata seria
		declarar um título de crédito que não existe."""
		self.assertNotIn("cobr", documento()["infNFe"])

	def test_as_duplicatas_chegam_intactas(self):
		cobr = documento(cobr=self._cobr())["infNFe"]["cobr"]

		self.assertEqual(len(cobr["dup"]), 2)
		self.assertEqual(cobr["dup"][0]["dVenc"], "2026-10-10")

	def test_a_ordem_sobrevive_a_serializacao(self):
		"""O que importa de verdade é o XML final, não o dicionário."""
		from erpnext_brasil.fiscal.documento.nfe import montar_nfe
		from erpnext_brasil.fiscal.documento.serializacao import para_xml

		xml = para_xml(montar_nfe(documento(cobr=self._cobr())))

		self.assertLess(xml.index("<transp>"), xml.index("<cobr>"))
		self.assertLess(xml.index("<cobr>"), xml.index("<pag>"))


class TestEstrutura(unittest.TestCase):
	def setUp(self):
		self.doc = documento()["infNFe"]

	def test_grupos_obrigatorios(self):
		for grupo in ("ide", "emit", "dest", "det", "total"):
			with self.subTest(grupo=grupo):
				self.assertIn(grupo, self.doc)

	def test_versao_e_id(self):
		self.assertEqual(self.doc["@versao"], "4.00")
		self.assertTrue(self.doc["@Id"].startswith("NFe"))
		self.assertEqual(len(self.doc["@Id"]), 47)  # "NFe" + 44

	def test_itens_numerados(self):
		doc = documento(itens=[{"prod": {}}, {"prod": {}}, {"prod": {}}])["infNFe"]

		self.assertEqual([d["@nItem"] for d in doc["det"]], ["1", "2", "3"])

	def test_documento_sem_item_e_erro(self):
		with self.assertRaises(NFeInvalida):
			documento(itens=[])


class TestChaveDerivadaDoIde(unittest.TestCase):
	"""A chave nunca é informada em paralelo: é calculada do `ide` e do emitente."""

	def setUp(self):
		self.doc = documento()["infNFe"]
		self.chave = self.doc["@Id"][3:]

	def test_chave_e_valida(self):
		self.assertEqual(validar_chave(self.chave), self.chave)

	def test_chave_reflete_o_ide(self):
		lida = ler_chave(self.chave)

		self.assertEqual(lida.uf, self.doc["ide"]["cUF"])
		self.assertEqual(lida.modelo, self.doc["ide"]["mod"])
		self.assertEqual(lida.numero.lstrip("0"), self.doc["ide"]["nNF"])
		self.assertEqual(lida.codigo_numerico, self.doc["ide"]["cNF"])
		self.assertEqual(lida.tipo_emissao, self.doc["ide"]["tpEmis"])

	def test_chave_reflete_o_cnpj_do_emitente(self):
		self.assertEqual(ler_chave(self.chave).cnpj, self.doc["emit"]["CNPJ"])

	def test_ano_e_mes_vem_da_emissao(self):
		self.assertEqual(ler_chave(self.chave).ano_mes, "2608")

	def test_cdv_do_ide_e_o_da_chave(self):
		"""Duas fontes para o mesmo dígito seria divergência garantida."""
		self.assertEqual(self.doc["ide"]["cDV"], self.chave[-1])

	def test_mudar_o_numero_muda_a_chave(self):
		outra = documento(ide=identificacao(numero="43"))["infNFe"]["@Id"][3:]

		self.assertNotEqual(outra, self.chave)
		self.assertEqual(ler_chave(outra).numero, "000000043")

	def test_emitente_com_cnpj_alfanumerico(self):
		doc = documento(emit=emitente(cnpj="12ABC34501DE35"))["infNFe"]
		lida = ler_chave(doc["@Id"][3:])

		self.assertEqual(lida.cnpj, "12ABC34501DE35")
		self.assertTrue(lida.cnpj_alfanumerico)


class TestGruposObrigatoriosTranspEPag(unittest.TestCase):
	"""transp e pag não têm minOccurs="0" no XSD — são obrigatórios mesmo vazios."""

	def test_sem_transp_e_erro(self):
		from erpnext_brasil.fiscal.documento.pagamento import montar_pag

		with self.assertRaises(NFeInvalida) as ctx:
			montar_infnfe(
				identificacao=identificacao(),
				emitente=emitente(),
				destinatario=destinatario(),
				itens=[{"prod": {}}],
				totais={"ICMSTot": {}},
				transp=None,
				pag=montar_pag([{"forma": "90", "valor": None}])["pag"],
			)

		self.assertEqual(ctx.exception.campo, "transp")

	def test_sem_pag_e_erro(self):
		from erpnext_brasil.fiscal.documento.transporte import montar_transp

		with self.assertRaises(NFeInvalida) as ctx:
			montar_infnfe(
				identificacao=identificacao(),
				emitente=emitente(),
				destinatario=destinatario(),
				itens=[{"prod": {}}],
				totais={"ICMSTot": {}},
				transp=montar_transp("9")["transp"],
				pag=None,
			)

		self.assertEqual(ctx.exception.campo, "pag")

	def test_mensagem_orienta_o_valor_minimo(self):
		"""A mensagem não só recusa: diz como preencher quando não há o que informar."""
		with self.assertRaises(NFeInvalida) as ctx:
			documento(transp=None)

		self.assertIn("9", str(ctx.exception))


class TestRegra897(unittest.TestCase):
	"""Rejeição 897 / regra B03-10: restrições do código numérico."""

	def test_cnf_igual_a_nnf_e_erro(self):
		with self.assertRaises(NFeInvalida) as ctx:
			montar_ide(identificacao(numero="42", codigo_numerico="00000042"), "x" * 44)

		self.assertIn("897", str(ctx.exception))

	def test_cnf_com_digitos_iguais_e_erro(self):
		for codigo in ("00000000", "11111111", "99999999"):
			with self.subTest(codigo=codigo):
				with self.assertRaises(NFeInvalida):
					montar_ide(identificacao(codigo_numerico=codigo), "x" * 44)

	def test_cnf_valido_passa(self):
		grupo = montar_ide(identificacao(codigo_numerico="12345678"), "x" * 44)

		self.assertEqual(grupo["cNF"], "12345678")

	def test_campo_do_erro_e_apontado(self):
		with self.assertRaises(NFeInvalida) as ctx:
			montar_ide(identificacao(codigo_numerico="11111111"), "x" * 44)

		self.assertEqual(ctx.exception.campo, "codigo_numerico")


class TestIde(unittest.TestCase):
	def setUp(self):
		self.grupo = documento()["infNFe"]["ide"]

	def test_ambiente_padrao_e_homologacao(self):
		"""Emitir em produção precisa ser escolha consciente."""
		self.assertEqual(self.grupo["tpAmb"], "2")

	def test_data_com_fuso(self):
		self.assertIn("T", self.grupo["dhEmi"])

	def test_natureza_obrigatoria(self):
		with self.assertRaises(NFeInvalida) as ctx:
			montar_ide(identificacao(natureza_operacao="  "), "x" * 44)

		self.assertIn("natureza", str(ctx.exception))

	def test_modelo_invalido(self):
		with self.assertRaises(NFeInvalida):
			montar_ide(identificacao(modelo="99"), "x" * 44)

	def test_nfce_e_aceita(self):
		grupo = montar_ide(identificacao(modelo=MODELO_NFCE), "x" * 44)

		self.assertEqual(grupo["mod"], MODELO_NFCE)


class TestEmitente(unittest.TestCase):
	def test_cnpj_validado_e_limpo(self):
		self.assertEqual(montar_emit(emitente())["CNPJ"], "11222333000181")

	def test_cnpj_invalido_e_erro(self):
		with self.assertRaises(NFeInvalida) as ctx:
			montar_emit(emitente(cnpj="11222333000182"))

		self.assertIn("CNPJ do emitente", str(ctx.exception))

	def test_opcionais_ausentes_nao_viram_tag_vazia(self):
		"""Tag vazia é rejeição, não omissão."""
		grupo = montar_emit(emitente())

		for opcional in ("xFant", "IM", "CNAE"):
			self.assertNotIn(opcional, grupo)

	def test_opcionais_presentes_entram(self):
		grupo = montar_emit(emitente(nome_fantasia="Exemplo", cnae="4711302"))

		self.assertEqual(grupo["xFant"], "Exemplo")
		self.assertEqual(grupo["CNAE"], "4711302")

	def test_ie_obrigatoria(self):
		with self.assertRaises(NFeInvalida):
			montar_emit(emitente(inscricao_estadual=""))


class TestDestinatario(unittest.TestCase):
	def test_pessoa_juridica_usa_cnpj(self):
		grupo = montar_dest(destinatario())

		self.assertIn("CNPJ", grupo)
		self.assertNotIn("CPF", grupo)

	def test_pessoa_fisica_usa_cpf(self):
		grupo = montar_dest(destinatario(cnpj_cpf="111.444.777-35", indicador_ie="9", inscricao_estadual=""))

		self.assertIn("CPF", grupo)
		self.assertNotIn("CNPJ", grupo)

	def test_estrangeiro(self):
		grupo = montar_dest(destinatario(cnpj_cpf="", identificacao_estrangeiro="EX123", indicador_ie="9"))

		self.assertEqual(grupo["idEstrangeiro"], "EX123")

	def test_documento_e_estrangeiro_juntos_e_erro(self):
		"""Mutuamente exclusivos no XSD: informar os dois é rejeição."""
		with self.assertRaises(NFeInvalida) as ctx:
			montar_dest(destinatario(identificacao_estrangeiro="EX123"))

		self.assertIn("apenas um", str(ctx.exception))

	def test_sem_nenhuma_identificacao_e_erro(self):
		with self.assertRaises(NFeInvalida):
			montar_dest(destinatario(cnpj_cpf=""))

	def test_ie_apenas_para_contribuinte(self):
		contribuinte = montar_dest(destinatario(indicador_ie="1"))
		nao_contribuinte = montar_dest(destinatario(indicador_ie="9", inscricao_estadual=""))

		self.assertIn("IE", contribuinte)
		self.assertNotIn("IE", nao_contribuinte)

	def test_contribuinte_sem_ie_e_erro(self):
		with self.assertRaises(NFeInvalida):
			montar_dest(destinatario(indicador_ie="1", inscricao_estadual=""))

	def test_cpf_invalido_e_erro(self):
		with self.assertRaises(NFeInvalida):
			montar_dest(destinatario(cnpj_cpf="111.444.777-36", indicador_ie="9"))


class TestInfAdic(unittest.TestCase):
	"""`montar_infadic` devolve `None` quando vazio; `montar_infnfe` recebe o miolo,
	não o dicionário envolto — mesma convenção de `transp` e `pag`."""

	def test_sem_infadic_o_grupo_nao_aparece(self):
		doc = documento()["infNFe"]

		self.assertNotIn("infAdic", doc)

	def test_com_infadic_encaixa_no_documento(self):
		from erpnext_brasil.fiscal.documento.informacoes_adicionais import montar_infadic

		resultado = montar_infadic(informacoes_complementares="Venda à vista")
		doc = documento(infadic=resultado["infAdic"])["infNFe"]

		self.assertEqual(doc["infAdic"]["infCpl"], "Venda à vista")

	def test_infadic_vazio_nao_e_repassado(self):
		from erpnext_brasil.fiscal.documento.informacoes_adicionais import montar_infadic

		self.assertIsNone(montar_infadic())


class TestMontarNFe(unittest.TestCase):
	"""A raiz NFe, onde a Signature entra como irmã de infNFe (enveloped)."""

	def test_namespace_na_raiz(self):
		nfe = montar_nfe(documento())

		self.assertEqual(nfe["NFe"]["@xmlns"], NAMESPACE_NFE)

	def test_infnfe_preservado(self):
		infnfe = documento()
		nfe = montar_nfe(infnfe)

		self.assertEqual(nfe["NFe"]["infNFe"], infnfe["infNFe"])


class AssinadorFalso:
	"""Duplo que satisfaz a porta `Assinador` sem certificado — registra o que recebeu."""

	def __init__(self):
		self.recebido: tuple[bytes, str] | None = None

	def assinar(self, xml: bytes, id_elemento: str):
		from erpnext_brasil.fiscal.documento.assinatura import MaterialAssinatura

		self.recebido = (xml, id_elemento)

		return MaterialAssinatura(digest="ZGlnZXN0", assinatura="YXNzaW5hdHVyYQ==", certificado="Y2VydA==")


class TestAssinarNFe(unittest.TestCase):
	def setUp(self):
		self.nfe = montar_nfe(documento())
		self.assinador = AssinadorFalso()
		self.assinado = assinar_nfe(self.nfe, self.assinador)

	def test_assina_o_id_do_infnfe(self):
		"""O que se assina é o Id de infNFe, nunca outro elemento."""
		self.assertEqual(self.assinador.recebido[1], self.nfe["NFe"]["infNFe"]["@Id"])

	def test_signature_e_irma_de_infnfe(self):
		"""Enveloped: Signature dentro de NFe, ao lado de infNFe — não dentro dele."""
		self.assertIn("infNFe", self.assinado["NFe"])
		self.assertIn("Signature", self.assinado["NFe"])
		self.assertNotIn("Signature", self.assinado["NFe"]["infNFe"])

	def test_infnfe_nao_muda_ao_assinar(self):
		self.assertEqual(self.assinado["NFe"]["infNFe"], self.nfe["NFe"]["infNFe"])

	def test_documento_assinado_serializa(self):
		xml = para_xml(self.assinado)

		self.assertIn("<Signature ", xml)
		self.assertIn(f'Id="{self.nfe["NFe"]["infNFe"]["@Id"]}"', xml)

	def test_referencia_aponta_para_a_chave(self):
		signature = self.assinado["NFe"]["Signature"]
		uri = signature["SignedInfo"]["Reference"]["@URI"]

		self.assertEqual(uri, f"#{self.nfe['NFe']['infNFe']['@Id']}")


class TestConformidadeDeTags(unittest.TestCase):
	"""Toda tag emitida precisa existir no layout oficial."""

	def setUp(self):
		import json
		import pathlib

		manifesto = (
			pathlib.Path(__file__).resolve().parents[1] / "fiscal" / "documento" / "elementos_nfe.json"
		)
		self.elementos = set(json.loads(manifesto.read_text(encoding="utf-8")))

	def _tags(self, no, encontradas=None):
		encontradas = encontradas if encontradas is not None else set()

		if isinstance(no, dict):
			for chave, valor in no.items():
				# Atributos usam prefixo "@" e não são elementos do manifesto.
				if not chave.startswith("@"):
					encontradas.add(chave)

				self._tags(valor, encontradas)
		elif isinstance(no, list):
			for item in no:
				self._tags(item, encontradas)

		return encontradas

	def test_todas_as_tags_existem_no_xsd(self):
		from erpnext_brasil.fiscal.documento.informacoes_adicionais import montar_infadic

		doc = documento(
			dest=destinatario(),
			itens=[{"prod": {"cProd": "1"}}],
			totais={"ICMSTot": {}},
			infadic=montar_infadic(informacoes_complementares="Teste")["infAdic"],
		)

		desconhecidas = self._tags(doc) - self.elementos

		self.assertEqual(desconhecidas, set(), f"tags fora do layout: {sorted(desconhecidas)}")

	def test_tags_do_destinatario_estrangeiro_existem(self):
		grupo = montar_dest(destinatario(cnpj_cpf="", identificacao_estrangeiro="EX1", indicador_ie="9"))

		self.assertEqual(self._tags(grupo) - self.elementos, set())


class TestAtivarContingenciaSVC(unittest.TestCase):
	"""`ativar_contingencia_svc` — a chave repete `tpEmis` (posição 35), então ativar
	contingência muda a chave; e o tipo de SVC é derivado da UF, não escolhido à toa."""

	def test_sp_cai_no_svcan(self):
		nova = ativar_contingencia_svc(identificacao(uf="35"), "SEFAZ SP fora do ar por instabilidade")

		self.assertEqual(nova.tipo_emissao, TIPO_EMISSAO_SVCAN)

	def test_am_cai_no_svcrs(self):
		"""AM tem webservice próprio como autorizador normal, mas cai no SVC-RS em
		contingência — não no SVC-AN, e muito menos num "SVC-AM" que não existe."""
		nova = ativar_contingencia_svc(identificacao(uf="13"), "SEFAZ AM fora do ar por instabilidade")

		self.assertEqual(nova.tipo_emissao, TIPO_EMISSAO_SVCRS)

	def test_original_nao_muda(self):
		"""Identificacao é imutável — ativar contingência devolve variante nova."""
		original = identificacao(uf="35")
		ativar_contingencia_svc(original, "SEFAZ SP fora do ar por instabilidade")

		self.assertEqual(original.tipo_emissao, "1")

	def test_nfce_nao_pode_entrar_em_contingencia_svc(self):
		with self.assertRaises(NFeInvalida):
			ativar_contingencia_svc(identificacao(uf="35", modelo=MODELO_NFCE), "SEFAZ SP fora do ar")

	def test_justificativa_curta_e_rejeitada(self):
		with self.assertRaises(NFeInvalida):
			ativar_contingencia_svc(identificacao(uf="35"), "curta demais")

	def test_uf_desconhecida_levanta_erro(self):
		with self.assertRaises(NFeInvalida):
			ativar_contingencia_svc(identificacao(uf="99"), "SEFAZ fora do ar por instabilidade")

	def test_chave_muda_em_relacao_a_emissao_normal(self):
		"""tpEmis é a posição 35 da chave — mudar de '1' para '6'/'7' muda a chave
		inteira, exatamente como a fonte de referência documenta."""
		normal = identificacao(uf="35")
		contingencia = ativar_contingencia_svc(normal, "SEFAZ SP fora do ar por instabilidade")

		doc_normal = montar_infnfe(
			normal, emitente(), destinatario(), [{"prod": {"cProd": "1"}}], {"ICMSTot": {}},
			transp={"modFrete": "9"}, pag={"detPag": [{"tPag": "90"}]},
		)  # fmt: skip
		doc_contingencia = montar_infnfe(
			contingencia, emitente(), destinatario(), [{"prod": {"cProd": "1"}}], {"ICMSTot": {}},
			transp={"modFrete": "9"}, pag={"detPag": [{"tPag": "90"}]},
		)  # fmt: skip

		chave_normal = doc_normal["infNFe"]["@Id"]
		chave_contingencia = doc_contingencia["infNFe"]["@Id"]

		self.assertNotEqual(chave_normal, chave_contingencia)
		self.assertEqual(doc_normal["infNFe"]["ide"]["tpEmis"], "1")
		self.assertEqual(doc_contingencia["infNFe"]["ide"]["tpEmis"], TIPO_EMISSAO_SVCAN)

	def test_dhcont_e_xjust_aparecem_no_ide_em_contingencia_e_so_ai(self):
		normal = identificacao(uf="35")
		contingencia = ativar_contingencia_svc(normal, "SEFAZ SP fora do ar por instabilidade")

		ide_normal = montar_ide(normal, "3" * 44)
		ide_contingencia = montar_ide(contingencia, "3" * 44)

		self.assertNotIn("dhCont", ide_normal)
		self.assertNotIn("xJust", ide_normal)
		self.assertEqual(ide_contingencia["xJust"], "SEFAZ SP fora do ar por instabilidade")
		self.assertIn("dhCont", ide_contingencia)


if __name__ == "__main__":
	unittest.main()
