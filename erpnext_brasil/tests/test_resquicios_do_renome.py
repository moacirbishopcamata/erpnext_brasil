# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Nenhum código lê ou escreve os nomes de campo **anteriores** ao prefixo `br_`.

O bug que este arquivo existe para não deixar voltar
--------------------------------------------------------------
O renome para `br_` trocou as ocorrências **entre aspas** — `doc.get("ncm")`,
`{"fieldname": "ncm"}`. Escapou o que não tem aspas: **atribuição de atributo**.

```python
codigo = doc.get("br_codigo_municipio_ibge")  # lê o campo novo
...
doc.codigo_municipio_ibge = limpo  # escreve no antigo
```

Três dessas ficaram em `integracao/party.py` — inscrição estadual, código de município e
NCM. Todas eram **normalizações**: o valor era lido, limpo, e gravado num atributo que não
existe mais. O Frappe não reclama de atribuição a campo inexistente; o valor simplesmente
não é persistido.

⚠️ E o modo de falhar é o pior possível: **nada quebra**. O cadastro salva, a validação
passa, e o usuário fica com o valor cru — IE com máscara, NCM com ponto — sem aviso nenhum.
Só apareceria muito depois, no arquivo do SPED ou numa rejeição da SEFAZ.

Nenhum teste da suíte pura pegava: os três testes existentes chamavam a função e conferiam o
resultado **no objeto em memória**, onde a atribuição funciona. Quem achou foi o teste de
bench, ao reler do banco.

Como este teste funciona
-------------------------------
Lê a lista de nomes antigos **do próprio patch de renome** — fonte única, e a mesma que a
migração usa —, e varre a árvore sintática procurando escrita ou leitura desses nomes.
Buscar por texto não serviria: `ncm` aparece dentro de `br_ncm`.

Módulo puro: roda sem bench.
"""

import ast
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

PATCH = RAIZ / "patches" / "v0_177_renomear_campos_com_prefixo_br.py"

NOMES_ANTIGOS = set(re.findall(r'\("([a-z_]+)", "br_[a-z_]+"\)', PATCH.read_text(encoding="utf-8")))
"""Os nomes de antes do prefixo, lidos do patch que os renomeou.

Derivar do patch em vez de listar aqui é o que mantém as duas coisas juntas: um renome novo
acrescenta pares lá, e este teste passa a cobri-los sem que ninguém se lembre de editá-lo.
"""


def _modulos():
	"""Todo `.py` do app, menos os próprios testes e o patch que declara os nomes."""
	for caminho in sorted(RAIZ.rglob("*.py")):
		if "tests" in caminho.parts or caminho == PATCH:
			continue

		yield caminho


class TestResquiciosDoRenome(unittest.TestCase):
	def test_a_lista_de_nomes_antigos_nao_esta_vazia(self):
		"""Se a extração parasse de casar, os testes abaixo passariam sem conferir nada —
		varrer zero nomes nunca encontra resquício."""
		self.assertGreater(len(NOMES_ANTIGOS), 20)

	def test_nenhuma_escrita_em_atributo_com_nome_antigo(self):
		"""Teste-âncora. `doc.ncm = x` não levanta erro e não persiste: o valor some."""
		encontrados = []

		for caminho in _modulos():
			for no in ast.walk(ast.parse(caminho.read_text(encoding="utf-8"))):
				if not isinstance(no, ast.Assign):
					continue

				for alvo in no.targets:
					if isinstance(alvo, ast.Attribute) and alvo.attr in NOMES_ANTIGOS:
						encontrados.append(f"{caminho.relative_to(RAIZ)}:{alvo.lineno} {alvo.attr}")

		self.assertEqual([], encontrados, f"escrita em campo antigo: {encontrados}")

	def test_nenhuma_leitura_de_campo_com_nome_antigo(self):
		"""`doc.get("ncm")` devolve `None` em silêncio — o outro lado do mesmo problema."""
		encontrados = []

		for caminho in _modulos():
			for no in ast.walk(ast.parse(caminho.read_text(encoding="utf-8"))):
				achou = (
					isinstance(no, ast.Call)
					and isinstance(no.func, ast.Attribute)
					and no.func.attr in ("get", "set")
					and no.args
					and isinstance(no.args[0], ast.Constant)
					and no.args[0].value in NOMES_ANTIGOS
				)

				if achou:
					encontrados.append(
						f"{caminho.relative_to(RAIZ)}:{no.lineno} {no.func.attr}({no.args[0].value!r})"
					)

		self.assertEqual([], encontrados, f"leitura de campo antigo: {encontrados}")


if __name__ == "__main__":
	unittest.main()
