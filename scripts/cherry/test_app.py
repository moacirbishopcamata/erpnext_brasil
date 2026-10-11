# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Teste de fumaça da interface: a janela existe (oculta), carrega um bench temporário e cada
aba grava de verdade — o arquivo é relido por fora, não pela própria tela.

Precisa de um display (Windows, ou Linux com `DISPLAY`). Sem ele, pula: a CI do projeto
roda em Ubuntu sem X, e o núcleo (`test_config.py`) continua coberto lá.

Rodar: `python -m unittest scripts.cherry.test_app -v` na raiz do repositório.
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from scripts.cherry import config as cfg

TEM_DISPLAY = sys.platform == "win32" or bool(os.environ.get("DISPLAY"))


def _bench_temporario(raiz: Path) -> cfg.Bench:
	(raiz / "sites" / "a.localhost").mkdir(parents=True)
	(raiz / "sites" / "a.localhost" / "site_config.json").write_text(
		'{"db_name": "_a", "db_password": "x"}\n'
	)
	(raiz / "sites" / "b.localhost").mkdir()
	(raiz / "sites" / "b.localhost" / "site_config.json").write_text('{"db_name": "_b"}\n')
	cfg.gravar_json(
		raiz / "sites" / "common_site_config.json",
		{"db_type": "mariadb", "redis_cache": "redis://127.0.0.1:13001"},
	)
	cfg.gravar_apps_txt(raiz / "sites" / "apps.txt", ["frappe", "erpnext"])

	return cfg.Bench(raiz)


