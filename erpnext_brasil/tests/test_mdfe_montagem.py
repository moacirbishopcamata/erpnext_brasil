# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da montagem do MDF-e a partir de dados já extraídos (`fiscal/mdfe_montagem.py`).

O que se trava aqui é a **composição**: que grupo vem depois de qual, que o número alocado entra na
chave, que o manifesto agrupa os documentos por município de descarga e que cada dado faltante é
recusado **nomeando** o que falta. Os montadores de cada grupo têm teste próprio
(`test_mdfe.py`, `test_mdfe_rodoviario.py`); aqui entra o encadeamento.

Teste-âncora: `test_recusa_sem_documento_algum_nao_consome_o_numero`. Um manifesto sem carga não
manifesta nada, e o número da série 58 é sequencial — gastá-lo com algo que nem chegou a ser
montado deixa uma lacuna que só se desfaz por inutilização de faixa.
"""

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave, montar_chave
from erpnext_brasil.fiscal.mdfe import (
	Emitente,
	MdfeInvalido,
	MunicipioCarrega,
	MunicipioDescarga,
)
from erpnext_brasil.fiscal.mdfe_montagem import (
	DadosMdfe,
	montar_mdfe_alocando_numero,
	montar_mdfe_de_dados,
)
from erpnext_brasil.fiscal.mdfe_rodoviario import RODADO_CAVALO_MECANICO, Condutor, Veiculo

ENDERECO = {
	"xLgr": "Rua A",
	"nro": "10",
	"xBairro": "Centro",
	"cMun": "1100205",
	"xMun": "Porto Velho",
	"CEP": "76800000",
	"UF": "RO",
}
CPF_VALIDO = "11144477735"


def _chave_nfe(numero: str) -> str:
	return montar_chave("11", "2610", "11222333000181", "55", "1", numero, "1", "12345678")


def _sorteio_fixo(_numero):
	return "12345678"


def _veiculo(**mudancas) -> Veiculo:
	base = {
		"placa": "ABC1234",
		"tara": "8500",
		"tipo_rodado": RODADO_CAVALO_MECANICO,
		"condutores": [Condutor(nome="João da Silva", cpf=CPF_VALIDO)],
	}
	return Veiculo(**{**base, **mudancas})


def _dados(**mudancas) -> DadosMdfe:
	base = {
		"emitente": Emitente(
			cnpj_cpf="11222333000181",
			nome="Transportadora Teste Ltda",
			endereco=ENDERECO,
			inscricao_estadual="123456789",
		),
		"serie": "1",
		"emissao": datetime(2026, 10, 9, 9, 30, 0, tzinfo=timezone(timedelta(hours=-4))),
		"uf_inicio": "RO",
		"uf_fim": "RO",
		"municipios_carrega": [MunicipioCarrega(codigo="1100205", nome="Porto Velho")],
		"municipios_descarga": [
			MunicipioDescarga(codigo="1100122", nome="Ji-Paraná", chaves_nfe=[_chave_nfe("10")])
		],
		"rntrc": "12345678",
		"veiculo_tracao": _veiculo(),
		"valor_carga": Decimal("5000.00"),
		"peso_carga": Decimal("1200.5"),
	}
	return DadosMdfe(**{**base, **mudancas})


def _montar(numero="42", **mudancas):
	return montar_mdfe_de_dados(_dados(**mudancas), numero, sortear=_sorteio_fixo)


def _info(**mudancas) -> dict:
	return _montar(**mudancas)[0]["MDFe"]["infMDFe"]


class TestMontagemValida(unittest.TestCase):
	def test_os_grupos_saem_na_ordem_do_leiaute(self):
		grupos = [k for k in _info() if not k.startswith("@")]

		self.assertEqual(grupos, ["ide", "emit", "infModal", "infDoc", "tot"])

	def test_o_numero_alocado_entra_na_chave_e_no_ide(self):
		arvore, chave = _montar(numero="42")
		lida = ler_chave(chave)

		self.assertEqual(lida.modelo, "58")
		self.assertEqual(lida.numero.lstrip("0"), "42")
		self.assertEqual(arvore["MDFe"]["infMDFe"]["ide"]["nMDF"], "42")
		self.assertEqual(arvore["MDFe"]["infMDFe"]["@Id"], f"MDFe{chave}")
		self.assertEqual(arvore["MDFe"]["infMDFe"]["ide"]["cDV"], lida.dv)

	def test_emitente_e_tipo_de_carga_propria_por_padrao(self):
		self.assertEqual(_info()["ide"]["tpEmit"], "2")

	def test_agrupa_por_municipio_de_descarga_preservando_a_ordem(self):
		municipios = [
			MunicipioDescarga(
				codigo="1100122", nome="Ji-Paraná", chaves_nfe=[_chave_nfe("10"), _chave_nfe("11")]
			),
			MunicipioDescarga(codigo="1100205", nome="Porto Velho", chaves_nfe=[_chave_nfe("12")]),
		]

		descarga = _info(municipios_descarga=municipios)["infDoc"]["infMunDescarga"]

		self.assertEqual([m["cMunDescarga"] for m in descarga], ["1100122", "1100205"])
		self.assertEqual(len(descarga[0]["infNFe"]), 2)
		self.assertEqual(len(descarga[1]["infNFe"]), 1)

	def test_o_total_de_nfe_e_a_soma_dos_municipios(self):
		municipios = [
			MunicipioDescarga(
				codigo="1100122", nome="Ji-Paraná", chaves_nfe=[_chave_nfe("10"), _chave_nfe("11")]
			),
			MunicipioDescarga(codigo="1100205", nome="Porto Velho", chaves_nfe=[_chave_nfe("12")]),
		]

		tot = _info(municipios_descarga=municipios)["tot"]

		self.assertEqual(tot["qNFe"], "3")
		self.assertNotIn("qCTe", tot)
		self.assertEqual((tot["vCarga"], tot["cUnid"], tot["qCarga"]), ("5000.00", "01", "1200.5"))

	def test_rntrc_veiculo_e_condutor_vao_no_modal(self):
		modal = _info()["infModal"]

		self.assertEqual(modal["@versaoModal"], "3.00")
		self.assertEqual(modal["rodo"]["infANTT"]["RNTRC"], "12345678")
		self.assertEqual(modal["rodo"]["veicTracao"]["placa"], "ABC1234")
		self.assertEqual(modal["rodo"]["veicTracao"]["condutor"][0]["CPF"], CPF_VALIDO)


class TestRecusas(unittest.TestCase):
	"""Uma recusa por caso, cada uma nomeando o dado faltante (`campo` e mensagem)."""

	def _recusa(self, campo: str, trecho: str, **mudancas):
		with self.assertRaises(MdfeInvalido) as contexto:
			_montar(**mudancas)

		self.assertEqual(contexto.exception.campo, campo)
		self.assertIn(trecho, str(contexto.exception))

	def test_sem_municipio_de_descarga_nada_a_manifestar(self):
		self._recusa("municipios_descarga", "nenhum documento fiscal", municipios_descarga=[])

	def test_municipio_de_descarga_sem_documento(self):
		vazio = MunicipioDescarga(codigo="1100122", nome="Ji-Paraná")

		self._recusa("municipios_descarga", "Ji-Paraná", municipios_descarga=[vazio])

	def test_sem_municipio_de_carregamento(self):
		self._recusa("municipios_carrega", "infMunCarrega", municipios_carrega=[])

	def test_valor_da_carga_nao_positivo(self):
		self._recusa("valor_carga", "vCarga", valor_carga=Decimal("0"))

	def test_peso_da_carga_nao_positivo(self):
		self._recusa("peso_carga", "qCarga", peso_carga=Decimal("0"))

	def test_sem_rntrc(self):
		self._recusa("rntrc", "RNTRC", rntrc="")

	def test_veiculo_sem_condutor(self):
		self._recusa("veiculo_tracao", "condutor", veiculo_tracao=_veiculo(condutores=[]))

	def test_veiculo_sem_placa(self):
		self._recusa("veiculo_tracao", "placa", veiculo_tracao=_veiculo(placa=""))

	def test_emitente_pessoa_fisica_nao_gera_chave(self):
		emitente = Emitente(cnpj_cpf=CPF_VALIDO, nome="Autônomo", endereco=ENDERECO)

		self._recusa("cnpj_cpf", "CPF", emitente=emitente)

	def test_endereco_do_emitente_incompleto_nomeia_o_que_falta(self):
		incompleto = {**ENDERECO, "cMun": "", "CEP": ""}
		emitente = Emitente(cnpj_cpf="11222333000181", nome="X Ltda", endereco=incompleto)

		self._recusa("emitente", "cMun, CEP", emitente=emitente)

	def test_data_de_emissao_sem_fuso(self):
		self._recusa("emissao", "fuso", emissao=datetime(2026, 10, 9, 9, 30))

	def test_modal_que_nao_e_rodoviario(self):
		self._recusa("modal", "rodoviário", modal="2")

	def test_uf_desconhecida(self):
		self._recusa("uf", "UF", uf_fim="XX")

	def test_numero_invalido(self):
		with self.assertRaises(MdfeInvalido) as contexto:
			_montar(numero="abc")

		self.assertEqual(contexto.exception.campo, "numero")


class TestAlocacaoDoNumero(unittest.TestCase):
	def test_recusa_sem_documento_algum_nao_consome_o_numero(self):
		alocacoes = []

		with self.assertRaises(MdfeInvalido):
			montar_mdfe_alocando_numero(
				_dados(municipios_descarga=[]), lambda: alocacoes.append(1) or "7", sortear=_sorteio_fixo
			)

		self.assertEqual(alocacoes, [], "a série foi tocada por um manifesto que nem foi montado")

	def test_aloca_uma_vez_e_o_numero_entra_na_chave(self):
		alocacoes = []

		def alocar():
			alocacoes.append(1)

			return "7"

		arvore, chave = montar_mdfe_alocando_numero(_dados(), alocar, sortear=_sorteio_fixo)

		self.assertEqual(len(alocacoes), 1)
		self.assertEqual(arvore["MDFe"]["infMDFe"]["ide"]["nMDF"], "7")
		self.assertEqual(ler_chave(chave).numero.lstrip("0"), "7")

	def test_falha_ao_alocar_nao_devolve_arvore(self):
		def alocar():
			raise RuntimeError("série sem número livre")

		with self.assertRaises(RuntimeError):
			montar_mdfe_alocando_numero(_dados(), alocar, sortear=_sorteio_fixo)


if __name__ == "__main__":
	unittest.main()
