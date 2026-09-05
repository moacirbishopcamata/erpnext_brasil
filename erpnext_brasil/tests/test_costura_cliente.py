# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Costura entre o JavaScript do cliente e o Python que ele chama.

Mesma classe de gap dos 31 campos de `docs/gaps.md`: o navegador chama um método por
**string**, e uma string errada não quebra nada em teste — quebra no clique do usuário,
com "método não encontrado" e nenhuma pista de onde está o erro.

Aqui a verificação é de texto contra código: todo `method:` citado num `.js` deste app
existe como função com `@frappe.whitelist()`. Roda sem bench, porque as duas fontes são
arquivos.

O que **não** substitui: clicar no botão num site real. A lacuna segue em `docs/gaps.md`.
"""

import ast
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

_CHAMADA = re.compile(r'method:\s*["\']([\w.]+)["\']')


def _sem_comentarios(fonte: str) -> str:
	"""O JavaScript sem `//` nem `/* */`.

	Serve para medir **o que executa**, não o que explica: as docstrings deste projeto
	citam o que não se deve usar, e uma asserção de ausência sobre o texto inteiro
	reprovaria a explicação junto com o erro que ela previne.
	"""
	sem_bloco = re.sub(r"/\*.*?\*/", "", fonte, flags=re.S)

	return re.sub(r"//.*", "", sem_bloco)


def _bloco(fonte: str, cabecalho: str) -> str:
	"""O corpo da função/método que começa em `cabecalho`, por chaves balanceadas.

	Existe porque medir `assertIn` sobre o arquivo inteiro deixa de provar qualquer coisa
	assim que um segundo botão entra no mesmo `.js`: `br_chave_acesso` passaria a aparecer
	por causa do botão de cancelamento, e o teste da condição do botão de emissão ficaria
	verde sem condição nenhuma. É a mesma armadilha que `_sem_comentarios` resolve do outro
	lado — asserção que mede texto demais.
	"""
	inicio = fonte.index(cabecalho)
	profundidade = 0

	for posicao in range(fonte.index("{", inicio), len(fonte)):
		if fonte[posicao] == "{":
			profundidade += 1
		elif fonte[posicao] == "}":
			profundidade -= 1

			if profundidade == 0:
				return fonte[inicio : posicao + 1]

	raise AssertionError(f"bloco {cabecalho!r} não fecha")


def _metodos_chamados() -> set[str]:
	chamados: set[str] = set()

	for arquivo in (RAIZ / "public" / "js").glob("*.js"):
		chamados |= set(_CHAMADA.findall(arquivo.read_text(encoding="utf-8")))

	return {m for m in chamados if m.startswith("erpnext_brasil.")}


def _tem_whitelist(caminho: Path, funcao: str) -> bool:
	"""Confere no AST que a função existe **e** está exposta.

	Procurar `@frappe.whitelist()` por texto acharia o decorador de outra função no mesmo
	arquivo — o que é justamente o erro que este teste existe para pegar.
	"""
	arvore = ast.parse(caminho.read_text(encoding="utf-8"))

	for no in ast.walk(arvore):
		if not isinstance(no, ast.FunctionDef) or no.name != funcao:
			continue

		for decorador in no.decorator_list:
			alvo = decorador.func if isinstance(decorador, ast.Call) else decorador

			if isinstance(alvo, ast.Attribute) and alvo.attr == "whitelist":
				return True

	return False


class TestMetodosChamadosPeloCliente(unittest.TestCase):
	def test_ha_chamadas_a_conferir(self):
		"""Sem isto, os testes abaixo passariam por vacuidade se o regex quebrasse."""
		self.assertTrue(_metodos_chamados(), "nenhuma chamada encontrada — regex quebrou?")

	def test_todo_metodo_chamado_existe_e_esta_exposto(self):
		for caminho_ponto in sorted(_metodos_chamados()):
			modulo, funcao = caminho_ponto.rsplit(".", 1)
			arquivo = RAIZ.parent / (modulo.replace(".", "/") + ".py")

			with self.subTest(metodo=caminho_ponto):
				self.assertTrue(arquivo.exists(), f"módulo inexistente: {arquivo}")
				self.assertTrue(
					_tem_whitelist(arquivo, funcao),
					f"{funcao} não existe em {modulo} ou não tem @frappe.whitelist()",
				)

	def test_todo_js_do_app_esta_ligado_em_hooks(self):
		"""JavaScript que ninguém carrega é código morto com aparência de recurso."""
		hooks = (RAIZ / "hooks.py").read_text(encoding="utf-8")

		for arquivo in (RAIZ / "public" / "js").glob("*.js"):
			with self.subTest(arquivo=arquivo.name):
				self.assertIn(arquivo.name, hooks)


class TestBotoesFiscais(unittest.TestCase):
	"""Três botões dividem `emissao_nfe.js`, então cada asserção mede a sua fatia.

	Antes do cancelamento este arquivo tinha um botão só, e `assertIn` sobre o texto
	inteiro bastava. Deixou de bastar no instante em que o segundo botão citou
	`br_chave_acesso`: o teste da condição do primeiro continuaria verde mesmo se a
	condição sumisse. Ver `_bloco`.
	"""

	def _fonte(self) -> str:
		return (RAIZ / "public" / "js" / "emissao_nfe.js").read_text(encoding="utf-8")

	def _refresh(self) -> str:
		return _sem_comentarios(_bloco(self._fonte(), "refresh(frm) {"))

	def test_so_aparece_em_documento_efetivado(self):
		"""Rascunho não tem NF-e a emitir: o número seria consumido por algo que ainda
		pode mudar."""
		self.assertIn("docstatus !== 1", self._refresh())

	def test_a_emissao_depende_de_nao_haver_chave_de_acesso(self):
		"""Documento com chave já foi emitido — reemitir queimaria outro número."""
		refresh = self._refresh()
		guarda = refresh.index("!frm.doc.br_chave_acesso")

		self.assertLess(guarda, refresh.index("Emitir NF-e"))

	def test_os_eventos_dependem_de_haver_chave_de_acesso(self):
		"""Sem nota autorizada não há evento a enviar; o botão convidaria a uma recusa."""
		refresh = self._refresh()
		guarda = refresh.index("!frm.doc.br_chave_acesso")

		for rotulo in ("Cancelar NF-e", "Carta de Correção"):
			with self.subTest(botao=rotulo):
				self.assertLess(guarda, refresh.index(rotulo))

	def test_pede_confirmacao_antes_de_emitir(self):
		"""Emitir é irreversível: o número é consumido mesmo se a SEFAZ recusar."""
		self.assertIn("frappe.confirm", _bloco(self._fonte(), "function confirmar_e_emitir"))

	def test_a_confirmacao_diz_o_ambiente(self):
		"""A diferença entre homologação e produção é a diferença entre um teste e um
		documento que existe perante o Fisco."""
		self.assertIn("br_ambiente_sefaz", _bloco(self._fonte(), "function confirmar_e_emitir"))

	def test_pede_confirmacao_antes_de_cancelar(self):
		"""Cancelamento homologado não se desfaz, e a nota não volta a valer."""
		self.assertIn("frappe.confirm", _bloco(self._fonte(), "function pedir_justificativa_e_cancelar"))

	def test_a_justificativa_e_conferida_antes_de_transmitir(self):
		"""Espelho do limite do XSD: dizer a regra antes evita descobri-la por rejeição.
		Quem valida de verdade é `montar_evento_cancelamento`, no domínio puro."""
		from erpnext_brasil.fiscal.documento.evento import JUSTIFICATIVA_MINIMA

		bloco = _bloco(self._fonte(), "function pedir_justificativa_e_cancelar")

		self.assertIn(f"JUSTIFICATIVA_MINIMA = {JUSTIFICATIVA_MINIMA}", self._fonte())
		self.assertIn("< JUSTIFICATIVA_MINIMA", bloco)

	def test_o_texto_da_correcao_e_conferido_antes_de_transmitir(self):
		from erpnext_brasil.fiscal.documento.evento import CORRECAO_MINIMA

		bloco = _bloco(self._fonte(), "function pedir_texto_e_corrigir")

		self.assertIn(f"CORRECAO_MINIMA = {CORRECAO_MINIMA}", self._fonte())
		self.assertIn("< CORRECAO_MINIMA", bloco)

	def test_o_dialogo_avisa_que_a_carta_substitui_a_anterior(self):
		"""Regra de negócio da SEFAZ: quem envia só a correção nova apaga as antigas da
		vista. Este diálogo é o único lugar onde dá para saber isso a tempo."""
		bloco = _sem_comentarios(_bloco(self._fonte(), "function pedir_texto_e_corrigir"))

		self.assertIn("substitui a anterior", bloco)

	def test_toda_chamada_a_sefaz_congela_a_tela(self):
		"""Sem `freeze`, o segundo clique transmite de novo — outro número na emissão,
		outro evento no cancelamento."""
		for funcao in ("function emitir", "function cancelar", "function corrigir"):
			with self.subTest(funcao=funcao):
				self.assertIn("freeze: true", _bloco(self._fonte(), funcao))


class TestTelaDeGeracaoDoEfd(unittest.TestCase):
	"""O botão que faltava para `gerar_efd` — mesma lacuna que a NF-e tinha."""

	def _fonte(self) -> str:
		return (RAIZ / "public" / "js" / "geracao_efd_list.js").read_text(encoding="utf-8")

	def test_esta_na_lista_e_nao_no_formulario(self):
		"""O `Arquivo SPED` é o resultado da geração; um botão no formulário só existiria
		depois de o registro existir, tarde demais."""
		hooks = (RAIZ / "hooks.py").read_text(encoding="utf-8")

		self.assertIn("doctype_list_js", hooks)
		self.assertIn("geracao_efd_list.js", hooks)
		self.assertIn("listview_settings", self._fonte())

	def test_pede_o_endereco_porque_o_backend_se_recusa_a_deduzir(self):
		"""A `Company` pode ter vários vinculados, e o EFD declara um."""
		self.assertIn('fieldname: "address"', self._fonte())
		self.assertIn("reqd: 1", self._fonte())

	def test_o_endereco_e_limpo_ao_trocar_de_empresa(self):
		"""Manter o anterior geraria o arquivo com o estabelecimento errado, e o número
		seria plausível."""
		self.assertIn('dialogo.set_value("address", "")', self._fonte())

	def test_congela_a_tela_durante_a_geracao(self):
		"""Sem isso o segundo clique produz um arquivo idêntico."""
		self.assertIn("freeze: true", self._fonte())

	def test_o_aviso_de_parcial_nao_e_anunciado_como_sucesso(self):
		"""`msgprint` laranja, não alerta verde: anunciar sucesso convidaria a tentar
		transmitir um arquivo que ainda não tem o Bloco D.

		A checagem ignora comentários — eles citam `show_alert` justamente para explicar
		por que não usá-lo, e medir o texto inteiro reprovaria a explicação junto com o
		erro que ela previne. Mesmo tropeço já cometido em `test_efd_inventario`.
		"""
		fonte = _sem_comentarios(self._fonte())

		self.assertIn('indicator: "orange"', fonte)
		self.assertNotIn("show_alert", fonte)


if __name__ == "__main__":
	unittest.main()
