# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Leitura do XML de uma NF-e recebida.

A chave usada nos exemplos é **montada por `montar_chave`**, não digitada: o dígito
verificador precisa fechar, e uma chave inventada à mão faria o teste passar por um motivo
errado (ou falhar sem que o leitor tivesse defeito).

Teste-âncora: `test_le_as_duas_quantidades`. Comercial e tributável divergem sempre que a
unidade de venda não é a de tributação — caixa com 12, saca de 60 kg —, e um leitor que
devolvesse só a comercial faria o estoque bater e o SPED não, sem que nada acusasse.

Módulo puro: roda sem bench.
"""

import unittest
from decimal import Decimal

from erpnext_brasil.fiscal.documento.chave_acesso import montar_chave
from erpnext_brasil.fiscal.documento.leitura_nfe import NfeIlegivel, ler_nfe

CHAVE = montar_chave(
	uf="35",
	ano_mes="2607",
	cnpj="12345678000199",
	modelo="55",
	serie="1",
	numero="1",
	tipo_emissao="1",
	codigo_numerico="00000001",
)

NAMESPACE = "http://www.portalfiscal.inf.br/nfe"


def _xml(itens: str = "", com_protocolo: bool = True, chave: str = CHAVE) -> str:
	protocolo = (
		f"<protNFe><infProt><chNFe>{chave}</chNFe><nProt>135260000000001</nProt></infProt></protNFe>"
		if com_protocolo
		else ""
	)

	det = itens or (
		'<det nItem="1">'
		"<prod>"
		"<cProd>ABC-1</cProd><cEAN>7891234567890</cEAN><xProd>Parafuso sextavado</xProd>"
		"<NCM>73181500</NCM><CEST>0100100</CEST><CFOP>5102</CFOP>"
		"<uCom>CX</uCom><qCom>2.0000</qCom><vUnCom>150.0000000000</vUnCom><vProd>300.00</vProd>"
		"<uTrib>UN</uTrib><qTrib>24.0000</qTrib><vUnTrib>12.5000000000</vUnTrib>"
		"</prod>"
		"</det>"
	)

	return (
		f'<?xml version="1.0" encoding="UTF-8"?>'
		f'<nfeProc xmlns="{NAMESPACE}" versao="4.00">'
		f'<NFe><infNFe Id="NFe{chave}" versao="4.00">'
		f"<ide><nNF>1</nNF><serie>1</serie><mod>55</mod>"
		f"<dhEmi>2026-07-15T10:30:00-03:00</dhEmi><natOp>Venda de mercadoria</natOp></ide>"
		f"<emit><CNPJ>12345678000199</CNPJ><xNome>Fornecedor Ltda</xNome><IE>110042490114</IE>"
		f"<enderEmit><UF>SP</UF></enderEmit></emit>"
		f"<dest><CNPJ>98765432000188</CNPJ><xNome>Comprador SA</xNome>"
		f"<enderDest><UF>RO</UF></enderDest></dest>"
		f"{det}"
		f"<total><ICMSTot><vProd>300.00</vProd><vNF>318.00</vNF><vICMS>54.00</vICMS>"
		f"<vIPI>18.00</vIPI><vFrete>0.00</vFrete><vSeg>0.00</vSeg><vDesc>0.00</vDesc>"
		f"<vOutro>0.00</vOutro></ICMSTot></total>"
		f"</infNFe></NFe>{protocolo}</nfeProc>"
	)


class TestIdentificacao(unittest.TestCase):
	def test_le_a_chave_sem_o_prefixo_nfe(self):
		self.assertEqual(CHAVE, ler_nfe(_xml()).chave_acesso)

	def test_le_a_identificacao_da_nota(self):
		nota = ler_nfe(_xml())

		self.assertEqual("1", nota.numero)
		self.assertEqual("1", nota.serie)
		self.assertEqual("55", nota.modelo)
		self.assertEqual("Venda de mercadoria", nota.natureza_operacao)
		self.assertEqual("2026-07-15T10:30:00-03:00", nota.data_emissao)

	def test_le_o_protocolo_quando_ha(self):
		nota = ler_nfe(_xml())

		self.assertEqual("135260000000001", nota.protocolo)
		self.assertTrue(nota.tem_protocolo)

	def test_nfe_sem_protocolo_e_lida_mesmo_assim(self):
		"""O fornecedor manda `nfeProc`, mas intermediários repassam a `NFe` solta;
		recusá-la obrigaria o usuário a editar XML à mão."""
		nota = ler_nfe(_xml(com_protocolo=False))

		self.assertEqual(CHAVE, nota.chave_acesso)
		self.assertFalse(nota.tem_protocolo)


class TestPartes(unittest.TestCase):
	def test_le_emitente_e_destinatario(self):
		nota = ler_nfe(_xml())

		self.assertEqual("Fornecedor Ltda", nota.emitente.nome)
		self.assertEqual("12345678000199", nota.emitente.cnpj)
		self.assertEqual("SP", nota.emitente.uf)
		self.assertEqual("RO", nota.destinatario.uf)

	def test_o_documento_e_o_cnpj_ou_o_cpf(self):
		"""Pessoa física não tem CNPJ: o grupo é uma escolha entre os dois no leiaute."""
		nota = ler_nfe(_xml())

		self.assertEqual("12345678000199", nota.emitente.documento)

	def test_a_uf_vem_do_endereco_e_nao_da_raiz_da_parte(self):
		"""`UF` só existe dentro de `enderEmit`/`enderDest`; procurá-la um nível acima
		devolveria vazio."""
		self.assertTrue(ler_nfe(_xml()).emitente.uf)


class TestItens(unittest.TestCase):
	def test_le_um_item_com_os_campos_da_escrituracao(self):
		item = ler_nfe(_xml()).itens[0]

		self.assertEqual("ABC-1", item.codigo)
		self.assertEqual("Parafuso sextavado", item.descricao)
		self.assertEqual("73181500", item.ncm)
		self.assertEqual("5102", item.cfop)
		self.assertEqual("0100100", item.cest)
		self.assertEqual("7891234567890", item.ean)

	def test_o_numero_do_item_vem_do_atributo_nitem(self):
		"""`nItem` é atributo de `det`, não elemento filho — lê-lo como filho numeraria
		todos os itens como zero."""
		self.assertEqual(1, ler_nfe(_xml()).itens[0].numero)

	def test_le_as_duas_quantidades(self):
		"""Teste-âncora: comercial e tributável divergem, e devolver só uma faria o
		estoque bater e o SPED não."""
		item = ler_nfe(_xml()).itens[0]

		self.assertEqual(Decimal("2.0000"), item.quantidade)
		self.assertEqual("CX", item.unidade)
		self.assertEqual(Decimal("24.0000"), item.quantidade_tributavel)
		self.assertEqual("UN", item.unidade_tributavel)

	def test_os_valores_sao_decimal_e_nao_float(self):
		"""`Decimal(float("0.1"))` traz o erro binário junto, e três somas deslocam um
		centavo — que em nota fiscal é divergência de escrituração."""
		item = ler_nfe(_xml()).itens[0]

		self.assertIsInstance(item.valor_unitario, Decimal)
		self.assertEqual(Decimal("150.0000000000"), item.valor_unitario)
		self.assertEqual(Decimal("300.00"), item.valor_total)

	def test_le_varios_itens_na_ordem(self):
		dois = (
			'<det nItem="1"><prod><cProd>A</cProd><qCom>1.0000</qCom></prod></det>'
			'<det nItem="2"><prod><cProd>B</cProd><qCom>3.0000</qCom></prod></det>'
		)
		itens = ler_nfe(_xml(itens=dois)).itens

		self.assertEqual(2, len(itens))
		self.assertEqual(["A", "B"], [i.codigo for i in itens])
		self.assertEqual([1, 2], [i.numero for i in itens])

	def test_item_sem_campo_opcional_nao_quebra(self):
		"""CEST e EAN não são obrigatórios; ausência é vazio, não erro."""
		item = ler_nfe(_xml(itens='<det nItem="1"><prod><cProd>A</cProd></prod></det>')).itens[0]

		self.assertEqual("", item.cest)
		self.assertEqual(Decimal("0"), item.quantidade)


class TestTotais(unittest.TestCase):
	def test_le_o_grupo_icmstot(self):
		totais = ler_nfe(_xml()).totais

		self.assertEqual(Decimal("300.00"), totais.valor_produtos)
		self.assertEqual(Decimal("318.00"), totais.valor_nota)
		self.assertEqual(Decimal("54.00"), totais.valor_icms)
		self.assertEqual(Decimal("18.00"), totais.valor_ipi)

	def test_o_valor_da_nota_nao_e_o_dos_produtos(self):
		"""Confundir os dois é o erro que faz o contas a pagar nascer errado: o que se
		paga é `vNF`, com IPI e frete."""
		totais = ler_nfe(_xml()).totais

		self.assertNotEqual(totais.valor_produtos, totais.valor_nota)


class TestRecusas(unittest.TestCase):
	def test_xml_malformado_falha_alto(self):
		with self.assertRaises(NfeIlegivel):
			ler_nfe("<nfeProc><infNFe>")

	def test_xml_que_nao_e_nfe_falha_alto(self):
		with self.assertRaises(NfeIlegivel) as erro:
			ler_nfe('<?xml version="1.0"?><outraCoisa><a>1</a></outraCoisa>')

		self.assertIn("infNFe", str(erro.exception))

	def test_chave_com_digito_errado_e_recusada(self):
		"""XML truncado ou adulterado falha aqui, e não depois de a chave errada já ter
		sido gravada num `Purchase Invoice`."""
		errada = CHAVE[:-1] + ("0" if CHAVE[-1] != "0" else "1")

		with self.assertRaises(ValueError):
			ler_nfe(_xml(chave=errada))

	def test_valor_numerico_ilegivel_falha_alto(self):
		"""Devolver zero para um valor corrompido seria pior: zero é plausível."""
		quebrado = '<det nItem="1"><prod><cProd>A</cProd><vProd>trezentos</vProd></prod></det>'

		with self.assertRaises(NfeIlegivel):
			ler_nfe(_xml(itens=quebrado))


if __name__ == "__main__":
	unittest.main()
