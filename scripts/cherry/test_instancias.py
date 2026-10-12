# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da identidade das instâncias vista pelo Cherry: leitura do contrato do Soda, alcance e portas.

O registro de exemplo é gravado pelo **próprio Soda** (`Registro`) e lido pelo Cherry por outro caminho (o leitor
somente leitura do contrato). Os casos de versão futura e de arquivo ilegível gravam o registro à mão.

Rodar: `python -m unittest scripts.cherry.test_instancias -v` na raiz do repositório.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from erpnext_brasil.bancos.repositorio import Uso
from erpnext_brasil.soda import configuracao as soda_configuracao
from erpnext_brasil.soda.modelo import Estado
from scripts.cherry import config as cfg
from scripts.cherry import instancias as inst


class _ComBench(unittest.TestCase):
	def setUp(self):
		self._tmp = tempfile.TemporaryDirectory()
		self.addCleanup(self._tmp.cleanup)
		self.raiz = Path(self._tmp.name)
		(self.raiz / "sites").mkdir()
		self.bench = cfg.Bench(self.raiz)

	def criar_site(self, nome, config=None):
		pasta = self.raiz / "sites" / nome
		pasta.mkdir(parents=True, exist_ok=True)
		cfg.gravar_json(pasta / "site_config.json", config if config is not None else {"db_name": "_x"})

	def registrar(self, descritivo, estado=Estado.PARADA, **opcoes):
		"""Cria a instância pelo Soda, cria o site dela no bench e leva ao estado pedido."""
		pasta = soda_configuracao.pasta_do_soda(self.bench.sites)
		pasta.mkdir(parents=True, exist_ok=True)
		registro = soda_configuracao.abrir_registro(pasta, livre=lambda porta: True)
		instancia = registro.criar(descritivo, perfil_de_banco="padrao", tipo_de_banco="mariadb", **opcoes)
		self.criar_site(
			instancia.host,
			{"db_name": "_x", "soda_instance_id": instancia.uuid, "soda_descritivo": descritivo},
		)
		registro.mudar_estado(instancia.uuid, Estado.PARADA)

		if estado in (Estado.SUBINDO, Estado.NO_AR):
			registro.mudar_estado(instancia.uuid, Estado.SUBINDO)

		if estado == Estado.NO_AR:
			registro.mudar_estado(instancia.uuid, Estado.NO_AR)

		return instancia


