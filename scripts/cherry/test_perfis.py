# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes dos perfis de banco do Cherry: a costura entre a regra pura e os arquivos do bench.

Cada teste grava por um caminho e relê por outro (o arquivo cru, o leitor do Soda), e os que tratam de senha
varrem **todos os arquivos do bench** em busca dela.

Rodar: `python -m unittest scripts.cherry.test_perfis -v` na raiz do repositório.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from erpnext_brasil.bancos import perfis as leitor_de_perfis
from erpnext_brasil.bancos.repositorio import PerfilEmUso
from erpnext_brasil.soda import configuracao as soda_configuracao
from erpnext_brasil.soda.modelo import Estado
from scripts.cherry import config as cfg
from scripts.cherry import perfis as pf

SENHA = "s3nh4-Secreta-do-root"
EXEMPLO = {
	"background_workers": 1,
	"db_host": "127.0.0.1",
	"db_port": 3306,
	"db_type": "mariadb",
	"default_site": "um.localhost",
	"developer_mode": 1,
	"redis_cache": "redis://127.0.0.1:13000",
	"root_login": "root",
	"root_password": SENHA,
}


class _Executor:
	def __init__(self, *respostas):
		self.respostas = list(respostas)
		self.ambientes = []
		self.comandos = []

	def __call__(self, comando, **opcoes):
		self.comandos.append(list(comando))
		self.ambientes.append(opcoes.get("env") or {})
		saida = self.respostas.pop(0)

		return mock.Mock(stdout=saida, stderr="", returncode=0)


class _ComBench(unittest.TestCase):
	def setUp(self):
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.raiz = Path(self._tmp.name)
		(self.raiz / "sites").mkdir()
		self.bench = cfg.Bench(self.raiz)

	def escrever_config(self, dados=None):
		cfg.gravar_json(self.bench.common_config, EXEMPLO if dados is None else dados)

	def lido(self):
		return json.loads(self.bench.common_config.read_text(encoding="utf-8"))

	def todos_os_arquivos(self):
		return [a for a in self.raiz.rglob("*") if a.is_file()]


class TestAdocaoDaConfiguracaoAtual(_ComBench):
	def test_o_bench_existente_vira_o_perfil_padrao_e_o_arquivo_fica_identico(self):
		self.escrever_config()
		antes = self.bench.common_config.read_bytes()

		perfis = pf.abrir_perfis(self.bench)

		(padrao,) = perfis.listar()
		self.assertEqual(
			(padrao.nome, padrao.tipo, padrao.host, padrao.porta, padrao.usuario_root),
			("padrao", "mariadb", "127.0.0.1", 3306, "root"),
		)
		self.assertTrue(padrao.padrao)
		self.assertEqual(self.bench.common_config.read_bytes(), antes, "byte a byte")

	def test_a_senha_de_root_do_arquivo_nao_vai_para_o_perfil(self):
		self.escrever_config()
		pf.abrir_perfis(self.bench)

		perfis_em_disco = [a for a in self.todos_os_arquivos() if a != self.bench.common_config]
		self.assertTrue(perfis_em_disco)

		for arquivo in perfis_em_disco:
			self.assertNotIn(SENHA.encode(), arquivo.read_bytes(), arquivo.name)

	def test_abrir_duas_vezes_nao_duplica(self):
		self.escrever_config()
		pf.abrir_perfis(self.bench)
		self.assertEqual(len(pf.abrir_perfis(self.bench).listar()), 1)

	def test_bench_sem_banco_configurado_nao_cria_perfil_e_nem_o_arquivo_de_configuracao(self):
		self.assertEqual(pf.abrir_perfis(self.bench).listar(), [])
		self.assertFalse(self.bench.common_config.exists())

	def test_perfis_ficam_em_sites_cherry(self):
		self.assertEqual(pf.pasta_dos_perfis(self.bench), self.raiz / "sites" / "cherry")


