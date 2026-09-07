# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consumo indevido: a guarda que existe para **não** fazer nada.

Teste-âncora: `test_a_guarda_vem_antes_da_rede`. O valor inteiro desta funcionalidade
depende de a verificação acontecer **antes** da requisição sair. Uma guarda que rodasse
depois da resposta seria correta, passaria em qualquer teste de unidade, e não impediria o
bloqueio de se estender — porque a requisição já teria chegado à SEFAZ e reiniciado a hora.

Segundo eixo: `test_garantir_liberado_levanta_em_vez_de_devolver`. Um retorno booleano que
o chamador pode ignorar por descuido devolveria o comportamento antigo sem que nada
acusasse — e o sintoma seria uma espera que nunca termina.

`fiscal/consumo_indevido.py` é puro e se importa de verdade; a camada de integração e o
transporte são conferidos por AST e texto.

Módulo puro: roda sem bench.
"""

import ast
import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from erpnext_brasil.fiscal.consumo_indevido import (
	CARENCIA,
	CSTAT_CONSUMO_INDEVIDO,
	CSTAT_NENHUM_DOCUMENTO_LOCALIZADO,
	Bloqueio,
	e_consumo_indevido,
	iniciar_bloqueio,
)
from erpnext_brasil.tests.ajudantes import sem_docstrings

RAIZ = Path(__file__).resolve().parent.parent

_INTEGRACAO = sem_docstrings((RAIZ / "integracao" / "consumo_indevido.py").read_text(encoding="utf-8"))
_TRANSPORTE = sem_docstrings((RAIZ / "integracao" / "transporte_sefaz.py").read_text(encoding="utf-8"))

_DOCTYPE_DIR = RAIZ / "registros_fiscais" / "doctype" / "bloqueio_sefaz"
_DOCTYPE_JSON = json.loads((_DOCTYPE_DIR / "bloqueio_sefaz.json").read_text(encoding="utf-8"))
_CONTROLLER = (_DOCTYPE_DIR / "bloqueio_sefaz.py").read_text(encoding="utf-8")

AGORA = datetime(2026, 9, 7, 10, 0, 0)


class TestARegraDoTempo(unittest.TestCase):
	def test_a_carencia_e_de_uma_hora(self):
		"""Prazo da SEFAZ, não parâmetro do app."""
		self.assertEqual(timedelta(hours=1), CARENCIA)

	def test_bloqueado_durante_a_janela(self):
		bloqueio = Bloqueio(inicio=AGORA)

		self.assertTrue(bloqueio.ativo_em(AGORA))
		self.assertTrue(bloqueio.ativo_em(AGORA + timedelta(minutes=59, seconds=59)))

	def test_liberado_exatamente_ao_completar_a_hora(self):
		"""Fronteira inclusiva no fim: esperar um segundo a mais não custa nada;
		transmitir um segundo antes custa outra hora."""
		bloqueio = Bloqueio(inicio=AGORA)

		self.assertFalse(bloqueio.ativo_em(AGORA + CARENCIA))
		self.assertEqual(AGORA + CARENCIA, bloqueio.liberado_em)

	def test_o_restante_nunca_e_negativo(self):
		"""Depois de liberado o resultado é zero, não tempo passado — quem formata a
		mensagem não deve precisar tratar sinal."""
		bloqueio = Bloqueio(inicio=AGORA)

		self.assertEqual(timedelta(0), bloqueio.restante(AGORA + timedelta(hours=5)))
		self.assertEqual(timedelta(minutes=30), bloqueio.restante(AGORA + timedelta(minutes=30)))

	def test_nova_rejeicao_reinicia_a_janela(self):
		"""Teste-âncora da regra. Um 656 recebido dentro de uma janela ativa **não**
		estende a antiga: começa outra a partir de agora, e é isso que faz a insistência
		custar cada vez mais."""
		primeiro = iniciar_bloqueio(AGORA)
		mais_tarde = AGORA + timedelta(minutes=45)
		segundo = iniciar_bloqueio(mais_tarde, anterior=primeiro)

		self.assertEqual(mais_tarde, segundo.inicio)
		self.assertEqual(mais_tarde + CARENCIA, segundo.liberado_em)
		self.assertGreater(segundo.liberado_em, primeiro.liberado_em)


class TestOReconhecimentoDoCstat(unittest.TestCase):
	def test_reconhece_texto_e_numero(self):
		"""O `cStat` chega como texto do XML e como número de um campo do Desk. Devolver
		`False` por diferença de tipo significaria transmitir de novo."""
		for valor in ("656", 656, " 656 ", "0656"):
			with self.subTest(valor=valor):
				self.assertTrue(e_consumo_indevido(valor))

	def test_ignora_os_demais(self):
		for valor in ("100", "137", 204, "", None):
			with self.subTest(valor=valor):
				self.assertFalse(e_consumo_indevido(valor))

	def test_o_gatilho_esta_declarado(self):
		"""`137` não é a rejeição — é o gatilho mais comum dela, e está nomeado para quem
		escrever um caminho de reconsulta encontrar o porquê."""
		self.assertEqual("137", CSTAT_NENHUM_DOCUMENTO_LOCALIZADO)
		self.assertEqual("656", CSTAT_CONSUMO_INDEVIDO)


class TestACosturaDaGuarda(unittest.TestCase):
	def test_a_guarda_vem_antes_da_rede(self):
		"""Teste-âncora. Verificar depois da resposta seria correto, passaria nos testes de
		unidade, e não impediria nada — a requisição já teria reiniciado a hora.

		⚠️ A ordem é medida **dentro de `_contexto`**, e não por posição no arquivo: a
		primeira versão deste teste comparava índices do texto inteiro e reprovava código
		correto, porque `_preparar_arquivos_tls` é *definido* antes de `_contexto`. Posição
		de definição não é ordem de execução.
		"""
		corpo = ast.unparse(
			next(
				no
				for no in ast.walk(
					ast.parse((RAIZ / "integracao" / "transporte_sefaz.py").read_text(encoding="utf-8"))
				)
				if isinstance(no, ast.FunctionDef) and no.name == "_contexto"
			)
		)

		self.assertIn("self._guarda(self._cnpj_emitente, self._ambiente)", corpo)
		self.assertLess(corpo.index("self._guarda("), corpo.index("_preparar_arquivos_tls()"))

	def test_a_guarda_fica_no_ponto_unico(self):
		"""`_contexto` é por onde as cinco operações passam. Repetir a guarda em cada uma
		seria cinco chances de esquecer na sexta."""
		self.assertEqual(1, _TRANSPORTE.count("self._guarda("))

	def test_o_transporte_nao_importa_frappe(self):
		"""🔴 A regressão que a suíte pegou, e que este teste impede de voltar.

		`transporte_sefaz` é um adaptador **livre de `frappe`** — é isso que permite testar
		a orquestração inteira sem bench. A primeira versão desta proteção importou
		`integracao/consumo_indevido` no topo dele e derrubou 25 testes de uma vez: o módulo
		deixou de ser importável fora de um site.

		A guarda e o registrador chegam **injetados** de quem constrói o transporte, que já
		vive do lado do Frappe. Mesma disciplina de `sessao` e `dormir`.
		"""
		self.assertNotIn("import frappe", _TRANSPORTE)
		self.assertNotIn("consumo_indevido", _TRANSPORTE)

	def test_a_guarda_e_o_registrador_sao_injetados(self):
		"""Padrão `None` = sem guarda, e não é omissão: é o que mantém o adaptador
		utilizável em teste e em qualquer contexto sem banco."""
		self.assertIn("guarda=None", _TRANSPORTE)
		self.assertIn("registrador=None", _TRANSPORTE)

	def test_quem_transmite_de_verdade_liga_os_dois(self):
		"""Injeção que ninguém injeta é guarda que nunca roda — o gap de costura clássico,
		só que com o desligamento parecendo intencional."""
		for arquivo in ("emissao_nfe.py", "eventos_nfe.py"):
			fonte = (RAIZ / "integracao" / arquivo).read_text(encoding="utf-8")

			with self.subTest(arquivo=arquivo):
				self.assertIn("guarda=garantir_liberado", fonte)
				self.assertIn("registrador=partial(registrar_resposta", fonte)

	def test_toda_resposta_passa_pelo_registro(self):
		"""Quatro pontos de retorno para a SEFAZ: autorização, consulta, evento e
		inutilização. Um retorno sem envoltório é um 656 que ninguém anota."""
		self.assertEqual(4, _TRANSPORTE.count("self._registrar("))

	def test_garantir_liberado_levanta_em_vez_de_devolver(self):
		"""Segundo eixo. Um booleano que o chamador esquece de conferir devolve o
		comportamento antigo sem que nada acuse."""
		arvore = ast.parse((RAIZ / "integracao" / "consumo_indevido.py").read_text(encoding="utf-8"))
		funcao = next(
			no
			for no in ast.walk(arvore)
			if isinstance(no, ast.FunctionDef) and no.name == "garantir_liberado"
		)

		self.assertEqual("None", ast.unparse(funcao.returns))
		self.assertIn("frappe.throw", ast.unparse(funcao))

	def test_a_excecao_e_tipada(self):
		"""Aplicação da lei 6: quem chama precisa distinguir "espere" de "a nota está
		errada". A primeira não deve ser repetida de forma alguma."""
		self.assertIn("class BloqueadoPorConsumoIndevido", _INTEGRACAO)
		self.assertIn("exc=BloqueadoPorConsumoIndevido", _INTEGRACAO)

	def test_a_mensagem_manda_nao_insistir(self):
		"""A reação natural a um erro de transmissão é tentar de novo, e aqui isso custa
		mais uma hora — dizer só "bloqueado" seria informação pela metade."""
		# ⚠️ Lido pelo **AST**, não pelo texto. A mensagem é escrita como literais
		# concatenados implicitamente por causa da largura da linha, e procurá-la no fonte
		# esbarraria nas aspas do meio — reprovando a redação certa. O parser junta os
		# literais num só `Constant`, que é a frase que o usuário de fato lê.
		mensagens = [
			no.value
			for no in ast.walk(
				ast.parse((RAIZ / "integracao" / "consumo_indevido.py").read_text(encoding="utf-8"))
			)
			if isinstance(no, ast.Constant) and isinstance(no.value, str)
		]
		aviso = next(m for m in mensagens if "Não tente transmitir" in m)

		self.assertIn("Não tente transmitir antes disso", aviso)
		self.assertIn("reinicia a contagem de uma hora", aviso)


