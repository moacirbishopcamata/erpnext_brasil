# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes reais (bench) do alerta de validade do certificado A1.

O que só o bench prova
------------------------------
A cadeia inteira: `Company` → anexo `.pfx` → senha **criptografada** pelo Frappe →
`cryptography` lê a validade → a regra pura decide se alerta. A suíte pura testa a regra;
tudo antes dela é banco, arquivo e criptografia, e nenhum desses existe fora de um site.

O certificado é **gerado no teste**, autoassinado, com validade escolhida. Não há `.pfx` de
verdade no repositório — nem deveria: certificado com chave privada em repositório é o tipo
de arquivo que vaza.

Teste-âncora: `test_certificado_quebrado_nao_cala_o_alerta_das_outras_empresas`
--------------------------------------------------------------------------------------------
Num site multiempresa, uma empresa com anexo corrompido, senha trocada ou arquivo removido
**não pode** impedir que as demais sejam avaliadas. O `except` amplo do módulo existe para
isso, e amplo demais é fácil de escrever errado: um `return` no lugar de um `continue` faria
a primeira falha calar todas as seguintes — e ninguém receberia aviso de vencimento até o
certificado expirar de fato.

Como rodar
-----------------
    bench --site v16.localhost run-tests \\
        --module erpnext_brasil.tests_bench.test_alerta_certificado
"""

import datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext_brasil.integracao.alerta_certificado import verificar_validade_dos_certificados
from erpnext_brasil.tests_bench import test_cfop_sugestao

MODULOS_COBERTOS = ("alerta_certificado",)
"""Os módulos de `integracao/` que este arquivo exercita — **declarados**, não inferidos.

