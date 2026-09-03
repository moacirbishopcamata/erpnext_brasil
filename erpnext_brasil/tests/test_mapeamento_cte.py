# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes de `integracao/mapeamento_cte.py` — agrupamento de referências fiscais por
município de descarga, a costura entre dados do ERPNext e `fiscal.mdfe.montar_infdoc`."""

import unittest

from erpnext_brasil.fiscal.mdfe import MunicipioDescarga
from erpnext_brasil.integracao.mapeamento_cte import ReferenciaDocumentoFiscal, agrupar_por_municipio_descarga


def _ref(
	chave: str, modelo: str, municipio_codigo="3550308", municipio_nome="São Paulo"
) -> ReferenciaDocumentoFiscal:
	return ReferenciaDocumentoFiscal(
		chave=chave, modelo=modelo, municipio_codigo=municipio_codigo, municipio_nome=municipio_nome
	)


class TestAgruparPorMunicipioDescarga(unittest.TestCase):
	def test_uma_referencia_de_nfe(self):
		grupo = agrupar_por_municipio_descarga([_ref("chave-nfe-1", "55")])

		self.assertEqual(
			grupo, [MunicipioDescarga(codigo="3550308", nome="São Paulo", chaves_nfe=["chave-nfe-1"])]
		)

	def test_uma_referencia_de_cte(self):
		grupo = agrupar_por_municipio_descarga([_ref("chave-cte-1", "57")])

		self.assertEqual(
			grupo, [MunicipioDescarga(codigo="3550308", nome="São Paulo", chaves_cte=["chave-cte-1"])]
		)

	def test_mesmo_municipio_agrupa_nfe_e_cte_juntos(self):
		grupo = agrupar_por_municipio_descarga([_ref("chave-nfe-1", "55"), _ref("chave-cte-1", "57")])

		self.assertEqual(len(grupo), 1)
		self.assertEqual(grupo[0].chaves_nfe, ["chave-nfe-1"])
		self.assertEqual(grupo[0].chaves_cte, ["chave-cte-1"])

	def test_municipios_diferentes_preserva_ordem_de_primeira_aparicao(self):
		referencias = [
			_ref("chave-1", "55", "3304557", "Rio de Janeiro"),
			_ref("chave-2", "55", "3550308", "São Paulo"),
			_ref("chave-3", "55", "3304557", "Rio de Janeiro"),
		]

		grupo = agrupar_por_municipio_descarga(referencias)

		self.assertEqual([m.codigo for m in grupo], ["3304557", "3550308"])
		self.assertEqual(grupo[0].chaves_nfe, ["chave-1", "chave-3"])

	def test_lista_vazia_devolve_lista_vazia(self):
		self.assertEqual(agrupar_por_municipio_descarga([]), [])

	def test_devolve_municipiodescarga_de_verdade_nao_so_um_dict_parecido(self):
		grupo = agrupar_por_municipio_descarga([_ref("chave-1", "55")])

		self.assertIsInstance(grupo[0], MunicipioDescarga)


if __name__ == "__main__":
	unittest.main()