@unittest.skipUnless(TEM_DISPLAY, "sem display para o tkinter")
class TestCherry(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		from scripts.cherry import app

		cls.app = app
		cls._prefs = mock.patch.object(app, "PREFERENCIAS", Path(tempfile.mkdtemp()) / "cherry.json")
		cls._prefs.start()
		cls.janela = app.Cherry()
		cls.janela.withdraw()

	@classmethod
	def tearDownClass(cls):
		cls.janela.destroy()
		cls._prefs.stop()

	def setUp(self):
		self._tmp = tempfile.TemporaryDirectory()
		self.raiz = Path(self._tmp.name)
		self.bench = _bench_temporario(self.raiz)
		self.janela._carregar_bench(self.bench)

	def tearDown(self):
		self._tmp.cleanup()

	def test_titulo_traz_a_versao(self):
		from scripts.cherry import __version__

		self.assertIn(__version__, self.janela.title())

	def test_carregar_bench_preenche_as_abas(self):
		self.assertEqual(self.janela.tipo.get(), "mariadb")
		self.assertEqual(self.janela.portas["redis_cache"].get(), "redis://127.0.0.1:13001")
		self.assertEqual(list(self.janela.lista_sites.get(0, "end")), ["a.localhost", "b.localhost"])
		self.assertEqual(self.janela.texto_apps.get("1.0", "end").split(), ["frappe", "erpnext"])

	def test_trocar_para_postgres_sugere_porta_e_usuario_sem_pisar_valor_digitado(self):
		self.janela.tipo.set("postgres")
		self.janela._ao_trocar_tipo()
		self.assertEqual(self.janela.porta.get(), "5432")
		self.assertEqual(self.janela.usuario_root.get(), "postgres")

		self.janela.porta.set("5433")
		self.janela.usuario_root.set("dba")
		self.janela.tipo.set("mariadb")
		self.janela._ao_trocar_tipo()
		self.assertEqual(self.janela.porta.get(), "5433", "porta digitada é dado confirmado")
		self.assertEqual(self.janela.usuario_root.get(), "dba")

	def test_gravar_banco_confirma_a_troca_de_tipo_e_grava_o_arquivo(self):
		self.janela.tipo.set("postgres")
		self.janela.porta.set("5432")
		self.janela.usuario_root.set("postgres")
		self.janela.senha_root.set("postgres")

		with mock.patch.object(self.app.messagebox, "askyesno", return_value=True) as pergunta:
			self.janela._gravar_banco()

		pergunta.assert_called_once()
		relido = json.loads(self.bench.common_config.read_text(encoding="utf-8"))
		self.assertEqual(relido["db_type"], "postgres")
		self.assertEqual(relido["db_port"], 5432)
		self.assertEqual(relido["root_login"], "postgres")
		self.assertEqual(relido["redis_cache"], "redis://127.0.0.1:13001", "o resto do arquivo sobrevive")
		self.assertEqual(self.janela.marca.get(), "✓ gravado")

	def test_recusar_a_confirmacao_nao_grava(self):
		self.janela.tipo.set("postgres")

		with mock.patch.object(self.app.messagebox, "askyesno", return_value=False):
			self.janela._gravar_banco()

		self.assertEqual(json.loads(self.bench.common_config.read_text())["db_type"], "mariadb")

	def test_mesmo_tipo_nao_pergunta(self):
		with mock.patch.object(self.app.messagebox, "askyesno") as pergunta:
			self.janela._gravar_banco()

		pergunta.assert_not_called()

	def test_porta_nao_numerica_e_problema_sem_gravar(self):
		self.janela.porta.set("abc")

		with mock.patch.object(self.app.messagebox, "showerror") as erro:
			self.janela._gravar_banco()

		erro.assert_called_once()
		self.assertNotIn("Erro", self.janela.estado.get(), "vocabulário sem culpa")
		self.assertIn("Não foi possível", self.janela.estado.get())

	def test_gravar_portas_remove_o_que_ficou_vazio(self):
		self.janela.portas["redis_cache"].set("")
		self.janela.portas["webserver_port"].set("8001")
		self.janela.developer_mode.set(True)
		self.janela._gravar_portas()
		relido = json.loads(self.bench.common_config.read_text())
		self.assertNotIn("redis_cache", relido)
		self.assertEqual(relido["webserver_port"], 8001)
		self.assertEqual(relido["developer_mode"], 1)

	def test_site_allow_tests_e_default_site(self):
		self.janela.lista_sites.selection_set(1)
		self.janela._mostrar_site()
		self.assertIn('"db_name": "_b"', self.janela.detalhe_site.get("1.0", "end"))

		self.janela.allow_tests.set(True)
		self.janela._gravar_site()
		self.assertTrue(json.loads(self.bench.site_config("b.localhost").read_text())["allow_tests"])

		self.janela._tornar_padrao()
		comum = json.loads(self.bench.common_config.read_text())
		self.assertEqual(comum["default_site"], "b.localhost")
		self.assertTrue(comum["serve_default_site"])

	def test_senha_do_site_aparece_mascarada(self):
		self.janela.lista_sites.selection_set(0)
		self.janela._mostrar_site()
		detalhe = self.janela.detalhe_site.get("1.0", "end")
		self.assertIn('"db_password": "***"', detalhe)
		self.assertNotIn('"x"', detalhe)

	def test_gravar_apps_normaliza_e_termina_em_lf(self):
		self.janela.texto_apps.delete("1.0", "end")
		self.janela.texto_apps.insert("1.0", "erpnext\n\nfrappe\nerpnext_brasil")
		self.janela._gravar_apps()
		self.assertEqual(self.bench.apps_txt.read_bytes(), b"frappe\nerpnext\nerpnext_brasil\n")

	def test_comando_new_site_vai_para_a_tela_e_para_a_area_de_transferencia(self):
		self.janela.site_novo.set("novo.localhost")
		self.janela._copiar_new_site()
		self.assertIn("bench new-site novo.localhost", self.janela.texto_comando.get("1.0", "end"))
		self.assertIn("--db-type mariadb", self.janela.clipboard_get())

	def test_senha_de_administrador_nao_vem_preenchida_e_nao_entra_no_comando(self):
		"""CH-04: o `admin` pré-preenchido virava `--admin-password 'admin'` em quem não trocasse."""
		self.assertEqual(self.janela.senha_admin.get(), "")

		self.janela._copiar_new_site()

		self.assertNotIn("--admin-password", self.janela.texto_comando.get("1.0", "end"))

	def test_area_de_transferencia_e_limpa_quando_ainda_tem_o_comando(self):
		self.janela._copiar_new_site()
		comando = self.janela.clipboard_get()

		self.janela._limpar_area_de_transferencia(comando)

		with self.assertRaises(self.app.tk.TclError):
			self.janela.clipboard_get()

	def test_area_de_transferencia_nao_apaga_o_que_nao_e_do_cherry(self):
		self.janela._copiar_new_site()
		comando = self.janela.clipboard_get()
		self.janela.clipboard_clear()
		self.janela.clipboard_append("outra coisa copiada depois")

		self.janela._limpar_area_de_transferencia(comando)

		self.assertEqual(self.janela.clipboard_get(), "outra coisa copiada depois")

	def test_a_limpeza_fica_agendada_ao_copiar(self):
		with mock.patch.object(self.app, "LIMPEZA_DA_AREA_DE_TRANSFERENCIA_MS", 50):
			self.janela._copiar_new_site()

		self.assertIsNotNone(self.janela._limpeza_agendada)
		self.janela.after_cancel(self.janela._limpeza_agendada)

	# ------------------------------------------------------------------ teste de conexão (CH-05)

	def _esperar_fim_do_teste(self, limite=3.0):
		fim = time.monotonic() + limite

		while self.janela._teste_em_andamento and time.monotonic() < fim:
			self.janela.update()
			time.sleep(0.02)

		self.janela.update()

	def _teste_lento(self, resultado=None, erro=None):
		"""Uma sonda que só termina quando o teste manda: devolve (função, evento de liberação)."""
		liberar = threading.Event()

		def lenta(banco, bench=None, **_):
			liberar.wait(5)

			if erro:
				raise erro

			return resultado or self.app.cfg.ResultadoConexao(True, "autenticacao", "OK lento")

		return lenta, liberar

	def test_o_teste_de_conexao_nao_trava_a_janela(self):
		lenta, liberar = self._teste_lento()

		with mock.patch.object(self.app.cfg, "testar_conexao", lenta):
			inicio = time.monotonic()
			self.janela._testar_conexao()
			demora = time.monotonic() - inicio

			self.assertLess(demora, 0.5, "a janela esperou a sonda terminar")
			self.assertTrue(self.janela._teste_em_andamento)
			self.assertEqual(self.janela.botao_testar.cget("text"), "Parar de esperar")
			self.assertIn("Testando", self.janela.estado.get())
			self.janela.update()  # a janela continua atendendo eventos enquanto a sonda roda

			liberar.set()
			self._esperar_fim_do_teste()

		self.assertFalse(self.janela._teste_em_andamento)
		self.assertEqual(self.janela.botao_testar.cget("text"), "Testar conexão")
		self.assertIn("Conectou", self.janela.estado.get())
		self.assertIn("✓ conectou", self.janela.marca.get())

	def test_conexao_que_nao_conectou_avisa_com_a_mensagem(self):
		falha = self.app.cfg.ResultadoConexao(False, "autenticacao", "senha incorreta")

		with (
			mock.patch.object(self.app.cfg, "testar_conexao", return_value=falha),
			mock.patch.object(self.app.messagebox, "showwarning") as aviso,
		):
			self.janela._testar_conexao()
			self._esperar_fim_do_teste()

		aviso.assert_called_once()
		self.assertIn("senha incorreta", aviso.call_args.args[1])
		self.assertIn("Não conectou", self.janela.estado.get())

	def test_parar_de_esperar_descarta_o_resultado_que_chegar_depois(self):
		lenta, liberar = self._teste_lento()

		with (
			mock.patch.object(self.app.cfg, "testar_conexao", lenta),
			mock.patch.object(self.app.messagebox, "showwarning") as aviso,
		):
			self.janela._testar_conexao()
			self.janela._testar_conexao()  # segundo clique = "Parar de esperar"

			self.assertFalse(self.janela._teste_em_andamento)
			self.assertEqual(self.janela.botao_testar.cget("text"), "Testar conexão")
			self.assertIn("Parou de esperar", self.janela.estado.get())

			liberar.set()
			time.sleep(0.2)
			self.janela.update()

		aviso.assert_not_called()
		self.assertNotIn("Conectou", self.janela.estado.get())

	def test_excecao_na_sonda_vira_mensagem_e_nao_thread_morta(self):
		lenta, liberar = self._teste_lento(erro=RuntimeError("sonda quebrou"))
		liberar.set()

		with (
			mock.patch.object(self.app.cfg, "testar_conexao", lenta),
			mock.patch.object(self.app.messagebox, "showerror") as problema,
		):
			self.janela._testar_conexao()
			self._esperar_fim_do_teste()

		problema.assert_called_once()
		self.assertIn("sonda quebrou", problema.call_args.args[1])
		self.assertFalse(self.janela._teste_em_andamento)
		self.assertEqual(self.janela.botao_testar.cget("text"), "Testar conexão")

	def test_porta_ilegivel_nao_inicia_teste_nenhum(self):
		self.janela.porta.set("abc")

		with mock.patch.object(self.app.messagebox, "showerror"):
			self.janela._testar_conexao()

		self.assertFalse(self.janela._teste_em_andamento)
		self.janela.porta.set("3306")

	# ------------------------------------------------------------------ ramos de erro sem teste (CH-06)

	def test_gravar_banco_com_falha_de_escrita_mostra_o_problema(self):
		with (
			mock.patch.object(self.app.cfg, "atualizar_json", side_effect=OSError("disco cheio")),
			mock.patch.object(self.app.messagebox, "showerror") as problema,
		):
			self.janela._gravar_banco()

		problema.assert_called_once()
		self.assertIn("disco cheio", problema.call_args.args[1])

	def test_gravar_banco_com_json_ilegivel_mostra_o_problema(self):
		self.bench.common_config.write_text("{quebrado", encoding="utf-8")

		with mock.patch.object(self.app.messagebox, "showerror") as problema:
			self.janela._gravar_banco()

		problema.assert_called_once()
		self.assertEqual(self.bench.common_config.read_text(encoding="utf-8"), "{quebrado")

	def test_copiar_new_site_com_nome_recusado_mostra_o_problema(self):
		self.janela.site_novo.set("a;b")

		with mock.patch.object(self.app.messagebox, "showerror") as problema:
			self.janela._copiar_new_site()

		problema.assert_called_once()
		self.janela.site_novo.set("novo.localhost")

	def test_sem_bench_carregado_manda_para_a_primeira_aba(self):
		self.janela.bench = None

		with mock.patch.object(self.app.messagebox, "showerror"):
			self.assertFalse(self.janela._exigir_bench())

		self.assertEqual(self.janela.abas.index(self.janela.abas.select()), 0)

	def test_preferencias_nao_guardam_senha(self):
		self.janela.senha_root.set("segredo")
		self.janela._salvar_preferencias()
		prefs = self.app.PREFERENCIAS.read_text(encoding="utf-8")
		self.assertNotIn("segredo", prefs)
		self.assertIn(str(self.raiz).replace("\\", "\\\\"), prefs)


if __name__ == "__main__":
	unittest.main()