class TestLeituraDaIdentidade(_ComBench):
	def test_sem_registro_do_soda_o_cherry_funciona_como_antes(self):
		self.criar_site("um.localhost")

		self.assertIsNone(inst.leitor_do_soda(self.bench))
		self.assertFalse(inst.tem_registro_do_soda(self.bench))
		itens = inst.instancias_do_bench(self.bench)
		self.assertEqual([(i.site, i.identificada) for i in itens], [("um.localhost", False)])
		self.assertEqual(inst.rotulo_da_instancia(itens[0]), "um.localhost  (sem UUID)")
		self.assertEqual(inst.instancias_no_ar(self.bench), [])

	def test_o_que_o_soda_grava_o_cherry_le_pela_outra_porta(self):
		criada = self.registrar("Homologação", Estado.NO_AR)
		self.criar_site("solto.localhost")

		por_site = {i.site: i for i in inst.instancias_do_bench(self.bench)}

		identificada = por_site[criada.host]
		self.assertTrue(identificada.identificada)
		self.assertEqual(
			(identificada.instancia.uuid, identificada.instancia.descritivo, identificada.instancia.porta),
			(criada.uuid, "Homologação", criada.porta),
		)
		self.assertFalse(por_site["solto.localhost"].identificada)

	def test_rotulo_traz_descritivo_uuid_abreviado_porta_estado_e_o_site_em_segundo_plano(self):
		criada = self.registrar("Homologação", Estado.NO_AR)
		(item,) = [i for i in inst.instancias_do_bench(self.bench) if i.identificada]

		rotulo = inst.rotulo_da_instancia(item)

		self.assertTrue(rotulo.startswith(f"Homologação · {criada.abreviado} · porta {criada.porta} · no ar"))
		self.assertTrue(rotulo.endswith(f"[{criada.host}]"))

	def test_estado_de_versao_futura_aparece_como_veio(self):
		self.assertEqual(inst.rotulo_do_estado("no_ar"), "no ar")
		self.assertEqual(inst.rotulo_do_estado("hibernando"), "hibernando")

	def test_so_as_instancias_no_ar_ou_subindo_entram_no_aviso(self):
		self.registrar("Parada", Estado.PARADA)
		no_ar = self.registrar("NoAr", Estado.NO_AR)
		subindo = self.registrar("Subindo", Estado.SUBINDO)

		self.assertEqual(
			set(inst.instancias_no_ar(self.bench)),
			{Uso("NoAr", no_ar.abreviado), Uso("Subindo", subindo.abreviado)},
		)

	def test_registro_de_versao_futura_e_lido_sem_ser_gravado(self):
		criada = self.registrar("Homologação")
		caminho = soda_configuracao.caminho_do_registro(
			soda_configuracao.pasta_do_soda(self.bench.sites), "json"
		)
		dados = json.loads(caminho.read_text(encoding="utf-8"))
		dados["versao_esquema"] = 99
		dados["colecoes"]["instancias"][criada.uuid]["campo_do_futuro"] = {"a": 1}
		dados["colecoes"]["meta"]["esquema"] = {"versao_esquema": 99}
		caminho.write_text(json.dumps(dados), encoding="utf-8")
		antes = caminho.read_bytes()

		itens = [i for i in inst.instancias_do_bench(self.bench) if i.identificada]

		self.assertEqual([i.instancia.descritivo for i in itens], ["Homologação"])
		self.assertEqual(caminho.read_bytes(), antes, "o Cherry nunca grava no registro do Soda")

	def test_registro_ilegivel_degrada_para_sem_soda(self):
		self.criar_site("um.localhost")
		pasta = soda_configuracao.pasta_do_soda(self.bench.sites)
		pasta.mkdir(parents=True)
		(pasta / "registro.json").write_text("{ não é json", encoding="utf-8")

		self.assertEqual([i.identificada for i in inst.instancias_do_bench(self.bench)], [False])
		self.assertEqual(inst.instancias_no_ar(self.bench), [])

	def test_dois_formatos_sem_marcador_degrada_para_sem_soda(self):
		pasta = soda_configuracao.pasta_do_soda(self.bench.sites)
		pasta.mkdir(parents=True)
		(pasta / "registro.json").write_text("{}", encoding="utf-8")
		(pasta / "registro.sqlite").write_bytes(b"")

		self.assertFalse(inst.tem_registro_do_soda(self.bench))

	def test_pasta_do_soda_sem_registro_e_sem_soda(self):
		soda_configuracao.pasta_do_soda(self.bench.sites).mkdir(parents=True)
		self.assertFalse(inst.tem_registro_do_soda(self.bench))