class TestPublicacaoDoPadrao(_ComBench):
	def test_trocar_o_padrao_grava_no_common_site_config_e_preserva_o_resto(self):
		self.escrever_config()
		perfis = pf.abrir_perfis(self.bench)
		perfis.criar("pg", "postgres", "db.local", 5433, "postgres")

		perfis.definir_padrao("pg")

		lido = self.lido()
		self.assertEqual(
			(lido["db_type"], lido["db_host"], lido["db_port"], lido["root_login"]),
			("postgres", "db.local", 5433, "postgres"),
		)
		for chave in ("background_workers", "default_site", "developer_mode", "redis_cache"):
			self.assertEqual(lido[chave], EXEMPLO[chave], chave)

	def test_a_senha_de_root_existente_nao_e_tocada_nem_inventada(self):
		self.escrever_config()
		perfis = pf.abrir_perfis(self.bench)
		perfis.criar("pg", "postgres")
		perfis.definir_padrao("pg")
		self.assertEqual(self.lido()["root_password"], SENHA, "o que o usuário gravou fica")

		self.escrever_config({k: v for k, v in EXEMPLO.items() if k != "root_password"})
		perfis.definir_padrao("padrao")
		self.assertNotIn("root_password", self.lido())

	def test_o_primeiro_perfil_de_um_bench_vazio_e_publicado(self):
		perfis = pf.abrir_perfis(self.bench)
		perfis.criar("maria", "mariadb")

		self.assertEqual(self.lido(), {"db_host": "127.0.0.1", "db_port": 3306, "db_type": "mariadb"})

	def test_alterar_o_padrao_republica(self):
		perfis = pf.abrir_perfis(self.bench)
		perfis.criar("maria", "mariadb")
		perfis.alterar("maria", host="db.local", usuario_root="admin")

		self.assertEqual((self.lido()["db_host"], self.lido()["root_login"]), ("db.local", "admin"))

	def test_o_que_o_cherry_grava_o_leitor_do_soda_le_pela_outra_porta(self):
		perfis = pf.abrir_perfis(self.bench)
		perfis.criar("maria", "mariadb")
		perfis.criar("pg", "postgres")

		leitor = leitor_de_perfis.abrir_leitor(pf.pasta_dos_perfis(self.bench), pf.FORMATO_PADRAO)

		self.assertEqual([(p.nome, p.padrao) for p in leitor.ler().perfis], [("maria", True), ("pg", False)])


class TestPerfilEmUsoPeloSoda(_ComBench):
	def registrar_instancia(self, perfil, estado=Estado.PARADA, descritivo="Homologação"):
		pasta = soda_configuracao.pasta_do_soda(self.bench.sites)
		pasta.mkdir(parents=True, exist_ok=True)
		registro = soda_configuracao.abrir_registro(pasta, livre=lambda porta: True)
		instancia = registro.criar(descritivo, perfil_de_banco=perfil, tipo_de_banco="mariadb")
		registro.mudar_estado(instancia.uuid, Estado.PARADA)

		if estado != Estado.PARADA:
			registro.mudar_estado(instancia.uuid, Estado.SUBINDO)

			if estado == Estado.NO_AR:
				registro.mudar_estado(instancia.uuid, Estado.NO_AR)

		return instancia

	def test_sem_soda_nada_impede(self):
		perfis = pf.abrir_perfis(self.bench)
		perfis.criar("maria", "mariadb")
		perfis.criar("pg", "postgres")
		perfis.definir_padrao("pg")
		perfis.remover("maria")
		self.assertEqual(pf.instancias_no_ar(self.bench), [])

	def test_remocao_recusada_lista_as_instancias_pelo_descritivo_e_uuid_abreviado(self):
		perfis = pf.abrir_perfis(self.bench)
		perfis.criar("maria", "mariadb")
		perfis.criar("pg", "postgres")
		perfis.definir_padrao("pg")
		a = self.registrar_instancia("maria", descritivo="Homologação")
		b = self.registrar_instancia("maria", descritivo="Treino")

		with self.assertRaises(PerfilEmUso) as contexto:
			perfis.remover("maria")

		mensagem = str(contexto.exception)
		self.assertIn(f"Homologação ({a.abreviado})", mensagem)
		self.assertIn(f"Treino ({b.abreviado})", mensagem)

	def test_perfil_em_uso_nao_muda_de_tipo_nem_de_servidor(self):
		perfis = pf.abrir_perfis(self.bench)
		perfis.criar("maria", "mariadb")
		self.registrar_instancia("maria")

		with self.assertRaises(PerfilEmUso):
			perfis.alterar("maria", tipo="postgres")

		with self.assertRaises(PerfilEmUso):
			perfis.alterar("maria", host="outro.local")

	def test_instancias_no_ar_so_as_que_estao_no_ar_ou_subindo(self):
		self.registrar_instancia("maria", Estado.PARADA, "Parada")
		no_ar = self.registrar_instancia("maria", Estado.NO_AR, "NoAr")
		subindo = self.registrar_instancia("maria", Estado.SUBINDO, "Subindo")

		nomes = {(u.descritivo, u.uuid_abreviado) for u in pf.instancias_no_ar(self.bench)}

		self.assertEqual(nomes, {("NoAr", no_ar.abreviado), ("Subindo", subindo.abreviado)})

	def test_registro_do_soda_ilegivel_nao_derruba_o_cherry(self):
		pasta = soda_configuracao.pasta_do_soda(self.bench.sites)
		pasta.mkdir(parents=True)
		(pasta / "registro.json").write_text("{ não é json", encoding="utf-8")

		self.assertEqual(pf.instancias_no_ar(self.bench), [])

	def test_soda_com_dois_formatos_sem_marcador_e_ignorado(self):
		pasta = soda_configuracao.pasta_do_soda(self.bench.sites)
		pasta.mkdir(parents=True)
		(pasta / "registro.json").write_text("{}", encoding="utf-8")
		(pasta / "registro.sqlite").write_bytes(b"")

		self.assertEqual(pf.instancias_no_ar(self.bench), [])


