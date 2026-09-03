# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Verifica se o cadastro está pronto para gerar a EFD — e diz exatamente o que falta.

Por que existe: descobrir o que falta no fim é caro
------------------------------------------------------------
Os registros da EFD recusam dado ausente um a um, com a mensagem certa daquele campo —
mas só na hora da montagem, e a montagem para no primeiro erro. Quem tem mil itens
cadastrados descobre um problema por rodada: corrige o item, roda de novo, descobre o
próximo. Esta verificação inverte isso: varre tudo antes e devolve a **lista completa**
do que impede a geração.

Não duplica validação: consulta as mesmas regras
--------------------------------------------------------
O que é obrigatório aqui é exatamente o que `efd_bloco_0`/`efd_bloco_c` já exigem —
esta camada não inventa exigência nova, só antecipa a descoberta. Onde o registro aceita
vazio ("obrigatório quando houver"), aqui também não vira pendência: alertar sobre campo
opcional treinaria o usuário a ignorar o alerta, que é como um alerta morre.

Puro: recebe dicionários simples
----------------------------------------
Não conhece `Company`, `Item` nem Frappe — recebe o que já foi lido. Assim a regra do
que é pendência fica testável sem bench, e a camada de integração
(`integracao/prontidao_efd.py`) só faz a leitura.
"""

from dataclasses import dataclass

from erpnext_brasil.contabil.efd_bloco_0 import PERFIS, TIPOS_ITEM

__all__ = [
	"GRAVIDADE_ATENCAO",
	"GRAVIDADE_BLOQUEIA",
	"Pendencia",
	"verificar_empresa",
	"verificar_item",
]

GRAVIDADE_BLOQUEIA = "bloqueia"
"""Sem isto o arquivo não pode ser gerado."""

GRAVIDADE_ATENCAO = "atencao"
"""O arquivo sai, mas provavelmente sai errado ou incompleto."""


@dataclass(frozen=True)
class Pendencia:
	"""Uma coisa que falta, dita para quem vai resolver — não para quem escreveu o código.

	`onde` é o caminho que o usuário percorre na tela (ex.: "Empresa > Dados Fiscais"),
	e não o nome interno do campo: quem lê o alerta precisa saber para onde ir.
	"""

	campo: str
	onde: str
	motivo: str
	gravidade: str = GRAVIDADE_BLOQUEIA

	@property
	def bloqueia(self) -> bool:
		return self.gravidade == GRAVIDADE_BLOQUEIA


def verificar_empresa(dados: dict) -> list[Pendencia]:
	"""Pendências no cadastro da empresa que impedem gerar a EFD.

	`dados` são os campos já lidos da `Company` e do `Address` fiscal — as chaves
	seguem os nomes dos campos, para que a integração não precise traduzir nada.
	"""
	pendencias = []

	if not (dados.get("tax_id") or "").strip():
		pendencias.append(
			Pendencia(
				campo="CNPJ",
				onde="Empresa > Dados Fiscais",
				motivo="o registro 0000 identifica a entidade por CNPJ ou CPF",
			)
		)

	if not (dados.get("inscricao_estadual") or "").strip():
		pendencias.append(
			Pendencia(
				campo="Inscrição Estadual",
				onde="Empresa > Dados Fiscais",
				motivo="campo IE do registro 0000, obrigatório",
			)
		)

	perfil = (dados.get("br_efd_perfil") or "").strip()

	if perfil not in PERFIS:
		pendencias.append(
			Pendencia(
				campo="Perfil de Apresentação",
				onde="Empresa > EFD-ICMS/IPI",
				motivo=(
					"campo IND_PERFIL do registro 0000. Quem define é a SEFAZ do seu "
					f"estado — um de {sorted(PERFIS)}"
				),
			)
		)

	if not (dados.get("br_efd_atividade") or "").strip():
		pendencias.append(
			Pendencia(
				campo="Tipo de Atividade",
				onde="Empresa > EFD-ICMS/IPI",
				motivo="campo IND_ATIV do registro 0000, obrigatório",
			)
		)

	if not (dados.get("br_efd_versao_leiaute") or "").strip():
		pendencias.append(
			Pendencia(
				campo="Versão do Leiaute",
				onde="Empresa > EFD-ICMS/IPI",
				motivo=(
					"campo COD_VER do registro 0000. Vale a versão vigente na data final "
					"da escrituração, por isso não tem padrão fixo"
				),
			)
		)

	codigo_municipio = (dados.get("codigo_municipio_ibge") or "").strip()

	if len(codigo_municipio) != 7 or not codigo_municipio.isdigit():
		pendencias.append(
			Pendencia(
				campo="Código do Município (IBGE)",
				onde="Endereço fiscal da empresa > Dados Fiscais",
				motivo="campo COD_MUN do registro 0000, 7 dígitos da tabela IBGE",
			)
		)

	if not (dados.get("state") or "").strip():
		pendencias.append(
			Pendencia(
				campo="UF",
				onde="Endereço fiscal da empresa",
				motivo="campo UF do registro 0000",
			)
		)

	return pendencias


def verificar_item(dados: dict) -> list[Pendencia]:
	"""Pendências no cadastro de um item que impedem gerar o registro 0200.

	`dados` traz `item_code`/`stock_uom`/`ncm`/`br_efd_tipo_item`, já lidos.
	"""
	pendencias = []
	item = dados.get("item_code") or "?"

	tipo = (dados.get("br_efd_tipo_item") or "").split(" - ", 1)[0].strip()

	if tipo not in TIPOS_ITEM:
		pendencias.append(
			Pendencia(
				campo="Tipo do Item (EFD)",
				onde=f"Item {item} > Dados Fiscais",
				motivo="campo TIPO_ITEM do registro 0200, obrigatório e sem valor padrão",
			)
		)

	if not (dados.get("stock_uom") or "").strip():
		pendencias.append(
			Pendencia(
				campo="Unidade de Medida",
				onde=f"Item {item}",
				motivo="campo UNID_INV do registro 0200, e precisa existir num registro 0190",
			)
		)

	ncm = "".join(c for c in (dados.get("ncm") or "") if c.isdigit())

	if ncm and len(ncm) != 8:
		pendencias.append(
			Pendencia(
				campo="NCM",
				onde=f"Item {item} > Dados Fiscais",
				motivo=f"o NCM tem de ter 8 dígitos; este tem {len(ncm)}",
			)
		)
	elif not ncm:
		# Atenção, não bloqueio: o layout torna o COD_NCM obrigatório para indústria e
		# equiparada, e para quem gera crédito/débito de IPI — não para todo mundo.
		# Tratar como bloqueio recusaria um cadastro que o Fisco aceita.
		pendencias.append(
			Pendencia(
				campo="NCM",
				onde=f"Item {item} > Dados Fiscais",
				motivo=(
					"obrigatório para indústria e equiparada, e sempre que houver crédito ou débito de IPI"
				),
				gravidade=GRAVIDADE_ATENCAO,
			)
		)

	return pendencias