class TestPortas(_ComBench):
	def test_porta_do_valor(self):
		casos = {
			8000: 8000,
			"8000": 8000,
			" 8000 ": 8000,
			"redis://127.0.0.1:13000": 13000,
			"redis://127.0.0.1": None,
			"redis://[::1:99999": None,
			"": None,
			"abc": None,
			None: None,
			True: None,
			3.5: None,
		}

		for valor, esperado in casos.items():
			with self.subTest(valor=valor):
				self.assertEqual(inst.porta_do_valor(valor), esperado)

	def test_porta_de_uma_instancia_e_recusada_e_nomeia_a_instancia(self):
		criada = self.registrar("Homologação")

		motivo = inst.conflito_de_porta(self.bench, criada.porta)

		self.assertIn(f"Homologação ({criada.abreviado})", motivo)

	def test_porta_da_faixa_do_soda_e_recusada_mesmo_sem_instancia_nessa_porta(self):
		self.registrar("Homologação")

		motivo = inst.conflito_de_porta(self.bench, "8555")

		self.assertIn("faixa 8100 a 8999", motivo)

	def test_porta_fora_da_faixa_e_livre(self):
		self.registrar("Homologação")

		for valor in (8000, 9000, 11000, "redis://127.0.0.1:13000", "", None):
			with self.subTest(valor=valor):
				self.assertIsNone(inst.conflito_de_porta(self.bench, valor))

	def test_sem_soda_nenhuma_porta_e_recusada(self):
		self.assertIsNone(inst.conflito_de_porta(self.bench, 8100))

	def test_redis_na_porta_de_uma_instancia_tambem_e_recusado(self):
		criada = self.registrar("Homologação")
		self.assertIsNotNone(inst.conflito_de_porta(self.bench, f"redis://127.0.0.1:{criada.porta}"))


class TestIdentidadeProtegida(_ComBench):
	def test_editar_um_site_preserva_a_identidade(self):
		criada = self.registrar("Homologação")
		caminho = self.bench.site_config(criada.host)
		antes = {k: cfg.ler_json(caminho)[k] for k in ("soda_instance_id", "soda_descritivo")}

		inst.gravar_no_site(self.bench, criada.host, {"allow_tests": True})

		depois = json.loads(caminho.read_text(encoding="utf-8"))
		self.assertTrue(depois["allow_tests"])
		self.assertEqual({k: depois[k] for k in antes}, antes)
		self.assertEqual(depois["db_name"], "_x", "o resto do arquivo sobrevive")

	def test_as_chaves_da_identidade_sao_recusadas_e_nada_e_gravado(self):
		criada = self.registrar("Homologação")
		caminho = self.bench.site_config(criada.host)
		antes = caminho.read_bytes()

		for chave in ("soda_instance_id", "soda_descritivo"):
			with self.subTest(chave=chave), self.assertRaises(cfg.CherryInvalido) as contexto:
				inst.gravar_no_site(self.bench, criada.host, {chave: None, "allow_tests": True})

			self.assertIn(chave, str(contexto.exception))

		with self.assertRaises(cfg.CherryInvalido) as contexto:
			inst.gravar_no_site(self.bench, criada.host, {"soda_instance_id": "x", "soda_descritivo": "y"})

		self.assertIn("são da identidade", str(contexto.exception))
		self.assertEqual(caminho.read_bytes(), antes)

	def test_site_sem_identidade_continua_editavel(self):
		self.criar_site("solto.localhost")
		inst.gravar_no_site(self.bench, "solto.localhost", {"allow_tests": True})
		self.assertTrue(cfg.ler_json(self.bench.site_config("solto.localhost"))["allow_tests"])

	def test_site_desconhecido_e_recusado(self):
		with self.assertRaises(cfg.CherryInvalido):
			inst.gravar_no_site(self.bench, "nao-existe.localhost", {"allow_tests": True})

	def test_pos_condicao_falha_alto_se_a_identidade_mudar_durante_a_gravacao(self):
		criada = self.registrar("Homologação")
		caminho = self.bench.site_config(criada.host)
		original = cfg.atualizar_json

		def adulterado(arquivo, alteracoes):
			dados = original(arquivo, alteracoes)
			cfg.gravar_json(arquivo, {**dados, "soda_instance_id": "outro"})

			return dados

		with (
			mock.patch.object(cfg, "atualizar_json", adulterado),
			self.assertRaises(cfg.CherryInvalido) as contexto,
		):
			inst.gravar_no_site(self.bench, criada.host, {"allow_tests": True})

		self.assertIn("mudou durante a gravação", str(contexto.exception))
		self.assertEqual(cfg.ler_json(caminho)["soda_instance_id"], "outro")


if __name__ == "__main__":
	unittest.main()
