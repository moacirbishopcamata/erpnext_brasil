# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""CT-e (Conhecimento de Transporte Eletrônico, modelo 57): montagem de grupos do XML.

Por que existe
--------------
Primeira peça de código do CT-e, depois do levantamento em `docs/cte-estado.md`. Escopo
deliberadamente estreito: só o grupo `ICMSUFFim` (partilha do ICMS entre UF de origem e UF de
término da prestação, para tomador consumidor final não contribuinte — Art. 155 §2º VII/VIII
CF, EC 87/2015), porque é o único ponto do levantamento já verificado byte a byte contra o XSD
oficial (`cte_v4.00.xsd`, `nfephp-org/sped-cte`, grupo `imp/ICMSUFFim`, linha 3960).

O que fica de fora, e por quê
------------------------------
A tabela de CFOP para prestação de serviço de transporte (grupo `5.35x`/`6.35x`/`6.36x` do
Convênio SINIEF 6/89) **não** está aqui: não foi verificada contra fonte primária nesta
investigação (o levantamento em `docs/cte-estado.md` confirmou que `ide.CFOP` usa o mesmo tipo
`TCfop` de 4 dígitos já implementado em `fiscal/cfop.py`, mas não os valores específicos de
transporte). Adicionar esses códigos de memória, sem checar a fonte, é exatamente o tipo de erro
silencioso que este projeto existe para evitar (ver `docs/cfop.md` sobre o bug de dígito faltante
pego pelo teste, e `docs/pcp-estado.md` sobre o campo quase reaproveitado errado) — fica para um
incremento futuro, com fonte citada.

Reuso deliberado
----------------
`montar_icms_uf_fim` não recalcula DIFAL — delega inteiramente a
`fiscal.impostos.icms.calcular_difal`, que já implementa a partilha de base dupla/única e o FCP.
A única coisa nova aqui é o **nome dos campos** no grupo `ICMSUFFim` do CT-e, que diverge do
`ICMSUFDest` da NF-e (`vBCUFFim` em vez de `vBCUFDest`, `pICMSUFFim` em vez de `pICMSUFDest`) —
confirmado por leitura direta do XSD, não suposto por analogia.

`montar_infnfe` monta o grupo `infDoc/infNFe` (a ponte com a NF-e transportada — o dado que o
MDF-e vai precisar referenciar depois, ver `docs/cte-estado.md`). Não reimplementa validação de
chave de acesso: reusa `fiscal.documento.chave_acesso.ler_chave`, a mesma função que a NF-e usa
— o layout de 44 posições e o dígito verificador são idênticos entre os documentos da família
(NF-e, CT-e, MDF-e), só o dígito de modelo muda. Confirmado por leitura do XSD (`infNFe.chave`,
tipo `TChDFe` — "T**Ch****D**ocumento **F**iscal **e**letrônico", o mesmo tipo genérico usado
para `chCTe` em outros grupos do próprio CT-e) que o campo é só a chave, sem repetir o valor da
nota (diferente de `infNF`, para NF modelo 01/04 em papel, que carrega o detalhamento fiscal
inteiro — esse grupo não foi implementado, é o caso legado, cada vez mais raro).

`assinar_cte` reusa `fiscal.documento.assinatura.py` inteiro, sem alteração — `referencia_do_id`,
`montar_signed_info` e `montar_signature` já eram genéricos (parametrizados por `id_elemento`,
nunca fixados em `"NFe"`), então não havia nada a mudar para o CT-e. A única coisa a verificar
era se o **perfil** de assinatura do CT-e é mesmo o mesmo da NF-e — não é suposição por analogia:

- O XSD confirma o formato do `Id`: `infCte/@Id`, padrão `CTe[0-9]{44}` (linha 4917 de
  `cteTiposBasico_v4.00.xsd`) — mesma convenção `<prefixo><chave>` da NF-e, só troca `NFe` por
  `CTe`.
- O algoritmo de assinatura foi corroborado por **código de produção**, não por manual: a classe
  `Signer` de `nfephp-org/sped-common` — usada por `sped-nfe`, `sped-cte`, `sped-mdfe` e outros
  pacotes da mesma família — tem `OPENSSL_ALGO_SHA1` como algoritmo padrão; `signCTe()` de
  `nfephp-org/sped-cte` chama esse `Signer::sign` sem sobrescrever o algoritmo. É uma
  corroboração mais forte que a maioria das fontes secundárias deste projeto (não é um blog
  resumindo a regra, é a implementação que assina CT-e de verdade em produção), mas ainda não é
  o texto do Ajuste SINIEF — declarado como tal, mesmo padrão de honestidade do módulo
  `cfop_transporte.py`. Sem essa corroboração, reusar `assinatura.py` seria supor que o CT-e
  segue a NF-e por "fazerem parte da mesma família" — o mesmo tipo de suposição que já se provou
  falsa uma vez neste projeto (eSocial usa SHA-256, não SHA-1, apesar de também ser um
  documento fiscal eletrônico brasileiro — ver `docs/rh-esocial-assinatura.md`).