Lido por `scripts/cobertura_de_bench.py`. Ver a explicação em `cobertura_de_bench.py`:
inferir por nome de arquivo ou por import erra em direções opostas.
"""

EMPRESA_BOA = "_Teste Certificado Bom"
EMPRESA_QUEBRADA = "_Teste Certificado Quebrado"
SENHA = "senha-de-teste"
DIAS_ATE_VENCER = 20


def _pfx(dias: int, senha: str) -> bytes:
	"""Gera um `.pfx` autoassinado que vence em `dias`.

	Usa `cryptography`, que já é dependência do app (`assinador_local`). Gerar em vez de
	versionar mantém o teste independente do calendário: um arquivo fixo venceria, e o
	teste passaria a falhar por motivo que não é o dele.
	"""
	from cryptography import x509
	from cryptography.hazmat.primitives import hashes, serialization
	from cryptography.hazmat.primitives.asymmetric import rsa
	from cryptography.hazmat.primitives.serialization import pkcs12

	chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	nome = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "Teste A1")])
	agora = datetime.datetime.now(datetime.UTC)

	certificado = (
		x509.CertificateBuilder()
		.subject_name(nome)
		.issuer_name(nome)
		.public_key(chave.public_key())
		.serial_number(x509.random_serial_number())
		.not_valid_before(agora - datetime.timedelta(days=1))
		.not_valid_after(agora + datetime.timedelta(days=dias))
		.sign(chave, hashes.SHA256())
	)

	return pkcs12.serialize_key_and_certificates(
		name=b"teste",
		key=chave,
		cert=certificado,
		cas=None,
		encryption_algorithm=serialization.BestAvailableEncryption(senha.encode()),
	)


class TestAlertaDeCertificado(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		test_cfop_sugestao.TestSugestaoDeCfop.setUpClass()

		cls._empresa(EMPRESA_BOA, "_TCB", "11.444.777/0001-61", _pfx(DIAS_ATE_VENCER, SENHA))
		cls._empresa(EMPRESA_QUEBRADA, "_TCQ", "34.028.316/0001-03", b"isto nao e um pfx")

		frappe.db.commit()

	@classmethod
	def _empresa(cls, nome: str, abreviacao: str, cnpj: str, conteudo: bytes) -> None:
		if not frappe.db.exists("Company", nome):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": nome,
					"abbr": abreviacao,
					"default_currency": "BRL",
					"country": "Brazil",
					"tax_id": cnpj,
				}
			).insert(ignore_permissions=True)

		doc = frappe.get_doc("Company", nome)

		# ⚠️ O certificado é **regerado e reanexado a cada execução**, não só na primeira.
		# `_pfx` dá validade relativa a "agora" (`DIAS_ATE_VENCER`); guardar o anexo da primeira
		# execução congelava essa validade, e semanas depois o teste esperava 20 dias de um
		# certificado que já vencera (falhou em 2026-10-03: `20 != -5`). Mesma armadilha do
		# "setup idempotente por existência" de `test_cfop_sugestao`, agora com o relógio.
		anterior = doc.get("br_certificado_a1")

		if anterior:
			for antigo in frappe.get_all("File", filters={"file_url": anterior}, pluck="name"):
				frappe.delete_doc("File", antigo, force=True, ignore_permissions=True)

		arquivo = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{abreviacao}.pfx",
				"attached_to_doctype": "Company",
				"attached_to_name": nome,
				"is_private": 1,
				"content": conteudo,
			}
		).insert(ignore_permissions=True)

		doc.br_certificado_a1 = arquivo.file_url

		# ⚠️ `br_senha_certificado_a1` é `Password`: o Frappe criptografa no save e só
		# devolve por `get_password`. Gravar direto na coluna guardaria texto puro, e o
		# `carregar_certificado_da_empresa` leria lixo.
		doc.br_senha_certificado_a1 = SENHA
		doc.save(ignore_permissions=True)

	def _avaliacao_de(self, empresa: str, resultado: list[dict]) -> dict | None:
		"""⚠️ As chaves do retorno são **pt-BR** (`empresa`, `dias_restantes`), como todo o
		app. Escrevi este ajudante com `company`/`dias` na primeira tentativa e os quatro
		testes falharam com "unexpectedly None" — sintoma que aponta para a varredura não ter
		achado a empresa, e não para o nome da chave."""
		for item in resultado:
			if item.get("empresa") == empresa:
				return item

		return None

	def test_le_a_validade_do_certificado_atraves_da_senha_criptografada(self):
		"""A cadeia inteira: anexo lido do disco, senha decifrada pelo Frappe, validade
		extraída pelo `cryptography`."""
		avaliacao = self._avaliacao_de(EMPRESA_BOA, verificar_validade_dos_certificados())

		self.assertIsNotNone(avaliacao, f"{EMPRESA_BOA} não foi avaliada")
		self.assertAlmostEqual(DIAS_ATE_VENCER, avaliacao["dias_restantes"], delta=1)

	def test_certificado_quebrado_nao_cala_o_alerta_das_outras_empresas(self):
		"""Teste-âncora. Um `return` no lugar do `continue` faria a primeira falha calar
		todas as seguintes, e ninguém receberia aviso até o certificado expirar de fato."""
		resultado = verificar_validade_dos_certificados()

		self.assertIsNone(
			self._avaliacao_de(EMPRESA_QUEBRADA, resultado),
			"a empresa com certificado ilegível não deveria ser avaliada",
		)
		self.assertIsNotNone(
			self._avaliacao_de(EMPRESA_BOA, resultado),
			"a falha de uma empresa calou a avaliação das outras",
		)

	def test_a_data_de_hoje_e_injetavel(self):
		"""`hoje` é parâmetro para que o teste possa olhar o futuro sem esperar por ele.

		Vinte dias adiante do vencimento, os dias restantes ficam negativos — e o alerta
		precisa continuar avaliando, não sumir: certificado vencido é exatamente quando o
		aviso mais importa.
		"""
		muito_depois = datetime.date.today() + datetime.timedelta(days=DIAS_ATE_VENCER + 20)
		avaliacao = self._avaliacao_de(EMPRESA_BOA, verificar_validade_dos_certificados(hoje=muito_depois))

		self.assertIsNotNone(avaliacao)
		self.assertLess(avaliacao["dias_restantes"], 0)

	def test_empresa_sem_certificado_nao_entra_na_varredura(self):
		"""A maioria das empresas de um site não emite nota. Avaliá-las produziria erro de
		leitura para todas, todo dia, no `Error Log`."""
		nomes = {item["empresa"] for item in verificar_validade_dos_certificados()}

		self.assertNotIn(test_cfop_sugestao.MATRIZ, nomes)
