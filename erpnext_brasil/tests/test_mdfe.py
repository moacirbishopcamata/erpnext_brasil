# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/mdfe.py` — montagem de `infDoc`, `ide` e assinatura do MDF-e."""

import unittest
from datetime import datetime

from erpnext_brasil.fiscal.documento.assinatura import MaterialAssinatura
from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, montar_chave
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.mdfe import (
	EMITENTE_TRANSPORTADOR_CARGA_PROPRIA,
	MODAL_RODOVIARIO,
	NAMESPACE_MDFE,
	IdentificacaoMdfe,
	MdfeInvalido,
	MunicipioCarrega,
	MunicipioDescarga,
	assinar_mdfe,
	montar_ide,
	montar_infdoc,
	montar_mdfe,
)


def _chave(modelo: str, numero: str = "000000001") -> str:
	return montar_chave(
		uf="35",
		ano_mes="2608",
		cnpj="11222333000181",
		modelo=modelo,
		serie="001",
		numero=numero,
		tipo_emissao="1",
		codigo_numerico="12345678",
	)


class TestMontarInfdoc(unittest.TestCase):
	def test_um_municipio_com_cte_e_nfe(self):
		chave_cte = _chave("57")
		chave_nfe = _chave("55")
		municipio = MunicipioDescarga(
			codigo="3550308", nome="São Paulo", chaves_cte=[chave_cte], chaves_nfe=[chave_nfe]
		)

		grupo = montar_infdoc([municipio])

		infmun = grupo["infDoc"]["infMunDescarga"][0]
		self.assertEqual(infmun["cMunDescarga"], "3550308")
		self.assertEqual(infmun["xMunDescarga"], "São Paulo")
		self.assertEqual(infmun["infCTe"], [{"chCTe": chave_cte}])
		self.assertEqual(infmun["infNFe"], [{"chNFe": chave_nfe}])

	def test_grupo_ausente_quando_sem_chaves_daquele_tipo(self):
		municipio = MunicipioDescarga(codigo="3550308", nome="São Paulo", chaves_cte=[_chave("57")])

		infmun = montar_infdoc([municipio])["infDoc"]["infMunDescarga"][0]

		self.assertIn("infCTe", infmun)
		self.assertNotIn("infNFe", infmun)

	def test_varios_municipios_preserva_ordem(self):
		m1 = MunicipioDescarga(codigo="3550308", nome="São Paulo", chaves_nfe=[_chave("55", "000000001")])
		m2 = MunicipioDescarga(codigo="3304557", nome="Rio de Janeiro", chaves_nfe=[_chave("55", "000000002")])

		infmun = montar_infdoc([m1, m2])["infDoc"]["infMunDescarga"]

		self.assertEqual(infmun[0]["cMunDescarga"], "3550308")
		self.assertEqual(infmun[1]["cMunDescarga"], "3304557")

	def test_lista_vazia_de_municipios_levanta_erro(self):
		"""infMunDescarga não tem minOccurs=0 no XSD — pelo menos um é obrigatório."""
		with self.assertRaises(ValueError):
			montar_infdoc([])

	def test_recusa_chave_de_nfe_no_grupo_de_cte(self):
		municipio = MunicipioDescarga(codigo="3550308", nome="São Paulo", chaves_cte=[_chave("55")])

		with self.assertRaises(ChaveInvalida):
			montar_infdoc([municipio])

	def test_recusa_chave_de_cte_no_grupo_de_nfe(self):
		municipio = MunicipioDescarga(codigo="3550308", nome="São Paulo", chaves_nfe=[_chave("57")])

		with self.assertRaises(ChaveInvalida):
			montar_infdoc([municipio])


class AssinadorFalso:
	"""Duplo que satisfaz a porta `Assinador` sem certificado — registra o que recebeu.

	Mesmo duplo de `test_cte.py`/`test_nfe.py`, repetido aqui: um teste de `fiscal/mdfe.py`
	não deveria depender de um detalhe de teste de outro módulo."""

	def __init__(self):
		self.recebido: tuple[bytes, str] | None = None

	def assinar(self, xml: bytes, id_elemento: str):
		self.recebido = (xml, id_elemento)

		return MaterialAssinatura(
			digest="ZGlnZXN0", assinatura="YXNzaW5hdHVyYQ==", certificado="Y2VydA=="
		)


def _chave_mdfe() -> str:
	return _chave("58")


def _mdfe_minimo() -> dict:
	chave = _chave_mdfe()

	return {"MDFe": {"infMDFe": {"@Id": f"MDFe{chave}", "ide": {"cUF": "35"}}}}


class TestAssinarMdfe(unittest.TestCase):
	def setUp(self):
		self.mdfe = _mdfe_minimo()
		self.assinador = AssinadorFalso()
		self.assinado = assinar_mdfe(self.mdfe, self.assinador)

	def test_assina_o_id_do_infmdfe(self):
		self.assertEqual(self.assinador.recebido[1], self.mdfe["MDFe"]["infMDFe"]["@Id"])

	def test_id_assinado_usa_o_prefixo_mdfe(self):
		id_assinado = self.assinador.recebido[1]

		self.assertTrue(id_assinado.startswith("MDFe"))
		self.assertFalse(id_assinado.startswith("CTe"))
		self.assertFalse(id_assinado.startswith("NFe"))

	def test_signature_e_irma_de_infmdfe(self):
		"""Enveloped: Signature dentro de MDFe, ao lado de infMDFe — não dentro dele."""
		self.assertIn("infMDFe", self.assinado["MDFe"])
		self.assertIn("Signature", self.assinado["MDFe"])
		self.assertNotIn("Signature", self.assinado["MDFe"]["infMDFe"])

	def test_infmdfe_nao_muda_ao_assinar(self):
		self.assertEqual(self.assinado["MDFe"]["infMDFe"], self.mdfe["MDFe"]["infMDFe"])

	def test_documento_assinado_serializa(self):
		xml = para_xml(self.assinado)

		self.assertIn("<infMDFe", xml)
		self.assertIn("<Signature", xml)


