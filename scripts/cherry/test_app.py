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
from scripts.cherry import perfis as pf

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

	# ------------------------------------------------------------------ perfis de banco (cherry-perfis-de-banco)

	def _perfis_na_tabela(self):
		tabela = self.janela.tabela_de_perfis

		return {iid: tabela.item(iid, "values") for iid in tabela.get_children()}

	def _selecionar_perfil(self, nome):
		self.janela.tabela_de_perfis.selection_set(nome)
		self.janela.update()

	def _registrar_instancia_do_soda(self, perfil, estado, descritivo="Homologação"):
		from erpnext_brasil.soda import configuracao as soda_configuracao
		from erpnext_brasil.soda.modelo import Estado

		pasta = soda_configuracao.pasta_do_soda(self.bench.sites)
		pasta.mkdir(parents=True, exist_ok=True)
		registro = soda_configuracao.abrir_registro(pasta, livre=lambda porta: True)
		instancia = registro.criar(descritivo, perfil_de_banco=perfil, tipo_de_banco="mariadb")
		registro.mudar_estado(instancia.uuid, Estado.PARADA)
		registro.mudar_estado(instancia.uuid, Estado.SUBINDO)

		if estado == "no_ar":
			registro.mudar_estado(instancia.uuid, Estado.NO_AR)

		return instancia

	def _criar_perfil_pela_tela(
		self, nome, tipo="postgres", host="db.local", porta="5433", usuario="postgres"
	):
		self.janela._novo_perfil()
		self.janela.nome_do_perfil.set(nome)
		self.janela.tipo.set(tipo)
		self.janela.host.set(host)
		self.janela.porta.set(porta)
		self.janela.usuario_root.set(usuario)

		return self.janela._salvar_perfil()

	def test_bench_existente_aparece_como_o_perfil_padrao(self):
		self.janela.update()
		self.assertEqual(list(self._perfis_na_tabela()), ["padrao"])
		self.assertEqual(self._perfis_na_tabela()["padrao"][1], "✓")
		self.assertEqual(self.janela.nome_do_perfil.get(), "padrao")
		self.assertFalse(self.janela.aviso_sem_perfis.winfo_manager(), "com perfil, o aviso de vazio some")

	def test_estado_vazio_orienta_o_usuario(self):
		with tempfile.TemporaryDirectory() as raiz:
			(Path(raiz) / "sites").mkdir()
			self.janela._carregar_bench(cfg.Bench(Path(raiz)))
			self.assertEqual(self._perfis_na_tabela(), {})
			self.assertIn("Nenhum perfil ainda", self.janela.aviso_sem_perfis.cget("text"))
			self.assertTrue(self.janela.aviso_sem_perfis.winfo_manager())

	def test_salvar_um_perfil_novo_confirma_visualmente_e_lista(self):
		self.assertTrue(self._criar_perfil_pela_tela("pg"))

		self.assertEqual(set(self._perfis_na_tabela()), {"padrao", "pg"})
		self.assertEqual(self._perfis_na_tabela()["pg"][0], "PostgreSQL db.local:5433")
		self.assertEqual(self._perfis_na_tabela()["pg"][1], "", "o padrão continua sendo o outro")
		self.assertEqual(self.janela.marca.get(), "✓ perfil salvo")
		relido = json.loads(self.bench.common_config.read_text(encoding="utf-8"))
		self.assertEqual(relido["db_type"], "mariadb", "salvar não troca o padrão")

	def test_o_mesmo_nome_com_outra_caixa_edita_o_perfil_existente_em_vez_de_duplicar(self):
		self.assertTrue(self._criar_perfil_pela_tela("PADRAO", "mariadb", "outro.local", "3307", "root"))

		self.assertEqual(list(self._perfis_na_tabela()), ["padrao"])
		self.assertEqual(self._perfis_na_tabela()["padrao"][0], "MariaDB outro.local:3307")
		self.assertEqual(self.janela.nome_do_perfil.get(), "padrao")

	def test_nome_com_caracter_invalido_e_um_problema_antes_de_gravar(self):
		with mock.patch.object(self.app.messagebox, "showerror") as problema:
			self.assertFalse(self._criar_perfil_pela_tela("meu perfil"))

		problema.assert_called_once()
		self.assertEqual(set(self._perfis_na_tabela()), {"padrao"})

	def test_selecionar_um_perfil_preenche_o_formulario_e_limpa_a_senha(self):
		self._criar_perfil_pela_tela("pg")
		self.janela.senha_root.set("digitada")

		self._selecionar_perfil("padrao")
		self.assertEqual((self.janela.tipo.get(), self.janela.host.get()), ("mariadb", "127.0.0.1"))
		self._selecionar_perfil("pg")

		self.assertEqual(
			(
				self.janela.tipo.get(),
				self.janela.host.get(),
				self.janela.porta.get(),
				self.janela.usuario_root.get(),
			),
			("postgres", "db.local", "5433", "postgres"),
		)
		self.assertEqual(self.janela.nome_do_perfil.get(), "pg")
		self.assertEqual(self.janela.senha_root.get(), "", "a senha não é do perfil")

	def test_tornar_padrao_grava_no_common_site_config_sem_pisar_o_resto(self):
		self._criar_perfil_pela_tela("pg")
		self._selecionar_perfil("pg")

		self.janela._tornar_perfil_padrao()

		relido = json.loads(self.bench.common_config.read_text(encoding="utf-8"))
		self.assertEqual(
			(relido["db_type"], relido["db_host"], relido["db_port"]), ("postgres", "db.local", 5433)
		)
		self.assertEqual(relido["redis_cache"], "redis://127.0.0.1:13001")
		self.assertEqual(self._perfis_na_tabela()["pg"][1], "✓")
		self.assertEqual(self._perfis_na_tabela()["padrao"][1], "")
		self.assertEqual(self.janela.marca.get(), "✓ padrão")

	def test_tornar_padrao_com_instancia_no_ar_avisa_o_alcance_e_respeita_a_recusa(self):
		self._criar_perfil_pela_tela("pg")
		instancia = self._registrar_instancia_do_soda("padrao", "no_ar")
		self._selecionar_perfil("pg")

		with mock.patch.object(self.app.messagebox, "askyesno", return_value=False) as pergunta:
			self.janela._tornar_perfil_padrao()

		pergunta.assert_called_once()
		self.assertIn(f"Homologação ({instancia.abreviado})", pergunta.call_args.args[1])
		relido = json.loads(self.bench.common_config.read_text(encoding="utf-8"))
		self.assertEqual(relido["db_type"], "mariadb", "recusou: nada mudou")

		with mock.patch.object(self.app.messagebox, "askyesno", return_value=True):
			self.janela._tornar_perfil_padrao()

		self.assertEqual(
			json.loads(self.bench.common_config.read_text(encoding="utf-8"))["db_type"], "postgres"
		)

	def test_tornar_padrao_sem_instancia_no_ar_nao_pergunta(self):
		self._criar_perfil_pela_tela("pg")
		self._selecionar_perfil("pg")

		with mock.patch.object(self.app.messagebox, "askyesno") as pergunta:
			self.janela._tornar_perfil_padrao()

		pergunta.assert_not_called()

	def test_remover_perfil_em_uso_e_recusado_e_lista_as_instancias(self):
		self._criar_perfil_pela_tela("pg")
		instancia = self._registrar_instancia_do_soda("pg", "parada", "Treino")
		self._selecionar_perfil("pg")

		with (
			mock.patch.object(self.app.messagebox, "askyesno", return_value=True),
			mock.patch.object(self.app.messagebox, "showerror") as problema,
		):
			self.janela._remover_perfil()

		problema.assert_called_once()
		self.assertIn(f"Treino ({instancia.abreviado})", problema.call_args.args[1])
		self.assertIn("pg", self._perfis_na_tabela())

	def test_remover_o_padrao_com_outros_perfis_e_recusado(self):
		self._criar_perfil_pela_tela("pg")
		self._selecionar_perfil("padrao")

		with (
			mock.patch.object(self.app.messagebox, "askyesno", return_value=True),
			mock.patch.object(self.app.messagebox, "showerror") as problema,
		):
			self.janela._remover_perfil()

		self.assertIn("é o padrão", problema.call_args.args[1])

	def test_remover_um_perfil_comum_confirma_e_some_da_lista(self):
		self._criar_perfil_pela_tela("pg")
		self._selecionar_perfil("pg")

		with mock.patch.object(self.app.messagebox, "askyesno", return_value=True):
			self.janela._remover_perfil()

		self.assertEqual(set(self._perfis_na_tabela()), {"padrao"})
		self.assertEqual(self.janela.marca.get(), "✓ removido")

	def test_remover_pedindo_confirmacao_e_recusando_nao_remove(self):
		self._criar_perfil_pela_tela("pg")
		self._selecionar_perfil("pg")

		with mock.patch.object(self.app.messagebox, "askyesno", return_value=False):
			self.janela._remover_perfil()

		self.assertIn("pg", self._perfis_na_tabela())

	def test_acoes_sem_perfil_selecionado_explicam_o_que_fazer(self):
		self.janela._novo_perfil()

		for acao in (self.janela._tornar_perfil_padrao, self.janela._remover_perfil):
			with mock.patch.object(self.app.messagebox, "showerror") as problema:
				acao()

			problema.assert_called_once()
			self.assertIn("escolha um perfil", problema.call_args.args[1])

	def test_o_teste_de_conexao_guarda_o_resultado_no_perfil_sem_a_senha(self):
		self._selecionar_perfil("padrao")
		self.janela.senha_root.set("s3nh4-do-teste")
		resultado = self.app.cfg.ResultadoConexao(True, "autenticacao", "OK MariaDB")

		with mock.patch.object(self.app.cfg, "testar_conexao", return_value=resultado):
			self.janela._testar_conexao()
			self._esperar_fim_do_teste()

		self.assertIn("autenticacao", self._perfis_na_tabela()["padrao"][2])
		self.assertIn("✓", self._perfis_na_tabela()["padrao"][2])

		for arquivo in self.raiz.rglob("*"):
			if arquivo.is_file():
				self.assertNotIn(b"s3nh4-do-teste", arquivo.read_bytes(), arquivo.name)

	def test_teste_sem_perfil_salvo_com_esse_nome_nao_registra_nada(self):
		self.janela._novo_perfil()
		resultado = self.app.cfg.ResultadoConexao(False, "tcp", "nada responde")

		with (
			mock.patch.object(self.app.cfg, "testar_conexao", return_value=resultado),
			mock.patch.object(self.app.messagebox, "showwarning"),
		):
			self.janela._testar_conexao()
			self._esperar_fim_do_teste()

		self.assertEqual(self.janela.perfis.obter("padrao").ultimo_teste, None)

	def test_new_site_usa_o_perfil_escolhido(self):
		self._criar_perfil_pela_tela("pg")
		self._selecionar_perfil("pg")
		self.janela.site_novo.set("novo.localhost")

		self.janela._copiar_new_site()

		comando = self.janela.texto_comando.get("1.0", "end")
		self.assertIn("--db-type postgres", comando)
		self.assertIn("--db-host db.local", comando)
		self.assertIn("--db-port 5433", comando)
		self.assertIn("--db-root-username postgres", comando)

	def test_gravar_no_bench_salva_o_perfil_torna_padrao_e_so_grava_a_senha_digitada(self):
		self.janela.nome_do_perfil.set("padrao")
		self.janela.senha_root.set("")
		self.janela._gravar_banco()
		self.assertNotIn("root_password", json.loads(self.bench.common_config.read_text(encoding="utf-8")))

		self.janela.senha_root.set("digitada-agora")
		self.janela._gravar_banco()
		self.assertEqual(
			json.loads(self.bench.common_config.read_text(encoding="utf-8"))["root_password"],
			"digitada-agora",
		)

	def test_gravar_no_bench_sem_nome_cria_o_perfil_padrao(self):
		with tempfile.TemporaryDirectory() as raiz:
			(Path(raiz) / "sites").mkdir()
			bench = cfg.Bench(Path(raiz))
			self.janela._carregar_bench(bench)
			self.janela.nome_do_perfil.set("")
			self.janela.tipo.set("postgres")
			self.janela._ao_trocar_tipo()
			self.janela._gravar_banco()

			self.assertEqual(set(self._perfis_na_tabela()), {"padrao"})
			self.assertEqual(
				json.loads(bench.common_config.read_text(encoding="utf-8"))["db_type"], "postgres"
			)

	def test_gravar_no_bench_para_outro_perfil_avisa_o_alcance(self):
		self._criar_perfil_pela_tela("pg")
		self._registrar_instancia_do_soda("padrao", "no_ar")
		self.janela.nome_do_perfil.set("pg")

		with mock.patch.object(self.app.messagebox, "askyesno", return_value=False) as pergunta:
			self.janela._gravar_banco()

		pergunta.assert_called_once()
		self.assertEqual(
			json.loads(self.bench.common_config.read_text(encoding="utf-8"))["db_type"], "mariadb"
		)

	def test_perfis_ilegiveis_mostram_o_problema_e_nao_travam_a_janela(self):
		pasta = pf.pasta_dos_perfis(self.bench)
		pasta.mkdir(parents=True, exist_ok=True)
		(pasta / "perfis-de-banco.json").write_text("{ não é json", encoding="utf-8")

		with mock.patch.object(self.app.messagebox, "showerror") as problema:
			self.janela._abrir_perfis()

		problema.assert_called()
		self.assertIsNone(self.janela.perfis)
		self.assertEqual(self._perfis_na_tabela(), {})

	def test_salvar_perfil_sem_bench_manda_para_a_primeira_aba(self):
		self.janela.bench = None

		with mock.patch.object(self.app.messagebox, "showerror"):
			self.assertFalse(self.janela._salvar_perfil())

		self.assertEqual(self.janela.abas.index(self.janela.abas.select()), 0)

	def test_perfil_com_porta_ilegivel_e_um_problema(self):
		self.janela.porta.set("abc")

		with mock.patch.object(self.app.messagebox, "showerror") as problema:
			self.assertFalse(self.janela._salvar_perfil())

		problema.assert_called_once()

	def test_selecionar_o_mesmo_perfil_de_novo_nao_apaga_o_que_o_usuario_digitou(self):
		self._selecionar_perfil("padrao")
		self.janela.senha_root.set("em-edicao")
		self.janela._ao_selecionar_perfil()
		self.assertEqual(self.janela.senha_root.get(), "em-edicao")


if __name__ == "__main__":
	unittest.main()