class TestAPersistencia(unittest.TestCase):
	def test_guarda_em_doctype_e_nao_em_cache(self):
		"""Perder a chave (Redis reiniciado, cache limpo num deploy) liberaria a
		transmissão antes da hora — exatamente o que reinicia a contagem."""
		self.assertIn('DOCTYPE = "Bloqueio Sefaz"', _INTEGRACAO)
		self.assertNotIn("frappe.cache", _INTEGRACAO)

	def test_a_chave_inclui_o_ambiente(self):
		"""Um bloqueio em homologação não pode parar a emissão em produção."""
		self.assertIn("ambiente", _INTEGRACAO)
		self.assertIn("::", _INTEGRACAO)

	def test_a_chave_limpa_o_cnpj(self):
		"""Com e sem máscara seriam duas chaves para o mesmo CNPJ, e uma delas liberaria a
		transmissão."""
		self.assertIn("limpar(cnpj)", _INTEGRACAO)

	def test_o_registro_e_confirmado_na_hora(self):
		"""A rejeição costuma vir num caminho que termina em exceção; o rollback levaria o
		bloqueio junto, deixando o app sem saber que está bloqueado."""
		self.assertIn("frappe.db.commit()", _INTEGRACAO)

	def test_o_doctype_tem_chave_unica(self):
		"""Dois registros para o mesmo par seriam duas verdades sobre a mesma espera."""
		self.assertEqual("field:chave", _DOCTYPE_JSON["autoname"])

		chave = next(c for c in _DOCTYPE_JSON["fields"] if c["fieldname"] == "chave")

		self.assertEqual(1, chave.get("unique"))

	def test_os_campos_de_tempo_sao_somente_leitura(self):
		"""Editar o início à mão é adiantar a liberação — e adiantar é o que reinicia a
		contagem."""
		por_nome = {c["fieldname"]: c for c in _DOCTYPE_JSON["fields"]}

		for campo in ("bloqueado_em", "liberado_em", "cnpj", "ambiente"):
			with self.subTest(campo=campo):
				self.assertEqual(1, por_nome[campo].get("read_only"))

	def test_o_nome_da_classe_do_controller_esta_certo(self):
		"""⚠️ Errar o nome não levanta erro: o Frappe cai no `Document` genérico, os hooks
		do arquivo nunca rodam, e `liberado_em` fica sem derivação — silenciosamente."""
		self.assertIn("class BloqueioSefaz(Document):", _CONTROLLER)
		self.assertEqual("Bloqueio Sefaz", _DOCTYPE_JSON["name"])

	def test_liberado_em_e_derivado_e_nao_digitado(self):
		"""Dois campos de data independentes divergiriam, e a divergência apareceria como
		emissão liberada cedo demais."""
		self.assertIn("self.liberado_em = ", _CONTROLLER)
		self.assertIn("CARENCIA", _CONTROLLER)

	def test_o_doctype_vive_no_modulo_de_registros(self):
		"""`fiscal/` é puro; controller de DocType importa `frappe` por definição."""
		self.assertEqual("Registros Fiscais", _DOCTYPE_JSON["module"])


if __name__ == "__main__":
	unittest.main()
