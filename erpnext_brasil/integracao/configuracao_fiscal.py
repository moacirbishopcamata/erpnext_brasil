# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Leitura das configurações fiscais da `Company` — um lugar só para "o que esta
empresa tem cadastrado" que os documentos eletrônicos precisam.

Completa a auditoria de configurações pedida pelo usuário ("existem mais configurações
a serem criadas?"), depois de `certificado_a1.py` (certificado/ambiente SEFAZ) e
`efd_dados_cadastrais.py` (cadastros da EFD). Aqui entram as que sobraram, cada uma com
consumidor real no código puro:

| Configuração | Quem consome |
|---|---|
| CSC + CSCId da NFC-e | `fiscal.documento.qrcode_nfce.montar_qrcode_online` |
| RNTRC | `fiscal.cte_rodoviario` e `fiscal.mdfe_rodoviario` |
| Série por modelo | `fiscal.documento.chave_acesso.montar_chave` e o transporte |
| Classificação tributária, transmissor e ambiente do eSocial | `folha.esocial_s1000` e `folha.esocial_lote` |

O CSC é segredo, e por isso é `Password`
------------------------------------------------
O Código de Segurança do Contribuinte é um segredo compartilhado com a SEFAZ — participa
só do hash do QR Code e **nunca** aparece na URL impressa no cupom
(`docs/nfce-qrcode.md`). Guardá-lo em `Data` o deixaria legível em tela, em export e no
log de alteração do documento; `Password` faz o Frappe criptografar, mesmo tratamento já
dado à senha do certificado A1. Foi o campo que a auditoria mais fez falta: sem ele,
emitir NFC-e exigiria datilografar o segredo a cada emissão.

O ambiente do eSocial é campo separado do ambiente da SEFAZ — de propósito
------------------------------------------------------------------------------------
`Company.br_ambiente_sefaz` é produção/homologação; o eSocial tem domínio próprio
(produção/produção restrita, `tpAmb` 1/2). Não são o mesmo conceito com nomes
diferentes, e um site pode estar homologando NF-e enquanto já opera em produção no
eSocial — reaproveitar um campo para os dois obrigaria os dois a andarem juntos, o que a
realidade não garante. Mesma lição que `esocial_consulta.py` já tinha registrado sobre
os três domínios distintos de "ambiente" no eSocial.

Séries: cadastro, porque o transporte já as exige como parâmetro
------------------------------------------------------------------------
`transporte_sefaz.inutilizar` e `chave_acesso.montar_chave` recebem `serie` como
parâmetro. A série é estável por estabelecimento (não muda a cada emissão), então é
cadastro — sem isso, quem emite datilografaria a mesma série toda vez, com o risco de
digitar diferente e gerar chave de acesso divergente.

O que deliberadamente **não** virou configuração
--------------------------------------------------------
- **Dados bancários do boleto** (carteira, convênio, código do cedente): `boleto.py`
  não modela `campo_livre` — cada banco tem o seu layout, e o módulo recebe os 25
  caracteres já prontos. Criar campos de cadastro sem nenhum código que os leia seria
  estrutura sem uso, o mesmo critério que manteve `0005`/`0100` fora do Bloco 0.
- **`verProc`** (versão do processo emissor, no eSocial e na NF-e): é a versão **deste
  app**, não do cliente — sai de `erpnext_brasil.__version__`, e virar campo editável
  permitiria declarar uma versão que não é a que gerou o arquivo.

Sem teste dedicado — depende do Frappe (mesma disciplina dos módulos irmãos).
"""

import frappe

from erpnext_brasil.setup.custom_fields import SERIE_POR_MODELO

__all__ = [
	"ConfiguracaoFiscalAusente",
	"ambiente_esocial_da_empresa",
	"classificacao_tributaria_esocial",
	"csc_da_empresa",
	"rntrc_da_empresa",
	"serie_padrao",
	"transmissor_esocial_da_empresa",
]

AMBIENTE_ESOCIAL_PRODUCAO = 1
AMBIENTE_ESOCIAL_PRODUCAO_RESTRITA = 2

# `SERIE_POR_MODELO` vem de `setup/custom_fields.py`, onde as definições de campo moram
# — uma fonte só para "qual campo guarda a série de qual modelo", conferida pela suíte
# pura (que não consegue importar este módulo, porque ele depende do Frappe).


class ConfiguracaoFiscalAusente(ValueError):
	"""Configuração obrigatória que a `Company` não tem preenchida.

	Erro explícito em vez de devolver vazio: um QR Code montado com CSC vazio é aceito
	pelo montador e recusado pelo consumidor que escaneia — falha longe da causa.
	"""


def csc_da_empresa(company: str) -> tuple[str, str]:
	"""Devolve `(csc_id, csc)` da `Company` para o QR Code da NFC-e.

	Levanta `ConfiguracaoFiscalAusente` se qualquer um faltar — os dois são
	inseparáveis: o `csc_id` diz à SEFAZ qual CSC foi usado no hash, e sem o `csc` não
	há hash. Ter só um dos dois é configuração pela metade, não estado válido.
	"""
	documento = frappe.get_doc("Company", company)

	csc_id = (documento.get("br_csc_id_nfce") or "").strip()
	csc = (documento.get_password("br_csc_nfce", raise_exception=False) or "").strip()

	if not csc_id or not csc:
		faltando = [
			nome
			for nome, valor in (("CSCId", csc_id), ("CSC", csc))
			if not valor
		]

		raise ConfiguracaoFiscalAusente(
			f"Company {company!r} não tem {' e '.join(faltando)} configurado(s) — "
			"sem os dois não há como montar o QR Code da NFC-e"
		)

	return csc_id, csc


def rntrc_da_empresa(company: str) -> str:
	"""RNTRC da empresa, para o modal rodoviário do CT-e/MDF-e.

	Devolve string vazia quando não configurado — diferente do CSC, aqui a ausência é
	estado válido: quem não é transportador não tem RNTRC, e o campo só é exigido no
	documento de transporte (onde `cte_rodoviario.validar_rntrc` reclama, com a
	mensagem certa para aquele contexto).
	"""
	return (frappe.db.get_value("Company", company, "br_rntrc") or "").strip()


def serie_padrao(company: str, modelo: str) -> str:
	"""Série cadastrada para o modelo de documento (`"55"`, `"65"`, `"57"`, `"58"`).

	Modelo desconhecido é erro de programação, não de configuração — por isso levanta
	`ValueError` em vez de devolver vazio.
	"""
	campo = SERIE_POR_MODELO.get(modelo)

	if campo is None:
		raise ValueError(
			f"modelo {modelo!r} não tem série cadastrável — conhecidos: {sorted(SERIE_POR_MODELO)}"
		)

	return (frappe.db.get_value("Company", company, campo) or "").strip()


def ambiente_esocial_da_empresa(company: str) -> int:
	"""`tpAmb` do eSocial: `1` (produção) ou `2` (produção restrita).

	Só o valor exato "Produção" ativa produção; qualquer outra coisa — inclusive campo
	vazio ou erro de digitação — resolve para produção restrita, o lado seguro. Mesma
	regra (e mesma razão) de `certificado_a1.ambiente_sefaz_da_empresa`.
	"""
	configurado = frappe.db.get_value("Company", company, "br_esocial_ambiente")

	if configurado == "Produção":
		return AMBIENTE_ESOCIAL_PRODUCAO

	return AMBIENTE_ESOCIAL_PRODUCAO_RESTRITA


def transmissor_esocial_da_empresa(company: str) -> str:
	"""CNPJ de quem transmite o lote do eSocial.

	Vazio no cadastro significa "o próprio empregador transmite", e por isso devolve o
	`tax_id` da própria `Company` — assim quem chama nunca precisa tratar o caso
	comum como exceção.
	"""
	dados = frappe.db.get_value(
		"Company", company, ["br_esocial_transmissor", "tax_id"], as_dict=True
	)

	transmissor = (dados.get("br_esocial_transmissor") or "").strip()

	return transmissor or (dados.get("tax_id") or "").strip()


def classificacao_tributaria_esocial(company: str) -> str:
	"""`classTrib` do S-1000 (Tabela 08 do eSocial), 2 dígitos.

	Devolve vazio quando não configurado; o `InfoCadastro` do S-1000 é que recusa, com
	a mensagem específica daquele registro — não cabe a este módulo duplicar a
	validação do domínio.
	"""
	return (
		frappe.db.get_value("Company", company, "br_esocial_classificacao_tributaria") or ""
	).strip()
