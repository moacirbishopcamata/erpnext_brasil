# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A correção opcional do instante de emissão — tarefas 5.1 a 5.3 de `fonte-de-tempo-ntp-br`.

Teste-âncora: `test_perto_da_virada_do_mes_a_chave_e_o_dhemi_continuam_no_mesmo_mes`. O `AAMM` da
chave sai do instante de emissão; se a correção empurra esse instante para o mês seguinte, a chave
tem de acompanhar, ou o documento sai com `dhEmi` de novembro e chave de outubro.
"""

import ast
import json
import pathlib
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave
from erpnext_brasil.fiscal.mdfe_montagem import montar_mdfe_de_dados
from erpnext_brasil.fiscal.relogio_politica import (
	ConfiguracaoRelogio,
	UltimaMedicao,
	deslocamento_a_aplicar,
)
from erpnext_brasil.fiscal.tempo_ntp import Medicao
from erpnext_brasil.tests.test_cte_montagem import _dados as _dados_cte
from erpnext_brasil.tests.test_cte_montagem import _sorteio_fixo
from erpnext_brasil.tests.test_mdfe_montagem import _dados as _dados_mdfe

AGORA = 1_760_000_000.0
RAIZ = pathlib.Path(__file__).resolve().parents[1]
FUSO = timezone(timedelta(hours=-4))


def _ultima(desvio_ms, *, confiavel=True, idade_s=30.0, motivo="") -> UltimaMedicao:
	medicao = Medicao(desvio_ms, confiavel, 3 if desvio_ms is not None else 0, 3, 4.0, motivo)

	return UltimaMedicao(medicao=medicao, medida_em=AGORA - idade_s)


LIGADA = ConfiguracaoRelogio(correcao_ligada=True)


class TestDeslocamentoAAplicar(unittest.TestCase):
	def test_desligada_por_padrao_nunca_aplica_nem_registra_motivo(self):
		correcao = deslocamento_a_aplicar(_ultima(3000.0), AGORA, ConfiguracaoRelogio())

		self.assertIsNone(correcao.segundos)
		self.assertEqual(correcao.motivo, "")

	def test_ligada_com_medicao_confiavel_soma_o_desvio_em_segundos(self):
		self.assertEqual(deslocamento_a_aplicar(_ultima(2500.0), AGORA, LIGADA).segundos, 2.5)

	def test_relogio_adiantado_subtrai(self):
		self.assertEqual(deslocamento_a_aplicar(_ultima(-2500.0), AGORA, LIGADA).segundos, -2.5)

	def test_ligada_sem_medicao_utilizavel_nao_aplica_e_diz_por_que(self):
		casos = {
			"ausente": None,
			"vencida": _ultima(3000.0, idade_s=10 * 3600),
			"nao confiavel": _ultima(3000.0, confiavel=False, motivo="as fontes divergem"),
			"nao medido": _ultima(None, confiavel=False, motivo="nenhuma das 3 fontes respondeu"),
		}

		for rotulo, ultima in casos.items():
			with self.subTest(caso=rotulo):
				correcao = deslocamento_a_aplicar(ultima, AGORA, LIGADA)

				self.assertIsNone(correcao.segundos)
				self.assertIn("correção do instante ligada", correcao.motivo)

	def test_o_desvio_zero_aplicado_e_diferente_de_nao_aplicar(self):
		"""Corrigir por 0 s é uma correção medida; `None` é "não houve correção"."""
		self.assertEqual(deslocamento_a_aplicar(_ultima(0.0), AGORA, LIGADA).segundos, 0.0)


class TestVirarDoMes(unittest.TestCase):
	"""5.3 — a chave e o `dhEmi` nascem do mesmo instante corrigido."""

	ANTES_DA_VIRADA = datetime(2026, 10, 31, 23, 59, 59, tzinfo=FUSO)

	def test_perto_da_virada_do_mes_a_chave_e_o_dhemi_continuam_no_mesmo_mes(self):
		corrigido = self.ANTES_DA_VIRADA + timedelta(seconds=2)  # relógio local 2 s atrasado

		self.assertEqual(corrigido.month, 11, "a premissa do teste: a correção cruza o mês")

		arvore, chave = montar_mdfe_de_dados(
			replace(_dados_mdfe(), emissao=corrigido), "42", sortear=_sorteio_fixo
		)
		dhemi = arvore["MDFe"]["infMDFe"]["ide"]["dhEmi"]

		self.assertTrue(dhemi.startswith("2026-11-01"), dhemi)
		self.assertEqual(chave[2:6], "2611", "AAMM da chave diverge do mês do dhEmi")
		self.assertEqual(ler_chave(chave).modelo, "58")

	def test_sem_correcao_a_chave_fica_em_outubro(self):
		arvore, chave = montar_mdfe_de_dados(
			replace(_dados_mdfe(), emissao=self.ANTES_DA_VIRADA), "42", sortear=_sorteio_fixo
		)

		self.assertTrue(arvore["MDFe"]["infMDFe"]["ide"]["dhEmi"].startswith("2026-10-31"))
		self.assertEqual(chave[2:6], "2610")

	def test_o_cte_tambem_acompanha_o_mes_corrigido(self):
		from erpnext_brasil.fiscal.cte_montagem import montar_cte_de_dados

		corrigido = self.ANTES_DA_VIRADA + timedelta(seconds=2)
		arvore, chave = montar_cte_de_dados(
			replace(_dados_cte(), emissao=corrigido), "42", sortear=_sorteio_fixo
		)

		self.assertTrue(arvore["CTe"]["infCte"]["ide"]["dhEmi"].startswith("2026-11-01"))
		self.assertEqual(chave[2:6], "2611")


def _arvore(modulo: str) -> ast.Module:
	return ast.parse((RAIZ / "integracao" / f"{modulo}.py").read_text(encoding="utf-8"))


class TestOInstanteViajaAteORegistro(unittest.TestCase):
	"""O deslocamento aplicado sai de `instante_de_emissao` e chega ao `Transmissao Fiscal`.

	Passa por argumento, não por `frappe.flags`: a dependência fica visível no código.
	"""

	def test_as_duas_emissoes_passam_o_momento_ao_mapeador_e_o_deslocamento_ao_registro(self):
		for modulo in ("emissao_nfe", "emissao_cte"):
			with self.subTest(modulo=modulo):
				codigo = ast.unparse(_arvore(modulo))

				self.assertIn("instante.momento", codigo)
				self.assertIn("instante.deslocamento_ms", codigo)
				self.assertIn("instante_de_emissao()", codigo)

	def test_o_mapeador_da_nfe_aceita_o_momento(self):
		funcao = next(
			n
			for n in ast.walk(_arvore("nfe_documento"))
			if isinstance(n, ast.FunctionDef) and n.name == "montar_nfe_do_documento"
		)

		self.assertIn("agora", [a.arg for a in funcao.args.args])

	def test_o_padrao_do_mapeador_continua_o_relogio_do_servidor(self):
		"""Sem `agora`, `agora_da_emissao()` — o comportamento de antes, para quem não passa nada."""
		codigo = ast.unparse(_arvore("nfe_documento"))

		self.assertIn("agora or agora_da_emissao()", codigo)

	def test_nao_ha_estado_escondido_em_flags(self):
		"""Só identificadores: o docstring cita `frappe.flags` justamente para explicar que não se usa."""
		usados = {n.attr for n in ast.walk(_arvore("instante_de_emissao")) if isinstance(n, ast.Attribute)}

		self.assertNotIn("flags", usados)
		self.assertNotIn("local", usados)

	def test_o_campo_do_registro_existe_e_e_somente_leitura(self):
		doctype = json.loads(
			(RAIZ / "registros_fiscais/doctype/transmissao_fiscal/transmissao_fiscal.json").read_text(
				encoding="utf-8"
			)
		)
		campo = next(f for f in doctype["fields"] if f["fieldname"] == "deslocamento_relogio_ms")

		self.assertEqual(campo["fieldtype"], "Float")
		self.assertEqual(campo["read_only"], 1)
		self.assertIn("deslocamento_relogio_ms", doctype["field_order"])

	def test_o_registro_distingue_sem_correcao_de_corrigido_em_zero(self):
		"""O Frappe grava 0 em campo numérico vazio; por isso há um `Check` ao lado do `Float`."""
		doctype = json.loads(
			(RAIZ / "registros_fiscais/doctype/transmissao_fiscal/transmissao_fiscal.json").read_text(
				encoding="utf-8"
			)
		)
		campo = next(f for f in doctype["fields"] if f["fieldname"] == "instante_corrigido")

		self.assertEqual(campo["fieldtype"], "Check")
		self.assertEqual(campo["read_only"], 1)

		for modulo in ("emissao_nfe", "emissao_cte"):
			with self.subTest(modulo=modulo):
				self.assertIn("'instante_corrigido'", ast.unparse(_arvore(modulo)))

	def test_os_dois_registradores_gravam_o_campo(self):
		for modulo in ("emissao_nfe", "emissao_cte"):
			with self.subTest(modulo=modulo):
				self.assertIn("'deslocamento_relogio_ms'", ast.unparse(_arvore(modulo)))


if __name__ == "__main__":
	unittest.main()
