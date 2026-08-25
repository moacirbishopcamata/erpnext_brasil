# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Conformidade dos nomes de tag com o XSD oficial da NF-e.

Origem do manifesto
-------------------
`elementos_nfe.json` lista todos os `xs:element name="..."` de `leiauteNFe_v4.00.xsd` e
`DFeTiposBasicos_v1.00.xsd`, extraídos do **Pacote de Liberação 010e_v1.02 (NT
2025.002)**, baixado do Portal Nacional da NF-e. São 598 nomes.

Por que um manifesto e não o XSD inteiro
----------------------------------------
Validar de verdade exigiria montar o XML completo — com emitente, destinatário,
assinatura — o que este app ainda não faz. O manifesto pega barato a falha que
efetivamente acontece na prática: **nome de tag digitado errado**. Um `vIBSUf` em vez de
`vIBSUF` não produz imposto errado, produz documento rejeitado, e nenhum teste de
aritmética o encontraria.

Este teste não substitui validar o XML final contra o XSD antes de emitir em produção —
ele garante que os nomes que este módulo escreve existem no layout.
"""

import json
import unittest
from decimal import Decimal
from pathlib import Path

from erpnext_brasil.fiscal.documento.ibs_cbs_xml import (
	grupo_ibscbs_item,
	grupo_totais_ibscbs,
)
from erpnext_brasil.fiscal.impostos.ibs_cbs import calcular_ibs_cbs

MANIFESTO = Path(__file__).resolve().parents[1] / "fiscal" / "documento" / "elementos_nfe.json"


def _tags(no, encontradas: set[str]) -> set[str]:
	"""Percorre a árvore e coleta todo nome de tag emitido."""
	if isinstance(no, dict):
		for chave, valor in no.items():
			encontradas.add(chave)
			_tags(valor, encontradas)

	return encontradas


class TestManifesto(unittest.TestCase):
	def setUp(self):
		self.elementos = set(json.loads(MANIFESTO.read_text(encoding="utf-8")))

	def test_manifesto_carrega(self):
		self.assertGreater(len(self.elementos), 500)

	def test_ancoras_conhecidas_estao_no_manifesto(self):
		# Se estas sumirem, o manifesto foi gerado do pacote errado.
		for tag in ("IBSCBS", "gIBSCBS", "pIBSUF", "vCBS", "cClassTrib", "IBSCBSTot"):
			with self.subTest(tag=tag):
				self.assertIn(tag, self.elementos)

	def test_todas_as_tags_do_item_existem_no_xsd(self):
		resultado = calcular_ibs_cbs(Decimal("1000.00"), ano=2026)
		grupo = grupo_ibscbs_item(resultado, cst="000", classificacao_tributaria="000001")

		desconhecidas = _tags(grupo, set()) - self.elementos

		self.assertEqual(desconhecidas, set(), f"tags fora do layout: {sorted(desconhecidas)}")

	def test_todas_as_tags_dos_totais_existem_no_xsd(self):
		itens = [calcular_ibs_cbs(Decimal("1000.00"), ano=2026)]
		totais = grupo_totais_ibscbs(itens)

		desconhecidas = _tags(totais, set()) - self.elementos

		self.assertEqual(desconhecidas, set(), f"tags fora do layout: {sorted(desconhecidas)}")

	def test_sufixo_tot_nao_existe_no_layout(self):
		"""Guarda contra a regressão que este teste encontrou.

		Fontes secundárias descreviam os totais como `gIBSUFTot`/`gIBSMunTot`. O XSD não
		tem esses nomes: dentro de `gIBS` os subgrupos repetem `gIBSUF` e `gIBSMun`.
		"""
		self.assertNotIn("gIBSUFTot", self.elementos)
		self.assertNotIn("gIBSMunTot", self.elementos)


class TestObrigatoriosDosTotais(unittest.TestCase):
	"""Em `gIBS` e `gCBS`, todo filho é obrigatório quando o grupo é informado."""

	def setUp(self):
		itens = [calcular_ibs_cbs(Decimal("1000.00"), ano=2026)]
		self.totais = grupo_totais_ibscbs(itens)["IBSCBSTot"]

	def test_gibs_traz_todos_os_filhos(self):
		self.assertEqual(
			set(self.totais["gIBS"]),
			{"gIBSUF", "gIBSMun", "vIBS", "vCredPres", "vCredPresCondSus"},
		)

	def test_gibsuf_traz_dif_e_devtrib(self):
		self.assertEqual(set(self.totais["gIBS"]["gIBSUF"]), {"vDif", "vDevTrib", "vIBSUF"})

	def test_gibsmun_traz_dif_e_devtrib(self):
		self.assertEqual(set(self.totais["gIBS"]["gIBSMun"]), {"vDif", "vDevTrib", "vIBSMun"})

	def test_gcbs_traz_todos_os_filhos(self):
		self.assertEqual(
			set(self.totais["gCBS"]),
			{"vDif", "vDevTrib", "vCBS", "vCredPres", "vCredPresCondSus"},
		)

	def test_campos_nao_calculados_saem_zerados_e_nao_omitidos(self):
		self.assertEqual(self.totais["gIBS"]["vCredPres"], "0.00")
		self.assertEqual(self.totais["gCBS"]["vDif"], "0.00")


class TestFormatoDosValores(unittest.TestCase):
	"""Os padrões do XSD: alíquota admite 2 a 4 decimais, valor exige exatamente 2."""

	def setUp(self):
		resultado = calcular_ibs_cbs(Decimal("1000.00"), ano=2026)
		self.grupo = grupo_ibscbs_item(resultado, cst="000", classificacao_tributaria="000001")[
			"IBSCBS"
		]["gIBSCBS"]

	def test_aliquota_com_quatro_decimais(self):
		for caminho in (("gIBSUF", "pIBSUF"), ("gIBSMun", "pIBSMun"), ("gCBS", "pCBS")):
			with self.subTest(caminho=caminho):
				texto = self.grupo[caminho[0]][caminho[1]]
				self.assertRegex(texto, r"^\d+\.\d{4}$")

	def test_valor_com_dois_decimais(self):
		for caminho in (("vBC",), ("vIBS",), ("gCBS", "vCBS")):
			with self.subTest(caminho=caminho):
				no = self.grupo
				for parte in caminho:
					no = no[parte]

				self.assertRegex(no, r"^\d+\.\d{2}$")


if __name__ == "__main__":
	unittest.main()