"""

from decimal import Decimal

from erpnext_brasil.fiscal.documento.assinatura import Assinador, montar_signature
from erpnext_brasil.fiscal.documento.chave_acesso import ChaveInvalida, ler_chave
from erpnext_brasil.fiscal.documento.serializacao import para_xml
from erpnext_brasil.fiscal.impostos.icms import calcular_difal

__all__ = ["assinar_cte", "montar_icms_uf_fim", "montar_infnfe"]


def montar_icms_uf_fim(
	valor_prestacao: Decimal,
	aliquota_interestadual: Decimal,
	aliquota_interna_destino: Decimal,
	aliquota_fcp: Decimal = Decimal(0),
	base_dupla: bool = True,
) -> dict:
	"""Monta o grupo `ICMSUFFim` (`imp/ICMSUFFim` do XSD do CT-e).

	Só se aplica a prestações interestaduais de transporte para consumidor final não
	contribuinte do ICMS — mesma condição de aplicabilidade do `ICMSUFDest` na NF-e.
	Devolve os nomes de campo exatos do XSD (`vBCUFFim`, `pFCPUFFim`, `pICMSUFFim`,
	`pICMSInter`, `vFCPUFFim`, `vICMSUFFim`, `vICMSUFIni` — este último é o ICMS que fica
	com a UF de início da prestação, equivalente ao `icms_origem` do cálculo).
	"""
	resultado = calcular_difal(
		valor_operacao=valor_prestacao,
		aliquota_interestadual=aliquota_interestadual,
		aliquota_interna_destino=aliquota_interna_destino,
		base_dupla=base_dupla,
		aliquota_fcp=aliquota_fcp,
	)

	grupo = {
		"vBCUFFim": str(resultado["base_destino"]),
		"pFCPUFFim": str(aliquota_fcp),
		"pICMSUFFim": str(aliquota_interna_destino),
		"pICMSInter": str(aliquota_interestadual),
		"vFCPUFFim": str(resultado["fcp"]),
		"vICMSUFFim": str(resultado["difal"]),
		"vICMSUFIni": str(resultado["icms_origem"]),
	}

	return grupo


def montar_infnfe(chaves_nfe: list[str]) -> list[dict]:
	"""Monta a lista de referências `infDoc/infNFe` — uma por NF-e transportada.

	Cada item vira `{"chave": <44 dígitos>}` — o XSD não carrega mais nada obrigatório
	além da chave (ver docstring do módulo). Valida cada chave com a mesma rotina da
	NF-e (`ler_chave`) e recusa uma chave que não seja de NF-e — evitaria colar por
	engano a chave de outro CT-e ou de um MDF-e no lugar errado, erro que só apareceria
	na rejeição da SEFAZ sem essa checagem local.
	"""
	grupo = []

	for chave in chaves_nfe:
		decomposta = ler_chave(chave)

		if decomposta.modelo != "55":
			raise ChaveInvalida(
				f"infDoc/infNFe só aceita chave de NF-e (modelo 55), "
				f"recebida chave de modelo {decomposta.modelo} ({decomposta.documento})",
				chave,
			)

		grupo.append({"chave": decomposta.valor})

	return grupo


def assinar_cte(cte: dict, assinador: Assinador) -> dict:
	"""Assina o documento e devolve a árvore completa, com `Signature` anexado.

	Mesma costura de `fiscal.documento.nfe.assinar_nfe`: serializa a árvore (com o `Id`
	já aplicado em `infCte`), assina, e monta o envelope `Signature` como irmão de
	`infCte` dentro de `CTe`. Recebe `cte` — não `infcte` — pelo mesmo motivo da NF-e: o
	`Id` a assinar é o de `infCte`, mas o digest tem que ser calculado sobre a árvore com
	o namespace já aplicado.
	"""
	id_elemento = cte["CTe"]["infCte"]["@Id"]
	xml = para_xml(cte).encode("utf-8")

	material = assinador.assinar(xml, id_elemento)
	signature = montar_signature(id_elemento, material)

	return {"CTe": {**cte["CTe"], **signature}}
