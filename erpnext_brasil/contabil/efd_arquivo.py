# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Monta o arquivo EFD-ICMS/IPI inteiro a partir dos blocos já implementados.

Os blocos existiam todos (`0`, `C`, `D`, `E`, `H`, `K`, `9`) e nada os juntava num
arquivo entregável — a montagem completa só existia dentro de
`tests/test_efd_arquivo_completo.py`. Lógica que só vive em teste é lógica que ninguém
pode usar; este módulo a promove a código, e o teste passa a exercitá-lo em vez de
reimplementá-lo.

A ordem dos blocos não é escolha
----------------------------------------
`0`, `C`, `D`, `E`, `G`, `H`, `K`, `1`, `9` — nessa sequência, sempre. O `9` é
necessariamente o último porque **conta os demais**, inclusive a si mesmo, e o `0` é
necessariamente o primeiro porque contém os cadastros que os outros referenciam.

Os blocos que este projeto ainda não implementa (`G` do CIAP e `1` de outras informações)
simplesmente não entram. O leiaute admite: bloco ausente é bloco sem movimento, e o PVA
não exige abertura/encerramento de bloco que não existe no arquivo — diferente de um bloco
presente e vazio, que exige o par `X001`/`X990`.

O Bloco 9 não é passado, é calculado
--------------------------------------------
`montar_bloco_9` recebe a contagem dos **demais** blocos e recusa que se informe os
registros dele próprio, porque a quantidade deles é justamente o que ele calcula (a
contagem é auto-referente: cada `9900` conta um tipo de registro, e os `9900` também são
registros). Aqui a contagem é derivada das linhas montadas, nunca informada — não há como
passar um número errado.

O que este módulo **não** faz
-------------------------------------
- **Não lê o site.** Recebe os blocos já montados. Quem os produz a partir de `Sales
  Invoice`, `Stock Ledger Entry` e afins é a camada de integração — e essa é a parte que
  ainda falta (`integracao/efd_dados_cadastrais.py` cobre só o Bloco 0).
- **Não valida entre blocos.** Que o `C190` some com o `E110`, que o `H010` referencie um
  item do `0200` — são regras que cada bloco confere no seu escopo, e cruzá-las aqui
  duplicaria a validação num lugar que não conhece o significado dos campos.
- **Não assina nem entrega.** O EFD não é assinado como a NF-e; é validado e transmitido
  pelo PVA. Este módulo produz o texto que entra nele.

Funções puras: nenhuma dependência do Frappe.
"""

from collections import Counter

from erpnext_brasil.contabil.efd_bloco_9 import montar_bloco_9
from erpnext_brasil.contabil.efd_icms_ipi import EfdInvalido
from erpnext_brasil.contabil.sped_texto import montar_linha

__all__ = ["ORDEM_DOS_BLOCOS", "montar_arquivo_efd", "serializar_arquivo_efd"]

ORDEM_DOS_BLOCOS = ("0", "C", "D", "E", "G", "H", "K", "1")
"""A ordem obrigatória. O `9` fica fora porque é sempre o último e é calculado."""

_REGISTRO_DE_ABERTURA = "0000"


def _bloco_da_linha(linha: dict) -> str:
	"""A letra (ou dígito) do bloco a que o registro pertence — o primeiro caractere."""
	return linha["REG"][0]


def montar_arquivo_efd(blocos: dict[str, list[dict]]) -> list[dict]:
	"""O arquivo inteiro, do `0000` ao `9999`, como lista de registros.

	`blocos` é `{letra do bloco: linhas}`. Bloco ausente do dicionário não entra no
	arquivo, que é o tratamento correto para bloco sem movimento.

	Pós-condições, conferidas aqui porque são propriedades do **arquivo**, não de nenhum
	bloco isolado — e é exatamente por isso que ninguém as checava:

	- o arquivo começa em `0000` e termina em `9999`;
	- cada linha pertence ao bloco em que foi declarada (um `C100` dentro do bloco `"D"`
		é erro de montagem, e passaria despercebido até o PVA reclamar);
	- a contagem do Bloco 9 é derivada das linhas reais, nunca informada.
	"""
	desconhecidos = sorted(set(blocos) - set(ORDEM_DOS_BLOCOS))

	if desconhecidos:
		raise EfdInvalido(
			f"blocos desconhecidos: {desconhecidos}; esperados {list(ORDEM_DOS_BLOCOS)} "
			"(o Bloco 9 é calculado, não informado)"
		)

	if "0" not in blocos:
		raise EfdInvalido("o Bloco 0 é obrigatório: é ele que traz os cadastros que os demais citam")

	linhas: list[dict] = []

	for bloco in ORDEM_DOS_BLOCOS:
		conteudo = blocos.get(bloco) or []

		for linha in conteudo:
			if _bloco_da_linha(linha) != bloco:
				raise EfdInvalido(
					f"o registro {linha['REG']} foi declarado no bloco {bloco!r}, mas pertence "
					f"ao bloco {_bloco_da_linha(linha)!r}"
				)

		linhas.extend(conteudo)

	if not linhas or linhas[0]["REG"] != _REGISTRO_DE_ABERTURA:
		raise EfdInvalido(f"o arquivo começa no registro {_REGISTRO_DE_ABERTURA}")

	contagem = Counter(linha["REG"] for linha in linhas)

	return linhas + montar_bloco_9(dict(contagem))


def serializar_arquivo_efd(linhas: list[dict]) -> str:
	"""O texto do arquivo, uma linha por registro.

	Sem quebra no fim: o `9999` encerra o arquivo, e uma linha vazia depois dele é linha a
	mais para o contador do próprio `9999` — que já foi calculado.
	"""
	return "\n".join(montar_linha(linha) for linha in linhas)