def _identificacao(**kwargs) -> IdentificacaoMdfe:
	base = {
		"uf": "35",
		"tipo_emitente": EMITENTE_TRANSPORTADOR_CARGA_PROPRIA,
		"serie": "1",
		"numero": "1",
		"codigo_numerico": "12345678",
		"modal": MODAL_RODOVIARIO,
		"emissao": datetime(2026, 8, 31, 12, 0, 0),
		"uf_inicio": "SP",
		"uf_fim": "RJ",
		"municipios_carrega": [MunicipioCarrega(codigo="3550308", nome="São Paulo")],
	}
	base.update(kwargs)
	return IdentificacaoMdfe(**base)


class TestIdentificacaoMdfeValidar(unittest.TestCase):
	def test_tipo_emitente_invalido(self):
		with self.assertRaises(MdfeInvalido):
			_identificacao(tipo_emitente="9").validar()

	def test_tipo_transportador_invalido(self):
		with self.assertRaises(MdfeInvalido):
			_identificacao(tipo_transportador="9").validar()

	def test_tipo_transportador_vazio_e_valido(self):
		"""tpTransp é opcional no XSD -- string vazia não deve levantar erro."""
		_identificacao(tipo_transportador="").validar()

	def test_modal_invalido(self):
		with self.assertRaises(MdfeInvalido):
			_identificacao(modal="99").validar()

	def test_modal_do_cte_e_invalido_aqui(self):
		"""'01' (zero à esquerda) é válido no CT-e, não no MDF-e -- tabelas diferentes."""
		with self.assertRaises(MdfeInvalido):
			_identificacao(modal="01").validar()

	def test_sem_municipio_de_carrega_e_invalido(self):
		with self.assertRaises(MdfeInvalido):
			_identificacao(municipios_carrega=[]).validar()

	def test_valores_validos_nao_levantam(self):
		_identificacao().validar()


class TestMontarIde(unittest.TestCase):
	def test_campos_basicos(self):
		grupo = montar_ide(_identificacao(), _chave_mdfe())

		self.assertEqual(grupo["cUF"], "35")
		self.assertEqual(grupo["mod"], "58")
		self.assertEqual(grupo["modal"], MODAL_RODOVIARIO)
		self.assertNotIn("CFOP", grupo)
		self.assertNotIn("natOp", grupo)

	def test_cdv_e_o_digito_verificador_da_chave(self):
		chave = _chave_mdfe()

		grupo = montar_ide(_identificacao(), chave)

		self.assertEqual(grupo["cDV"], chave[-1])

	def test_chave_de_outro_modelo_levanta_erro(self):
		with self.assertRaises(MdfeInvalido):
			montar_ide(_identificacao(), _chave("57"))

	def test_cmdf_preenchido_com_zeros_a_esquerda(self):
		grupo = montar_ide(_identificacao(codigo_numerico="7"), _chave_mdfe())

		self.assertEqual(grupo["cMDF"], "00000007")

	def test_tptransp_ausente_quando_nao_informado(self):
		grupo = montar_ide(_identificacao(), _chave_mdfe())

		self.assertNotIn("tpTransp", grupo)

	def test_infmuncarrega_com_varios_municipios(self):
		municipios = [
			MunicipioCarrega(codigo="3550308", nome="São Paulo"),
			MunicipioCarrega(codigo="3304557", nome="Rio de Janeiro"),
		]

		grupo = montar_ide(_identificacao(municipios_carrega=municipios), _chave_mdfe())

		self.assertEqual(len(grupo["infMunCarrega"]), 2)
		self.assertEqual(grupo["infMunCarrega"][0], {"cMunCarrega": "3550308", "xMunCarrega": "São Paulo"})

	def test_infpercurso_ausente_quando_vazio(self):
		grupo = montar_ide(_identificacao(), _chave_mdfe())

		self.assertNotIn("infPercurso", grupo)

	def test_infpercurso_presente_quando_informado(self):
		grupo = montar_ide(_identificacao(ufs_percurso=["MG"]), _chave_mdfe())

		self.assertEqual(grupo["infPercurso"], [{"UFPer": "MG"}])

	def test_identificacao_invalida_propaga_erro(self):
		with self.assertRaises(MdfeInvalido):
			montar_ide(_identificacao(modal="99"), _chave_mdfe())


class TestMontarMdfe(unittest.TestCase):
	def test_envolve_infmdfe_com_namespace_e_id(self):
		chave = _chave_mdfe()
		infmdfe = montar_ide(_identificacao(), chave)

		mdfe = montar_mdfe(infmdfe, chave)

		self.assertEqual(mdfe["MDFe"]["@xmlns"], NAMESPACE_MDFE)
		self.assertEqual(mdfe["MDFe"]["infMDFe"]["@Id"], f"MDFe{chave}")

	def test_serializa_e_pode_ser_assinado(self):
		"""Ponta a ponta: montar_ide -> montar_mdfe -> assinar_mdfe, mesma prova já feita
		para o CT-e."""
		chave = _chave_mdfe()
		infmdfe = montar_ide(_identificacao(), chave)
		mdfe = montar_mdfe(infmdfe, chave)

		xml = para_xml(mdfe)
		self.assertIn("<infMDFe", xml)

		assinado = assinar_mdfe(mdfe, AssinadorFalso())

		self.assertIn("Signature", assinado["MDFe"])


if __name__ == "__main__":
	unittest.main()