class TestTesteDeConexaoPorPerfil(_ComBench):
	def test_resultado_guardado_no_perfil_e_senha_em_lugar_nenhum_do_bench(self):
		perfis = pf.abrir_perfis(self.bench)
		perfis.criar("pg", "postgres", "db.local", 5433, "postgres")
		executor = _Executor("OK PostgreSQL 18.6\n")

		resultado = pf.testar_perfil(perfis, "PG", SENHA, executar=executor)

		self.assertTrue(resultado.ok)
		teste = perfis.obter("pg").ultimo_teste
		self.assertEqual((teste.ok, teste.nivel), (True, "autenticacao"))
		self.assertEqual(executor.comandos[0][-4:], ["postgres", "db.local", "5433", "postgres"])
		self.assertNotIn(SENHA, " ".join(executor.comandos[0]), "a senha nunca vai por argumento")
		self.assertEqual(executor.ambientes[0][cfg.VARIAVEL_DA_SENHA], SENHA, "vai pelo ambiente do filho")

		for arquivo in self.todos_os_arquivos():
			self.assertNotIn(SENHA.encode(), arquivo.read_bytes(), arquivo.name)

	def test_falha_tambem_e_guardada(self):
		perfis = pf.abrir_perfis(self.bench)
		perfis.criar("maria", "mariadb")

		resultado = pf.testar_perfil(
			perfis, "maria", "errada", executar=_Executor("FALHA OperationalError: negado\n")
		)

		self.assertFalse(resultado.ok)
		self.assertFalse(perfis.obter("maria").ultimo_teste.ok)

	def test_perfil_inexistente(self):
		with self.assertRaises(cfg.CherryInvalido):
			pf.testar_perfil(pf.abrir_perfis(self.bench), "x", "", executar=_Executor())


class TestNewSiteDoPerfil(_ComBench):
	def test_mariadb_e_postgres(self):
		perfis = pf.abrir_perfis(self.bench)
		maria = perfis.criar("maria", "mariadb", "127.0.0.1", 3306, "root")
		pg = perfis.criar("pg", "postgres", "db.local", 5433, "postgres")

		comando_maria = pf.comando_new_site_do_perfil(maria, "um.localhost")
		comando_pg = pf.comando_new_site_do_perfil(pg, "dois.localhost", apps=("erpnext", "erpnext_brasil"))

		self.assertIn("--db-type mariadb", comando_maria)
		self.assertIn("--db-port 3306", comando_maria)
		self.assertIn("--db-root-username root", comando_maria)
		self.assertIn("--db-type postgres", comando_pg)
		self.assertIn("--db-host db.local", comando_pg)
		self.assertIn("--db-port 5433", comando_pg)
		self.assertIn("--db-root-username postgres", comando_pg)
		self.assertIn("--install-app erpnext_brasil", comando_pg)

	def test_senha_so_entra_quando_informada(self):
		perfil = pf.abrir_perfis(self.bench).criar("maria", "mariadb", usuario_root="root")

		self.assertNotIn("password", pf.comando_new_site_do_perfil(perfil, "um.localhost"))
		self.assertIn(
			"--db-root-password", pf.comando_new_site_do_perfil(perfil, "um.localhost", senha_root=SENHA)
		)

	def test_o_criterio_de_nomes_seguros_continua(self):
		perfil = pf.abrir_perfis(self.bench).criar("maria", "mariadb")

		with self.assertRaises(cfg.CherryInvalido):
			pf.comando_new_site_do_perfil(perfil, "site; rm -rf /")

	def test_banco_do_perfil_leva_a_senha_so_por_parametro(self):
		perfil = pf.abrir_perfis(self.bench).criar("maria", "mariadb", usuario_root="root")

		self.assertEqual(pf.banco_do_perfil(perfil).senha_root, "")
		self.assertEqual(pf.banco_do_perfil(perfil, SENHA).senha_root, SENHA)


if __name__ == "__main__":
	unittest.main()
