# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""MDF-e (Manifesto Eletrônico de Documentos Fiscais, modelo 58): montagem de grupos do XML.

Por que existe
--------------
Primeira peça de código do MDF-e, depois do levantamento em `docs/mdfe-estado.md` — só possível
depois que o CT-e passou a existir neste projeto (o MDF-e referencia CT-e/NF-e por chave, nunca
os substitui). Escopo deliberadamente estreito, mesmo padrão do primeiro incremento do CT-e:
só `infDoc`, a peça mais barata e mais próxima de já estar pronta.

Reuso deliberado, e a diferença de forma que o obrigou a não ser cópia direta
------------------------------------------------------------------------------
`montar_infdoc` reusa `fiscal.documento.chave_acesso.ler_chave` — a mesma função usada por
`fiscal.cte.montar_infnfe` — porque o layout de 44 posições é idêntico entre NF-e, CT-e e MDF-e
(confirmado, não suposto: `chave_acesso.MODELOS` já tem `"57"`/`"58"` mapeados desde este
incremento). Mas a **forma** do grupo diverge: `infDoc/infNFe` do CT-e é uma lista plana; o
`infDoc` do MDF-e organiza as referências **por município de descarregamento** (confirmado no
XSD, `infDoc/infMunDescarga/{infCTe,infNFe}`) — cada `infMunDescarga` carrega `cMunDescarga`,
`xMunDescarga` e as chaves de CT-e/NF-e daquele município. Copiar a forma do CT-e sem verificar
teria produzido uma lista plana onde o layout exige agrupamento.

`infMDFeTransp` (referência a outro MDF-e — sub-manifesto de transferência multimodal) não foi
implementado ainda: caso menos comum, fora do escopo deste primeiro incremento.

`assinar_mdfe` reusa `fiscal.documento.assinatura.py` inteiro, sem alteração — mesma disciplina
de `fiscal.cte.assinar_cte`: verificar antes de reaproveitar, nunca supor por "mesma família de
documento" (o `modal` e o `procEmi` do `ide` já divergiram entre CT-e e MDF-e nesta mesma
investigação, ver `docs/mdfe-estado.md` — a assinatura poderia ter divergido também). Duas
confirmações, mesmo padrão do CT-e:

- XSD: `infMDFe/@Id`, padrão `MDFe[0-9]{44}` (`mdfeTiposBasico_v3.00.xsd`, linha 1230) — mesma
  convenção `<prefixo><chave>`.
- Código de produção: `signMDFe()` de `nfephp-org/sped-mdfe` (`src/Common/Tools.php`) chama
  `Signer::sign` com `$this->algorithm`, cujo valor padrão na própria classe é
  `OPENSSL_ALGO_SHA1` — o mesmo algoritmo já confirmado para o CT-e (`docs/cte-assinatura.md`).
"""

from dataclasses import dataclass, field

from erpnext_brasil.fiscal.documento.assinatura import Assinador, montar_signature
from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, ler_chave
from erpnext_brasil.fiscal.documento.serializacao import para_xml

__all__ = ["NAMESPACE_MDFE", "MunicipioDescarga", "assinar_mdfe", "montar_infdoc"]

NAMESPACE_MDFE = "http://www.portalfiscal.inf.br/mdfe"


@dataclass(frozen=True)
class MunicipioDescarga:
	"""Um município de descarregamento e os documentos fiscais nele entregues."""

	codigo: str
	"""`cMunDescarga` — código IBGE."""
	nome: str
	"""`xMunDescarga`."""
	chaves_cte: list[str] = field(default_factory=list)
	chaves_nfe: list[str] = field(default_factory=list)


def _montar_referencias(chaves: list[str], modelo_esperado: str, campo_chave: str, nome_grupo: str) -> list[dict]:
	"""Valida e monta uma lista de referências por chave — mesma lógica de
	`fiscal.cte.montar_infnfe`, parametrizada pelo modelo e pelo nome do campo/grupo
	porque `infCTe`/`chCTe` e `infNFe`/`chNFe` só diferem nisso."""
	referencias = []

	for chave in chaves:
		decomposta = ler_chave(chave)

		if decomposta.modelo != modelo_esperado:
			raise ChaveInvalida(
				f"{nome_grupo} só aceita chave de modelo {modelo_esperado}, "
				f"recebida chave de modelo {decomposta.modelo} ({decomposta.documento})",
				chave,
			)

		referencias.append({campo_chave: decomposta.valor})

	return referencias


def montar_infdoc(municipios: list[MunicipioDescarga]) -> dict:
	"""Monta `infDoc`, agrupado por município de descarregamento.

	Cada `MunicipioDescarga` vira um item de `infMunDescarga`, com `infCTe`/`infNFe`
	presentes só quando há chaves daquele tipo — sem grupo vazio.
	"""
	if not municipios:
		raise ValueError("infDoc precisa de ao menos um município de descarregamento (XSD: minOccurs=1)")

	infmun = []

	for municipio in municipios:
		item: dict = {"cMunDescarga": municipio.codigo, "xMunDescarga": municipio.nome}

		if municipio.chaves_cte:
			item["infCTe"] = _montar_referencias(municipio.chaves_cte, "57", "chCTe", "infDoc/infCTe")

		if municipio.chaves_nfe:
			item["infNFe"] = _montar_referencias(municipio.chaves_nfe, "55", "chNFe", "infDoc/infNFe")

		infmun.append(item)

	return {"infDoc": {"infMunDescarga": infmun}}


def assinar_mdfe(mdfe: dict, assinador: Assinador) -> dict:
	"""Assina o documento e devolve a árvore completa, com `Signature` anexado.

	Mesma costura de `fiscal.cte.assinar_cte`/`fiscal.documento.nfe.assinar_nfe`: serializa a
	árvore (com o `Id` já aplicado em `infMDFe`), assina, e monta o envelope `Signature` como
	irmão de `infMDFe` dentro de `MDFe`. Recebe `mdfe`, não `infmdfe`, pelo mesmo motivo dos
	outros dois: o digest tem que ser calculado sobre a árvore com o namespace já aplicado.
	"""
	id_elemento = mdfe["MDFe"]["infMDFe"]["@Id"]
	xml = para_xml(mdfe).encode("utf-8")

	material = assinador.assinar(xml, id_elemento)
	signature = montar_signature(id_elemento, material)

	return {"MDFe": {**mdfe["MDFe"], **signature}}
