# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Auditoria da pilha (`scripts/auditar_pilha.py`) — tarefa 3.1 de `tropicalizar-demais-modulos`.

Sem rede: as fontes são falsas. Os formatos dos avisos e do OSV nos testes são **os reais** que quebraram o
primeiro casamento de faixas, em 2026-10-09 — faixa só com a versão corrigida, `tbd`, prefixo `v`, CVE repetido
em GHSA e PYSEC.

Teste-âncora: `test_faixa_so_com_a_versao_corrigida_nao_afeta_quem_esta_acima`. A primeira versão tratava
"sem operador" como "afeta tudo" e acusou como vulneráveis o HRMS 16.20.1 (corrigido em 16.7.0) e o Frappe
16.36.1 (corrigido em 16.11.0).
"""

import datetime
import unittest

from scripts.auditar_pilha import (
	Relatorio,
	auditar,
	classificar_advisories,
	comparar_versoes,
	faixa_afeta,
	ultima_afetada,
)

HOJE = datetime.date(2026, 10, 9)


class TestCompararVersoes(unittest.TestCase):
	def test_ordem_numerica_e_nao_textual(self):
		self.assertEqual(comparar_versoes("16.9.0", "16.10.0"), -1)
		self.assertEqual(comparar_versoes("16.51.0", "16.51.0"), 0)
		self.assertEqual(comparar_versoes("3.14.8", "3.14.6"), 1)

	def test_tolera_prefixo_v_e_sufixo(self):
		self.assertEqual(comparar_versoes("v16.5.0", "16.5.0"), 0)
		self.assertEqual(comparar_versoes("16.0.0-beta", "16.0.0"), 0)

	def test_quantidade_diferente_de_partes(self):
		self.assertEqual(comparar_versoes("10.11", "10.11.0"), 0)
		self.assertEqual(comparar_versoes("5.31", "5.31.1"), -1)


class TestFaixaAfeta(unittest.TestCase):
	def test_faixa_so_com_a_versao_corrigida_nao_afeta_quem_esta_acima(self):
		self.assertEqual(faixa_afeta("16.7.0", "16.20.1"), "nao_afeta")
		self.assertEqual(faixa_afeta("16.11.0", "16.36.1"), "nao_afeta")

	def test_faixa_so_com_a_versao_corrigida_afeta_quem_esta_abaixo(self):
		self.assertEqual(faixa_afeta("16.7.0", "16.6.9"), "afeta")

	def test_na_propria_versao_corrigida_ja_nao_afeta(self):
		self.assertEqual(faixa_afeta("16.7.0", "16.7.0"), "nao_afeta")

	def test_tbd_ou_vazio_e_indeterminado(self):
		for faixa in ("tbd", "TBD", "", None, "  "):
			with self.subTest(faixa=faixa):
				self.assertEqual(faixa_afeta(faixa, "16.36.1"), "indeterminado")

	def test_operadores(self):
		self.assertEqual(faixa_afeta("< 16.34.0", "16.37.0"), "nao_afeta")
		self.assertEqual(faixa_afeta("< 16.34.0", "16.33.9"), "afeta")
		self.assertEqual(faixa_afeta("<16.34.0", "16.33.9"), "afeta", "sem espaço depois do operador")
		self.assertEqual(faixa_afeta(">= 16.0.0, < 16.18.0", "16.17.9"), "afeta")
		self.assertEqual(faixa_afeta(">= 16.0.0, < 16.18.0", "16.20.1"), "nao_afeta")
		self.assertEqual(faixa_afeta(">= 15.0.0, < 15.64.0", "16.20.1"), "nao_afeta", "outra série")

	def test_prefixo_v_na_faixa(self):
		self.assertEqual(faixa_afeta("< v16.5.0", "16.20.1"), "nao_afeta")
		self.assertEqual(faixa_afeta("< v16.5.0", "16.4.0"), "afeta")


def _aviso(identificador, gravidade, *entradas, resumo="x"):
	return {
		"cve_id": identificador if identificador.startswith("CVE") else None,
		"ghsa_id": identificador if identificador.startswith("GHSA") else "GHSA-zzzz",
		"severity": gravidade,
		"summary": resumo,
		"vulnerabilities": [{"vulnerable_version_range": f, "patched_versions": p} for f, p in entradas],
	}


class TestClassificarAdvisories(unittest.TestCase):
	def test_so_afeta_o_que_a_faixa_da_instalada_cobre(self):
		avisos = [
			_aviso("GHSA-a", "critical", ("< 15.121.0", "15.121.0"), ("< 16.34.0", "16.34.0")),
			_aviso("GHSA-b", "high", ("< 15.121.0", "15.121.0"), ("< 16.40.0", "16.40.0")),
		]

		afetam, indeterminados = classificar_advisories(avisos, "16.37.0", "erpnext")

		self.assertEqual([a.identificador for a in afetam], ["GHSA-b"])
		self.assertEqual(afetam[0].corrigido_em, "16.40.0")
		self.assertEqual(indeterminados, [])

	def test_tbd_vai_para_indeterminados_e_nao_para_afetam(self):
		avisos = [_aviso("CVE-2026-1", "medium", ("tbd", "tbd"), ("tbd", "tbd"))]

		afetam, indeterminados = classificar_advisories(avisos, "16.36.1", "frappe")

		self.assertEqual(afetam, [])
		self.assertEqual([i.identificador for i in indeterminados], ["CVE-2026-1"])

	def test_o_aviso_vem_com_cve_quando_tem(self):
		afetam, _ = classificar_advisories(
			[_aviso("CVE-2026-7", "high", ("< 99.0.0", "99.0.0"))], "16.0.0", "x"
		)

		self.assertEqual(afetam[0].identificador, "CVE-2026-7")


class FontesFalsas:
	def __init__(self, **mudancas):
		self.__dict__.update(
			{
				"tags": {"frappe": "16.51.0", "erpnext": "16.50.0", "hrms": "16.50.0"},
				"bench": "5.31.0",
				"ciclos": {
					"python": {"latest": "3.14.8", "eol": "2030-10-31"},
					"nodejs": {"latest": "24.21.0", "eol": "2028-04-30"},
					"mariadb": {"latest": "10.11.19", "eol": "2028-02-16"},
					"redis": {"latest": "7.2.16", "eol": "2029-12-01"},
				},
				"avisos": {"frappe": [], "erpnext": [], "hrms": [], "bench": []},
				"vulns": {},
				"quebradas": set(),
			}
		)
		self.__dict__.update(mudancas)

	def _checar(self, nome):
		if nome in self.quebradas:
			raise OSError(f"{nome} fora do ar")

	def ultima_tag(self, projeto, versao):
		self._checar("github")

		return self.tags[projeto]

	def ultima_pypi(self, pacote):
		self._checar("pypi")

		return self.bench

	def ciclo(self, produto, versao):
		self._checar("endoflife")

		return self.ciclos[produto]

	def advisories(self, projeto):
		self._checar("advisories")

		return self.avisos[projeto]

	def osv(self, bibliotecas):
		self._checar("osv")

		return [self.vulns.get(nome, []) for nome in bibliotecas]


def _instalados(**mudancas):
	base = {
		"apps": {"frappe": "16.51.0", "erpnext": "16.50.0", "hrms": "16.50.0"},
		"bench": "5.31.0",
		"runtimes": {"python": "3.14.8", "nodejs": "24.21.0", "mariadb": "10.11.19", "redis": "7.2.16"},
		"bibliotecas": {},
	}
	base.update(mudancas)

	return base


class TestAuditar(unittest.TestCase):
	def test_tudo_em_dia_sai_zero(self):
		relatorio = auditar(_instalados(), FontesFalsas(), HOJE)

		self.assertEqual(relatorio.falhas, [])
		self.assertEqual(relatorio.codigo_de_saida, 0)
		self.assertTrue(all(c["situacao"] == "em dia" for c in relatorio.componentes))

	def test_atras_da_ultima_e_relatado_mas_nao_falha(self):
		relatorio = auditar(
			_instalados(apps={"frappe": "16.36.1", "erpnext": "16.37.0", "hrms": "16.20.1"}),
			FontesFalsas(),
			HOJE,
		)

		atrasados = [c for c in relatorio.componentes if "atrás" in c["situacao"]]

		self.assertEqual({c["nome"] for c in atrasados}, {"frappe", "erpnext", "hrms"})
		self.assertIn(
			"16.51.0", atrasados[0]["situacao"] + atrasados[1]["situacao"] + atrasados[2]["situacao"]
		)
		self.assertEqual(relatorio.codigo_de_saida, 0, "defasagem não é falha")

	def test_serie_fora_de_suporte_falha(self):
		fontes = FontesFalsas(ciclos={
			"python": {"latest": "3.14.8", "eol": "2030-10-31"},
			"nodejs": {"latest": "24.21.0", "eol": "2028-04-30"},
			"mariadb": {"latest": "10.11.19", "eol": "2028-02-16"},
			"redis": {"latest": "7.0.15", "eol": "2024-07-29"},
		})  # fmt: skip

		relatorio = auditar(
			_instalados(
				runtimes={"python": "3.14.8", "nodejs": "24.21.0", "mariadb": "10.11.19", "redis": "7.0.15"}
			),
			fontes,
			HOJE,
		)

		self.assertEqual(relatorio.codigo_de_saida, 1)
		self.assertTrue(any("redis" in f and "fora de suporte" in f for f in relatorio.falhas))

	def test_eol_falso_significa_sem_data_de_fim(self):
		fontes = FontesFalsas()
		fontes.ciclos["redis"] = {"latest": "8.10.2", "eol": False}

		relatorio = auditar(_instalados(runtimes={"redis": "8.10.2"}), fontes, HOJE)

		self.assertEqual(relatorio.codigo_de_saida, 0)

	def test_vulnerabilidade_alta_que_afeta_falha(self):
		fontes = FontesFalsas(
			avisos={
				"frappe": [_aviso("CVE-2026-9", "high", ("< 16.60.0", "16.60.0"))],
				"erpnext": [],
				"hrms": [],
				"bench": [],
			}
		)

		relatorio = auditar(_instalados(), fontes, HOJE)

		self.assertEqual(relatorio.codigo_de_saida, 1)
		self.assertTrue(any("CVE-2026-9" in f for f in relatorio.falhas))

	def test_vulnerabilidade_media_e_relatada_mas_nao_falha(self):
		fontes = FontesFalsas(
			avisos={
				"frappe": [_aviso("CVE-2026-9", "medium", ("< 16.60.0", "16.60.0"))],
				"erpnext": [],
				"hrms": [],
				"bench": [],
			}
		)

		relatorio = auditar(_instalados(), fontes, HOJE)

		self.assertEqual(len(relatorio.vulnerabilidades), 1)
		self.assertEqual(relatorio.codigo_de_saida, 0)

	def test_aviso_corrigido_numa_versao_menor_que_a_instalada_nao_aparece(self):
		fontes = FontesFalsas(
			avisos={
				"frappe": [_aviso("CVE-2026-28436", "low", ("16.11.0", "16.11.0"), ("15.102.0", "15.102.0"))],
				"erpnext": [],
				"hrms": [],
				"bench": [],
			}
		)

		relatorio = auditar(_instalados(), fontes, HOJE)

		self.assertEqual(relatorio.vulnerabilidades, [])
		self.assertEqual(relatorio.indeterminados, [])

	def test_aviso_sem_versao_corrigida_e_indeterminado_e_nao_falha(self):
		fontes = FontesFalsas(
			avisos={
				"frappe": [_aviso("CVE-2026-53569", "medium", ("tbd", "tbd"))],
				"erpnext": [],
				"hrms": [],
				"bench": [],
			}
		)

		relatorio = auditar(_instalados(), fontes, HOJE)

		self.assertEqual(relatorio.vulnerabilidades, [])
		self.assertEqual([i.identificador for i in relatorio.indeterminados], ["CVE-2026-53569"])
		self.assertEqual(relatorio.codigo_de_saida, 0)

	def test_ultima_afetada_le_o_last_affected_do_osv(self):
		registro = {
			"affected": [
				{
					"ranges": [
						{
							"events": [{"introduced": "0"}],
							"database_specific": {"extracted_events": [{"last_affected": "16.31.0"}]},
						}
					]
				}
			]
		}

		self.assertEqual(ultima_afetada(registro), "16.31.0")
		self.assertIsNone(ultima_afetada({"affected": []}))

	def test_indeterminado_acima_do_last_affected_do_osv_nao_afeta(self):
		fontes = FontesFalsas(
			avisos={
				"frappe": [_aviso("CVE-2026-53569", "medium", ("tbd", "tbd"))],
				"erpnext": [],
				"hrms": [],
				"bench": [],
			}
		)
		fontes.vuln_osv = lambda identificador: {
			"affected": [{"ranges": [{"events": [{"last_affected": "16.31.0"}]}]}]
		}

		relatorio = auditar(_instalados(), fontes, HOJE)  # frappe 16.51.0 > 16.31.0

		self.assertEqual(relatorio.indeterminados, [])
		self.assertEqual(relatorio.vulnerabilidades, [])

	def test_indeterminado_dentro_do_last_affected_continua_indeterminado(self):
		fontes = FontesFalsas(
			avisos={
				"frappe": [_aviso("CVE-2026-53569", "medium", ("tbd", "tbd"))],
				"erpnext": [],
				"hrms": [],
				"bench": [],
			}
		)
		fontes.vuln_osv = lambda identificador: {
			"affected": [{"ranges": [{"events": [{"last_affected": "16.99.0"}]}]}]
		}

		relatorio = auditar(_instalados(), fontes, HOJE)

		self.assertEqual([i.identificador for i in relatorio.indeterminados], ["CVE-2026-53569"])

	def test_osv_fora_do_ar_nao_esconde_o_indeterminado(self):
		fontes = FontesFalsas(
			avisos={
				"frappe": [_aviso("CVE-2026-53569", "medium", ("tbd", "tbd"))],
				"erpnext": [],
				"hrms": [],
				"bench": [],
			}
		)

		def fora_do_ar(identificador):
			raise OSError("osv fora do ar")

		fontes.vuln_osv = fora_do_ar

		relatorio = auditar(_instalados(), fontes, HOJE)

		self.assertEqual([i.identificador for i in relatorio.indeterminados], ["CVE-2026-53569"])

	def test_o_mesmo_cve_em_ghsa_e_pysec_conta_uma_vez(self):
		duplicado = [
			{"id": "GHSA-1", "aliases": ["CVE-2026-100"], "summary": "dos", "database_specific": {"severity": "HIGH"},
			 "affected": [{"package": {"name": "pypdf"}, "ranges": [{"events": [{"introduced": "0"}, {"fixed": "6.19.0"}]}]}]},
			{"id": "PYSEC-1", "aliases": ["CVE-2026-100"], "summary": "dos", "database_specific": {},
			 "affected": [{"package": {"name": "pypdf"}, "ranges": [{"events": [{"fixed": "6.19.0"}]}]}]},
		]  # fmt: skip
		fontes = FontesFalsas(vulns={"pypdf": duplicado})

		relatorio = auditar(_instalados(bibliotecas={"pypdf": "6.15.0"}), fontes, HOJE)

		self.assertEqual(len(relatorio.vulnerabilidades), 1)
		self.assertEqual(relatorio.vulnerabilidades[0].identificador, "CVE-2026-100")
		self.assertEqual(relatorio.vulnerabilidades[0].corrigido_em, "6.19.0")
		self.assertEqual(relatorio.codigo_de_saida, 1, "alta que afeta")

	def test_a_correcao_indicada_e_a_menor_acima_da_instalada(self):
		v = {"id": "GHSA-2", "aliases": ["CVE-2026-200"], "summary": "x", "database_specific": {"severity": "MODERATE"},
			 "affected": [{"package": {"name": "Werkzeug"}, "ranges": [{"events": [{"fixed": "3.0.5"}, {"fixed": "3.1.9"}, {"fixed": "3.1.7"}]}]}]}  # fmt: skip

		relatorio = auditar(
			_instalados(bibliotecas={"Werkzeug": "3.1.6"}), FontesFalsas(vulns={"Werkzeug": [v]}), HOJE
		)

		self.assertEqual(relatorio.vulnerabilidades[0].corrigido_em, "3.1.7")

	def test_fonte_fora_do_ar_e_nao_verificado_e_nunca_em_dia(self):
		for fonte in ("github", "pypi", "endoflife", "advisories", "osv"):
			with self.subTest(fonte=fonte):
				relatorio = auditar(
					_instalados(bibliotecas={"pypdf": "6.19.0"}), FontesFalsas(quebradas={fonte}), HOJE
				)

				self.assertTrue(relatorio.nao_verificados, f"{fonte} caiu e o relatório não disse")
				self.assertEqual(relatorio.codigo_de_saida, 1)

	def test_componente_nao_encontrado_no_ambiente_falha(self):
		relatorio = auditar(_instalados(runtimes={"python": "3.14.8", "mariadb": None}), FontesFalsas(), HOJE)

		self.assertTrue(any("mariadb" in f and "não encontrado" in f for f in relatorio.falhas))
		self.assertEqual(relatorio.codigo_de_saida, 1)

	def test_app_nao_instalado_falha_em_vez_de_sumir(self):
		relatorio = auditar(_instalados(apps={"frappe": "16.51.0", "hrms": None}), FontesFalsas(), HOJE)

		self.assertTrue(any("hrms" in f for f in relatorio.falhas))


class TestRelatorio(unittest.TestCase):
	def test_relatorio_vazio_sai_zero(self):
		self.assertEqual(Relatorio().codigo_de_saida, 0)


if __name__ == "__main__":
	unittest.main()
