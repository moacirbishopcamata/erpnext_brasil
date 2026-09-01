# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `fiscal/cte.py` — montagem dos grupos `ICMSUFFim` e `infDoc/infNFe` do CT-e."""

import unittest
from datetime import datetime
from decimal import Decimal

from erpnext_brasil.fiscal.cte import (
	MODAL_RODOVIARIO,
	NAMESPACE_CTE,
	TIPO_SERVICO_NORMAL,
	TOMADOR_DESTINATARIO,
	TOMADOR_OUTROS,
	CteInvalido,
	IdentificacaoCte,
	TomadorOutros,
	assinar_cte,
	montar_cte,
	montar_icms_uf_fim,
	montar_ide,
	montar_infnfe,
	montar_toma3,
	montar_toma4,
)
from erpnext_brasil.fiscal.documento.assinatura import MaterialAssinatura
from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, montar_chave
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.impostos.icms import calcular_difal


def _chave_nfe(numero: str = "000000001") -> str:
	return montar_chave(
		uf="35",
		ano_mes="2608",
		cnpj="11222333000181",
		modelo="55",
		serie="001",
		numero=numero,
		tipo_emissao="1",
		codigo_numerico="12345678",
	)


def _chave_cte(numero: str = "000000001") -> str:
	return montar_chave(
		uf="35",
		ano_mes="2608",
		cnpj="11222333000181",
		modelo="57",
		serie="001",
		numero=numero,
		tipo_emissao="1",
		codigo_numerico="12345678",
	)


