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
	Destinatario,
	Emitente,
	Identificacao,
	NFeInvalida,
	montar_dest,
	montar_emit,
	montar_ide,
	montar_infnfe,
)

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
	return montar_infnfe(
		identificacao=ajustes.get("ide", identificacao()),
		emitente=ajustes.get("emit", emitente()),
		destinatario=ajustes.get("dest", destinatario()),
		itens=ajustes.get("itens", [{"prod": {"cProd": "1"}}]),
		totais=ajustes.get("totais", {"ICMSTot": {}}),
	)


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
		grupo = montar_dest(
			destinatario(cnpj_cpf="111.444.777-35", indicador_ie="9", inscricao_estadual="")
		)

		self.assertIn("CPF", grupo)
		self.assertNotIn("CNPJ", grupo)

	def test_estrangeiro(self):
		grupo = montar_dest(
			destinatario(cnpj_cpf="", identificacao_estrangeiro="EX123", indicador_ie="9")
		)

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


class TestConformidadeDeTags(unittest.TestCase):
	"""Toda tag emitida precisa existir no layout oficial."""

	def setUp(self):
		import json
		import pathlib

		manifesto = (
			pathlib.Path(__file__).resolve().parents[1]
			/ "fiscal"
			/ "documento"
			/ "elementos_nfe.json"
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
		doc = documento(
			dest=destinatario(),
			itens=[{"prod": {"cProd": "1"}}],
			totais={"ICMSTot": {}},
		)

		desconhecidas = self._tags(doc) - self.elementos

		self.assertEqual(desconhecidas, set(), f"tags fora do layout: {sorted(desconhecidas)}")

	def test_tags_do_destinatario_estrangeiro_existem(self):
		grupo = montar_dest(
			destinatario(cnpj_cpf="", identificacao_estrangeiro="EX1", indicador_ie="9")
		)

		self.assertEqual(self._tags(grupo) - self.elementos, set())


if __name__ == "__main__":
	unittest.main()