class TestMontarIcmsUfFim(unittest.TestCase):
	def test_delega_para_calcular_difal(self):
		"""O grupo não reimplementa a partilha — os valores batem exatamente com uma
		chamada direta a `calcular_difal` com os mesmos parâmetros."""
		esperado = calcular_difal(
			valor_operacao=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			aliquota_fcp=Decimal("0.02"),
		)

		grupo = montar_icms_uf_fim(
			valor_prestacao=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			aliquota_fcp=Decimal("0.02"),
		)

		self.assertEqual(grupo["vBCUFFim"], str(esperado["base_destino"]))
		self.assertEqual(grupo["vICMSUFFim"], str(esperado["difal"]))
		self.assertEqual(grupo["vICMSUFIni"], str(esperado["icms_origem"]))
		self.assertEqual(grupo["vFCPUFFim"], str(esperado["fcp"]))

	def test_nomes_de_campo_sao_os_do_xsd_do_cte_nao_os_da_nfe(self):
		"""ICMSUFFim usa vBCUFFim/pICMSUFFim/vICMSUFFim — não vBCUFDest/pICMSUFDest/
		vICMSUFDest, que são os nomes do grupo homônimo da NF-e. Confirmado por leitura
		direta do XSD (docs/cte-estado.md), não por analogia."""
		grupo = montar_icms_uf_fim(
			valor_prestacao=Decimal("500.00"),
			aliquota_interestadual=Decimal("0.07"),
			aliquota_interna_destino=Decimal("0.19"),
		)

		for campo in ("vBCUFFim", "pFCPUFFim", "pICMSUFFim", "pICMSInter", "vFCPUFFim", "vICMSUFFim", "vICMSUFIni"):
			self.assertIn(campo, grupo)

		for campo_nfe in ("vBCUFDest", "pICMSUFDest", "vICMSUFDest"):
			self.assertNotIn(campo_nfe, grupo)

	def test_sem_fcp_devolve_zero(self):
		grupo = montar_icms_uf_fim(
			valor_prestacao=Decimal("200.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
		)

		self.assertEqual(grupo["vFCPUFFim"], "0.00")

	def test_base_unica_e_repassada(self):
		"""base_dupla=False muda o resultado de calcular_difal, e a mudança se propaga
		até o grupo montado — prova que o parâmetro não é ignorado silenciosamente."""
		com_base_dupla = montar_icms_uf_fim(
			valor_prestacao=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			base_dupla=True,
		)
		com_base_unica = montar_icms_uf_fim(
			valor_prestacao=Decimal("1000.00"),
			aliquota_interestadual=Decimal("0.12"),
			aliquota_interna_destino=Decimal("0.18"),
			base_dupla=False,
		)

		self.assertNotEqual(com_base_dupla["vBCUFFim"], com_base_unica["vBCUFFim"])


class TestMontarInfnfe(unittest.TestCase):
	def test_uma_chave(self):
		chave = _chave_nfe()

		grupo = montar_infnfe([chave])

		self.assertEqual(grupo, [{"chave": chave}])

	def test_varias_chaves_preserva_ordem(self):
		chave_1 = _chave_nfe("000000001")
		chave_2 = _chave_nfe("000000002")

		grupo = montar_infnfe([chave_1, chave_2])

		self.assertEqual(grupo, [{"chave": chave_1}, {"chave": chave_2}])

	def test_lista_vazia_devolve_lista_vazia(self):
		self.assertEqual(montar_infnfe([]), [])

	def test_chave_invalida_levanta_erro(self):
		with self.assertRaises(ChaveInvalida):
			montar_infnfe(["0" * 43 + "9"])  # DV errado

	def test_recusa_chave_que_nao_e_de_nfe(self):
		"""infDoc/infNFe só aceita NF-e (modelo 55) — colar por engano a chave de outro
		CT-e (modelo 57) tem que falhar aqui, não só na rejeição da SEFAZ."""
		with self.assertRaises(ChaveInvalida):
			montar_infnfe([_chave_cte()])


class TestMontarToma3(unittest.TestCase):
	def test_papel_valido(self):
		self.assertEqual(montar_toma3(TOMADOR_DESTINATARIO), {"toma3": {"toma": TOMADOR_DESTINATARIO}})

	def test_papel_invalido_levanta_erro(self):
		with self.assertRaises(CteInvalido):
			montar_toma3("9")

	def test_nao_aceita_o_codigo_de_toma4(self):
		"""'4' (Outros) pertence a toma4, não a toma3 — são grupos mutuamente exclusivos
		no XSD, cada um com seu próprio conjunto de valores válidos para `toma`."""
		with self.assertRaises(CteInvalido):
			montar_toma3(TOMADOR_OUTROS)


def _tomador_outros(**kwargs) -> TomadorOutros:
	base = {
		"nome": "Transportes Além Ltda",
		"cnpj_cpf": "11222333000181",
		"endereco": {"xLgr": "Rua Teste", "nro": "100", "xMun": "São Paulo", "UF": "SP"},
	}
	base.update(kwargs)
	return TomadorOutros(**base)


class TestMontarToma4(unittest.TestCase):
	def test_campos_obrigatorios(self):
		grupo = montar_toma4(_tomador_outros())["toma4"]

		self.assertEqual(grupo["toma"], TOMADOR_OUTROS)
		self.assertEqual(grupo["xNome"], "Transportes Além Ltda")
		self.assertIn("CNPJ", grupo)
		self.assertIn("enderToma", grupo)

	def test_ordem_dos_campos_segue_o_xsd(self):
		"""toma, CNPJ/CPF, IE, xNome, xFant, fone, enderToma, email — xs:sequence não é
		ordem livre; embaralhar produziria XML que o schema rejeita."""
		grupo = montar_toma4(
			_tomador_outros(inscricao_estadual="123456789", nome_fantasia="Além", fone="11999999999")
		)["toma4"]

		self.assertEqual(
			list(grupo.keys()),
			["toma", "CNPJ", "IE", "xNome", "xFant", "fone", "enderToma"],
		)

	def test_cpf_quando_documento_tem_11_digitos(self):
		grupo = montar_toma4(_tomador_outros(cnpj_cpf="11144477735"))["toma4"]

		self.assertIn("CPF", grupo)
		self.assertNotIn("CNPJ", grupo)

	def test_documento_invalido_levanta_erro(self):
		with self.assertRaises(CteInvalido):
			montar_toma4(_tomador_outros(cnpj_cpf="123"))

	def test_nome_vazio_levanta_erro(self):
		with self.assertRaises(CteInvalido):
			montar_toma4(_tomador_outros(nome=""))

	def test_sem_endereco_levanta_erro(self):
		"""enderToma é obrigatório no XSD (sem minOccurs=0) — diferente de xFant/fone/
		email, que são opcionais."""
		with self.assertRaises(CteInvalido):
			montar_toma4(_tomador_outros(endereco={}))

	def test_email_e_opcional(self):
		sem_email = montar_toma4(_tomador_outros())["toma4"]
		com_email = montar_toma4(_tomador_outros(email="contato@alem.com.br"))["toma4"]

		self.assertNotIn("email", sem_email)
		self.assertEqual(com_email["email"], "contato@alem.com.br")


def _identificacao(**kwargs) -> IdentificacaoCte:
	base = {
		"uf": "35",
		"cfop": "5352",
		"natureza_operacao": "Prestação de serviço de transporte",
		"serie": "1",
		"numero": "1",
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


class TestIdentificacaoCteValidar(unittest.TestCase):
	def test_modal_invalido(self):
		with self.assertRaises(CteInvalido):
			_identificacao(modal="99").validar()

	def test_tipo_servico_invalido(self):
		with self.assertRaises(CteInvalido):
			_identificacao(tipo_servico="9").validar()

	def test_tipo_cte_invalido(self):
		with self.assertRaises(CteInvalido):
			_identificacao(tipo_cte="2").validar()

	def test_retira_invalido(self):
		with self.assertRaises(CteInvalido):
			_identificacao(retira="9").validar()

	def test_indicador_ie_tomador_invalido(self):
		with self.assertRaises(CteInvalido):
			_identificacao(indicador_ie_tomador="0").validar()

	def test_valores_validos_nao_levantam(self):
		_identificacao().validar()


class TestMontarIde(unittest.TestCase):
	def test_campos_basicos(self):
		grupo = montar_ide(_identificacao(), montar_toma3(TOMADOR_DESTINATARIO))

		self.assertEqual(grupo["cUF"], "35")
		self.assertEqual(grupo["CFOP"], "5352")
		self.assertEqual(grupo["mod"], "57")
		self.assertEqual(grupo["modal"], MODAL_RODOVIARIO)

	def test_cct_preenchido_com_zeros_a_esquerda(self):
		grupo = montar_ide(_identificacao(codigo_numerico="7"), montar_toma3(TOMADOR_DESTINATARIO))

		self.assertEqual(grupo["cCT"], "00000007")

	def test_indieToma_vem_antes_do_grupo_do_tomador(self):
		grupo = montar_ide(_identificacao(), montar_toma3(TOMADOR_DESTINATARIO))
		chaves = list(grupo.keys())

		self.assertLess(chaves.index("indIEToma"), chaves.index("toma3"))

	def test_aceita_toma3(self):
		grupo = montar_ide(_identificacao(), montar_toma3(TOMADOR_DESTINATARIO))

		self.assertIn("toma3", grupo)
		self.assertNotIn("toma4", grupo)

	def test_aceita_toma4(self):
		tomador = TomadorOutros(
			nome="Outros Ltda",
			cnpj_cpf="11222333000181",
			endereco={"xLgr": "Rua X", "xMun": "São Paulo", "UF": "SP"},
		)
		grupo = montar_ide(_identificacao(), montar_toma4(tomador))

		self.assertIn("toma4", grupo)
		self.assertNotIn("toma3", grupo)

	def test_xdetretira_so_aparece_quando_preenchido(self):
		sem_detalhe = montar_ide(_identificacao(), montar_toma3(TOMADOR_DESTINATARIO))
		com_detalhe = montar_ide(
			_identificacao(detalhes_retira="Retirar na filial 2"), montar_toma3(TOMADOR_DESTINATARIO)
		)

		self.assertNotIn("xDetRetira", sem_detalhe)
		self.assertEqual(com_detalhe["xDetRetira"], "Retirar na filial 2")

	def test_identificacao_invalida_propaga_erro(self):
		with self.assertRaises(CteInvalido):
			montar_ide(_identificacao(modal="99"), montar_toma3(TOMADOR_DESTINATARIO))


class TestMontarCte(unittest.TestCase):
	def test_envolve_infcte_com_namespace_e_id(self):
		infcte = montar_ide(_identificacao(), montar_toma3(TOMADOR_DESTINATARIO))
		chave = _chave_cte()

		cte = montar_cte(infcte, chave)

		self.assertEqual(cte["CTe"]["@xmlns"], NAMESPACE_CTE)
		self.assertEqual(cte["CTe"]["infCte"]["@Id"], f"CTe{chave}")

	def test_infcte_preservado(self):
		infcte = montar_ide(_identificacao(), montar_toma3(TOMADOR_DESTINATARIO))
		chave = _chave_cte()

		cte = montar_cte(infcte, chave)

		for k, v in infcte.items():
			self.assertEqual(cte["CTe"]["infCte"][k], v)

	def test_serializa_e_pode_ser_assinado(self):
		"""Ponta a ponta: montar_ide -> montar_cte -> assinar_cte, mesma costura de
		fiscal.documento.nfe, provando que as peças soltas do CT-e realmente se encaixam."""
		infcte = montar_ide(_identificacao(), montar_toma3(TOMADOR_DESTINATARIO))
		chave = _chave_cte()
		cte = montar_cte(infcte, chave)

		xml = para_xml(cte)
		self.assertIn("<infCte", xml)

		assinador = AssinadorFalso()
		assinado = assinar_cte(cte, assinador)

		self.assertIn("Signature", assinado["CTe"])


class AssinadorFalso:
	"""Duplo que satisfaz a porta `Assinador` sem certificado — registra o que recebeu.

	Mesmo duplo de `test_nfe.py`, repetido aqui em vez de importado: um teste de
	`fiscal/cte.py` não deveria depender de um detalhe de teste de `fiscal/documento/`."""

	def __init__(self):
		self.recebido: tuple[bytes, str] | None = None

	def assinar(self, xml: bytes, id_elemento: str):
		self.recebido = (xml, id_elemento)

		return MaterialAssinatura(
			digest="ZGlnZXN0", assinatura="YXNzaW5hdHVyYQ==", certificado="Y2VydA=="
		)


def _cte_minimo() -> dict:
	chave = _chave_cte()

	return {"CTe": {"infCte": {"@Id": f"CTe{chave}", "ide": {"cUF": "35"}}}}


class TestAssinarCte(unittest.TestCase):
	def setUp(self):
		self.cte = _cte_minimo()
		self.assinador = AssinadorFalso()
		self.assinado = assinar_cte(self.cte, self.assinador)

	def test_assina_o_id_do_infcte(self):
		"""O que se assina é o Id de infCte — mesmo elemento que o XSD identifica como
		alvo da assinatura (`infCte/@Id`, padrão `CTe[0-9]{44}`)."""
		self.assertEqual(self.assinador.recebido[1], self.cte["CTe"]["infCte"]["@Id"])

	def test_id_assinado_usa_o_prefixo_cte_nao_nfe(self):
		id_assinado = self.assinador.recebido[1]

		self.assertTrue(id_assinado.startswith("CTe"))
		self.assertFalse(id_assinado.startswith("NFe"))

	def test_signature_e_irma_de_infcte(self):
		"""Enveloped: Signature dentro de CTe, ao lado de infCte — não dentro dele."""
		self.assertIn("infCte", self.assinado["CTe"])
		self.assertIn("Signature", self.assinado["CTe"])
		self.assertNotIn("Signature", self.assinado["CTe"]["infCte"])

	def test_infcte_nao_muda_ao_assinar(self):
		self.assertEqual(self.assinado["CTe"]["infCte"], self.cte["CTe"]["infCte"])

	def test_documento_assinado_serializa(self):
		xml = para_xml(self.assinado)

		self.assertIn("<infCte", xml)
		self.assertIn("<Signature", xml)


if __name__ == "__main__":
	unittest.main()
