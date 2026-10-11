# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes do modelo (instância, estados) e do registro das instâncias, nos três formatos de persistência.

O registro é a regra de identidade e de portas sobre a porta de persistência. Por isso a **mesma bateria roda contra
memória, JSON e SQLite** (paridade), e há testes de **costura** (grava por um registro, relê por outro, independente)
e de **concorrência** (vários Sodas criando instâncias ao mesmo tempo não repetem porta nem UUID).
"""

import dataclasses
import tempfile
import threading
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from erpnext_brasil.persistencia.json_arquivo import RepositorioJson
from erpnext_brasil.persistencia.memoria import RepositorioEmMemoria
from erpnext_brasil.persistencia.sqlite_arquivo import RepositorioSqlite
from erpnext_brasil.soda import identidade as ident
from erpnext_brasil.soda import portas as pt
from erpnext_brasil.soda import registro as reg
from erpnext_brasil.soda.modelo import (
	TRANSICOES,
	TRANSICOES_DA_CONCILIACAO,
	Aposentada,
	DocumentoInvalido,
	Estado,
	Instancia,
)

AGORA = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
UUID_A = "12345678-1234-4234-8234-123456789abc"
UUID_B = "87654321-4321-4321-8321-cba987654321"


def uuids_em_sequencia(*valores: str):
	fila = iter(valores)

	return lambda: uuid.UUID(next(fila))


def documento_de(**mudancas):
	base = {
		"uuid": UUID_A,
		"descritivo": "NF-e em homologação",
		"host": "nf-e-em-homologacao-12345678.localhost",
		"porta": 8100,
		"estado": "parada",
		"perfil_de_banco": "padrao",
		"tipo_de_banco": "mariadb",
		"aplicativos": ["erpnext", "erpnext_brasil"],
		"criada_em": AGORA.isoformat(),
	}
	base.update(mudancas)

	return base


class TestModelo(unittest.TestCase):
	def test_instancia_vai_e_volta_pelo_documento(self):
		instancia = Instancia.de_documento(documento_de(expoe_na_rede=True))

		self.assertEqual(Instancia.de_documento(instancia.para_documento()), instancia)
		self.assertEqual(instancia.abreviado, "12345678")
		self.assertTrue(instancia.expoe_na_rede)

	def test_instancia_e_imutavel(self):
		instancia = Instancia.de_documento(documento_de())

		with self.assertRaises(dataclasses.FrozenInstanceError):
			instancia.porta = 9999

	def test_campo_desconhecido_e_ignorado(self):
		instancia = Instancia.de_documento(documento_de(campo_de_versao_futura="x"))
		self.assertEqual(instancia.descritivo, "NF-e em homologação")

	def test_expoe_na_rede_so_vale_se_for_verdadeiro_de_fato(self):
		for valor in ("true", 1, None):
			self.assertFalse(Instancia.de_documento(documento_de(expoe_na_rede=valor)).expoe_na_rede)

	def test_chave_ignora_acento_e_caixa(self):
		a = Instancia.de_documento(documento_de(descritivo="Homologação"))
		b = Instancia.de_documento(documento_de(descritivo="HOMOLOGACAO"))
		self.assertEqual(a.chave, b.chave)

	def test_documentos_malformados_sao_recusados(self):
		ruins = {
			"não é objeto": "texto",
			"sem uuid": documento_de(uuid=None),
			"uuid ruim": documento_de(uuid="x"),
			"descritivo curto": documento_de(descritivo="ab"),
			"porta texto": documento_de(porta="8100"),
			"porta bool": documento_de(porta=True),
			"porta zero": documento_de(porta=0),
			"porta grande": documento_de(porta=70000),
			"estado desconhecido": documento_de(estado="hibernando"),
			"tipo de banco": documento_de(tipo_de_banco="oracle"),
			"perfil ruim": documento_de(perfil_de_banco="com espaço"),
			"aplicativos vazios": documento_de(aplicativos=[]),
			"aplicativos não lista": documento_de(aplicativos="erpnext"),
			"aplicativo ruim": documento_de(aplicativos=["ERP Next"]),
			"host vazio": documento_de(host=""),
		}

		for nome, ruim in ruins.items():
			with self.subTest(caso=nome), self.assertRaises(DocumentoInvalido):
				Instancia.de_documento(ruim)

	def test_aposentada_vai_e_volta(self):
		rastro = Aposentada(UUID_A, "Antiga", AGORA.isoformat())
		self.assertEqual(Aposentada.de_documento(rastro.para_documento()), rastro)

	def test_aposentada_malformada_e_recusada(self):
		for ruim in ("texto", {"uuid": "x"}, {"uuid": UUID_A}, {"uuid": UUID_A, "ultimo_descritivo": "x"}):
			with self.subTest(ruim=str(ruim)), self.assertRaises(DocumentoInvalido):
				Aposentada.de_documento(ruim)

	def test_as_tabelas_de_transicao_cobrem_todos_os_estados(self):
		self.assertEqual(set(TRANSICOES), set(Estado))
		self.assertEqual(set(TRANSICOES_DA_CONCILIACAO), set(Estado))
		self.assertEqual(
			TRANSICOES[Estado.CRIACAO_INTERROMPIDA], frozenset(), "criação interrompida só se desfaz"
		)


class ContratoDoRegistro:
	"""Bateria única; cada formato a herda e diz como criar e reabrir o repositório."""

	COMPARTILHA = True

	def novo_repositorio(self):
		raise NotImplementedError

	def reabrir_repositorio(self):
		raise NotImplementedError

	def novo_registro(self, repositorio=None, **opcoes):
		padrao = {
			"livre": lambda porta: True,
			"agora": lambda: AGORA,
		}
		padrao.update(opcoes)

		return reg.Registro(repositorio or self.repo, **padrao)

	def setUp(self):
		self.repo = self.novo_repositorio()
		self.registro = self.novo_registro()

	def criar(self, descritivo="NF-e em homologação", **opcoes):
		padrao = {"perfil_de_banco": "padrao", "tipo_de_banco": "mariadb"}
		padrao.update(opcoes)

		return self.registro.criar(descritivo, **padrao)

	# ------------------------------------------------------------------ criar

	def test_criar_grava_a_instancia_em_criando_com_os_aplicativos_obrigatorios(self):
		instancia = self.criar()

		self.assertEqual(instancia.estado, Estado.CRIANDO)
		self.assertEqual(instancia.aplicativos, ("erpnext", "erpnext_brasil"))
		self.assertEqual(instancia.porta, 8100)
		self.assertEqual(instancia.criada_em, AGORA.isoformat())
		self.assertEqual(instancia.host, ident.nome_do_host("NF-e em homologação", instancia.uuid))
		self.assertEqual(self.registro.obter(instancia.uuid), instancia)

	def test_o_que_um_registro_grava_o_outro_le(self):
		"""Teste na costura: grava por um caminho e relê por outro, independente."""
		criada = self.criar()

		outro = self.novo_registro(self.reabrir_repositorio())

		self.assertEqual(outro.obter(criada.uuid), criada)
		self.assertEqual(outro.listar(), [criada])

	def test_aplicativos_opcionais_vem_depois_dos_obrigatorios_sem_repeticao(self):
		instancia = self.criar(aplicativos_opcionais=("hrms", "healthcare", "hrms"))
		self.assertEqual(instancia.aplicativos, ("erpnext", "erpnext_brasil", "hrms", "healthcare"))

	def test_entradas_invalidas_sao_recusadas_antes_de_gravar(self):
		casos = [
			("descritivo", dict(descritivo="ab"), ident.DescritivoInvalido),
			("tipo de banco", dict(tipo_de_banco="oracle"), ValueError),
			("perfil de banco", dict(perfil_de_banco="com espaço"), ValueError),
			("aplicativo opcional", dict(aplicativos_opcionais=("sap",)), ValueError),
		]

		for nome, opcoes, erro in casos:
			with self.subTest(caso=nome), self.assertRaises(erro):
				self.criar(**opcoes)

		self.assertEqual(self.registro.listar(), [])

	def test_descritivo_repetido_ignora_caixa_e_acento(self):
		primeira = self.criar("Homologação")

		with self.assertRaises(reg.DescritivoRepetido) as contexto:
			self.criar("HOMOLOGACAO")

		self.assertEqual(contexto.exception.existente, primeira)
		self.assertIn("ignora maiúsculas e acentos", str(contexto.exception))
		self.assertEqual(len(self.registro.listar()), 1)

	def test_cada_instancia_ganha_a_proxima_porta_livre(self):
		portas = [self.criar(f"Instância {n}").porta for n in range(3)]
		self.assertEqual(portas, [8100, 8101, 8102])

	def test_porta_ocupada_no_sistema_e_pulada(self):
		registro = self.novo_registro(livre=lambda porta: porta != 8100)
		instancia = registro.criar("Pulando", perfil_de_banco="padrao", tipo_de_banco="mariadb")
		self.assertEqual(instancia.porta, 8101)

	def test_porta_escolhida_e_respeitada_ou_recusada(self):
		escolhida = self.criar("Escolhida", porta=8555)
		self.assertEqual(escolhida.porta, 8555)

		with self.assertRaises(pt.PortaRecusada) as contexto:
			self.criar("Outra", porta=8555)

		self.assertIn("Escolhida", contexto.exception.motivo)

		with self.assertRaises(pt.PortaRecusada):
			self.criar("Reservada", porta=3306)

	def test_porta_escolhida_ocupada_usa_o_quem_ocupa_padrao(self):
		registro = self.novo_registro(livre=lambda porta: porta != 8600)

		with self.assertRaises(pt.PortaRecusada) as contexto:
			registro.criar("Ocupada", perfil_de_banco="padrao", tipo_de_banco="mariadb", porta=8600)

		self.assertIn("outro programa", contexto.exception.motivo)

	def test_relogio_e_gerador_padrao_produzem_data_com_fuso_e_uuid_valido(self):
		registro = reg.Registro(self.repo, livre=lambda porta: True)
		instancia = registro.criar("Padrões", perfil_de_banco="padrao", tipo_de_banco="postgres")

		self.assertIsNotNone(datetime.fromisoformat(instancia.criada_em).tzinfo)
		self.assertEqual(ident.normalizar_uuid(instancia.uuid), instancia.uuid)
		self.assertEqual(instancia.tipo_de_banco, "postgres")

	def test_exposicao_na_rede_e_explicita(self):
		self.assertFalse(self.criar("Local").expoe_na_rede)
		self.assertTrue(self.criar("Exposta", expoe_na_rede=True).expoe_na_rede)

	# ------------------------------------------------------------------ UUID

	def test_colisao_de_uuid_e_tratada_e_contada(self):
		registro = self.novo_registro(gerar_uuid=uuids_em_sequencia(UUID_A, UUID_A, UUID_B))
		primeira = registro.criar("Primeira", perfil_de_banco="padrao", tipo_de_banco="mariadb")
		segunda = registro.criar("Segunda", perfil_de_banco="padrao", tipo_de_banco="mariadb")

		self.assertEqual((primeira.uuid, segunda.uuid), (UUID_A, UUID_B))
		self.assertEqual(registro.colisoes_de_uuid(), 1)

	def test_uuid_de_instancia_removida_nunca_volta(self):
		registro = self.novo_registro(gerar_uuid=uuids_em_sequencia(UUID_A, UUID_A, UUID_B))
		removida = registro.criar("Removida", perfil_de_banco="padrao", tipo_de_banco="mariadb")
		registro.mudar_estado(removida.uuid, Estado.PARADA)
		registro.aposentar(removida.uuid)

		nova = registro.criar("Nova", perfil_de_banco="padrao", tipo_de_banco="mariadb")

		self.assertEqual(nova.uuid, UUID_B)
		self.assertNotEqual(nova.uuid, removida.uuid)

	def test_host_repetido_por_trecho_de_uuid_igual_e_evitado(self):
		irmao = "12345678-aaaa-4aaa-8aaa-aaaaaaaaaaaa"  # mesmo trecho de 8 caracteres de UUID_A
		registro = self.novo_registro(gerar_uuid=uuids_em_sequencia(UUID_A, irmao, UUID_B))
		primeira = registro.criar("A B", perfil_de_banco="padrao", tipo_de_banco="mariadb")
		segunda = registro.criar("a-b", perfil_de_banco="padrao", tipo_de_banco="mariadb")

		self.assertEqual(primeira.host, "a-b-12345678.localhost")
		self.assertNotEqual(segunda.host, primeira.host)
		self.assertEqual(segunda.uuid, UUID_B)

	# ------------------------------------------------------------------ renomear

	def test_renomear_muda_so_o_descritivo(self):
		original = self.criar("Antes")
		renomeada = self.registro.renomear(original.uuid, "Depois")

		self.assertEqual(renomeada.descritivo, "Depois")
		self.assertEqual(
			(renomeada.uuid, renomeada.host, renomeada.porta), (original.uuid, original.host, original.porta)
		)
		self.assertEqual(self.registro.obter(original.uuid).descritivo, "Depois")

	def test_renomear_para_um_nome_em_uso_e_recusado_mas_para_o_proprio_com_outra_caixa_nao(self):
		a = self.criar("Alfa")
		self.criar("Beta")

		with self.assertRaises(reg.DescritivoRepetido):
			self.registro.renomear(a.uuid, "BETA")

		self.assertEqual(self.registro.renomear(a.uuid, "ALFA").descritivo, "ALFA")

	def test_renomear_instancia_inexistente(self):
		with self.assertRaises(reg.InstanciaInexistente):
			self.registro.renomear(UUID_A, "Qualquer")

	def test_descritivo_de_instancia_removida_fica_livre(self):
		removida = self.criar("Reaproveitado")
		self.registro.mudar_estado(removida.uuid, Estado.PARADA)
		self.registro.aposentar(removida.uuid)

		self.assertEqual(self.criar("Reaproveitado").descritivo, "Reaproveitado")

	# ------------------------------------------------------------------ estados

	def test_ciclo_de_vida_pelas_acoes_do_usuario(self):
		instancia = self.criar()

		for estado in (Estado.PARADA, Estado.SUBINDO, Estado.NO_AR, Estado.PARADA):
			instancia = self.registro.mudar_estado(instancia.uuid, estado)
			self.assertEqual(instancia.estado, estado)

	def test_transicao_invalida_e_recusada(self):
		instancia = self.criar()

		with self.assertRaises(reg.TransicaoInvalida) as contexto:
			self.registro.mudar_estado(instancia.uuid, Estado.NO_AR)

		self.assertIn("criando", str(contexto.exception))
		self.assertEqual(self.registro.obter(instancia.uuid).estado, Estado.CRIANDO)

	def test_repetir_o_mesmo_estado_e_idempotente(self):
		instancia = self.criar()
		self.registro.mudar_estado(instancia.uuid, Estado.PARADA)

		self.assertEqual(self.registro.mudar_estado(instancia.uuid, Estado.PARADA).estado, Estado.PARADA)

	def test_a_conciliacao_pode_constatar_o_que_o_usuario_nao_pode_pedir(self):
		instancia = self.criar()
		self.registro.mudar_estado(instancia.uuid, Estado.PARADA)

		with self.assertRaises(reg.TransicaoInvalida):
			self.registro.mudar_estado(instancia.uuid, Estado.NO_AR)

		self.assertEqual(
			self.registro.mudar_estado(instancia.uuid, Estado.NO_AR, constatado=True).estado, Estado.NO_AR
		)
		self.assertEqual(
			self.registro.mudar_estado(instancia.uuid, Estado.CAIU, constatado=True).estado, Estado.CAIU
		)

		with self.assertRaises(reg.TransicaoInvalida):
			self.registro.mudar_estado(instancia.uuid, Estado.CRIANDO, constatado=True)

	def test_mudar_estado_de_instancia_inexistente(self):
		with self.assertRaises(reg.InstanciaInexistente):
			self.registro.mudar_estado(UUID_A, Estado.PARADA)

	def test_limite_de_instancias_no_ar(self):
		a, b = self.criar("Alfa"), self.criar("Beta")

		for instancia in (a, b):
			self.registro.mudar_estado(instancia.uuid, Estado.PARADA)

		self.registro.exigir_vaga_para_subir(2)
		self.registro.mudar_estado(a.uuid, Estado.SUBINDO)
		self.registro.exigir_vaga_para_subir(2)
		self.registro.mudar_estado(b.uuid, Estado.SUBINDO)

		with self.assertRaises(reg.LimiteDeInstancias) as contexto:
			self.registro.exigir_vaga_para_subir(2)

		self.assertIn("consome memória", str(contexto.exception))

	# ------------------------------------------------------------------ remover

	def test_aposentar_remove_a_instancia_e_guarda_o_rastro(self):
		instancia = self.criar("Vai embora")
		self.registro.mudar_estado(instancia.uuid, Estado.PARADA)

		rastro = self.registro.aposentar(instancia.uuid)

		self.assertEqual((rastro.uuid, rastro.ultimo_descritivo), (instancia.uuid, "Vai embora"))
		self.assertIsNone(self.registro.obter(instancia.uuid))
		self.assertEqual(self.registro.aposentadas(), [rastro])
		self.assertEqual(self.registro.portas_alocadas(), {})

	def test_instancia_no_ar_ou_subindo_ou_criando_nao_se_remove(self):
		instancia = self.criar()

		with self.assertRaises(reg.OperacaoNaoPermitida):
			self.registro.aposentar(instancia.uuid)  # criando

		self.registro.mudar_estado(instancia.uuid, Estado.PARADA)
		self.registro.mudar_estado(instancia.uuid, Estado.SUBINDO)

		with self.assertRaises(reg.OperacaoNaoPermitida) as contexto:
			self.registro.aposentar(instancia.uuid)

		self.assertIn("pare-a antes", str(contexto.exception))
		self.registro.mudar_estado(instancia.uuid, Estado.NO_AR)

		with self.assertRaises(reg.OperacaoNaoPermitida):
			self.registro.aposentar(instancia.uuid)

		self.assertIsNotNone(self.registro.obter(instancia.uuid))

	def test_aposentar_inexistente(self):
		with self.assertRaises(reg.InstanciaInexistente):
			self.registro.aposentar(UUID_A)

	def test_descartar_criacao_libera_porta_e_nome_sem_aposentar_o_uuid(self):
		instancia = self.criar("Falhou")
		self.registro.descartar_criacao(instancia.uuid)

		self.assertIsNone(self.registro.obter(instancia.uuid))
		self.assertEqual(self.registro.aposentadas(), [])
		self.assertEqual(self.registro.portas_alocadas(), {})
		self.assertEqual(self.criar("Falhou").porta, 8100)

	def test_descartar_criacao_interrompida(self):
		instancia = self.criar()
		self.registro.mudar_estado(instancia.uuid, Estado.CRIACAO_INTERROMPIDA, constatado=True)
		self.registro.descartar_criacao(instancia.uuid)
		self.assertEqual(self.registro.listar(), [])

	def test_descartar_criacao_so_vale_para_criacao(self):
		instancia = self.criar()
		self.registro.mudar_estado(instancia.uuid, Estado.PARADA)

		with self.assertRaises(reg.OperacaoNaoPermitida):
			self.registro.descartar_criacao(instancia.uuid)

	# ------------------------------------------------------------------ consultas

	def test_consultas_por_uuid_e_por_descritivo(self):
		instancia = self.criar("Homologação")

		self.assertEqual(self.registro.por_descritivo("HOMOLOGACAO"), instancia)
		self.assertIsNone(self.registro.por_descritivo("Outra"))
		self.assertIsNone(self.registro.obter(UUID_B))
		self.assertEqual(self.registro.obter(instancia.uuid.upper()), instancia)

		with self.assertRaises(ident.UuidInvalido):
			self.registro.obter("não é uuid")

	def test_listar_vem_ordenado_pelo_descritivo(self):
		for nome in ("Charlie", "alfa", "Bravo"):
			self.criar(nome)

		self.assertEqual([i.descritivo for i in self.registro.listar()], ["alfa", "Bravo", "Charlie"])

	def test_quem_le_recebe_instancia_imutavel_e_fresca(self):
		instancia = self.criar()
		lida = self.registro.obter(instancia.uuid)

		with self.assertRaises(dataclasses.FrozenInstanceError):
			lida.estado = Estado.NO_AR

		self.assertEqual(self.registro.obter(instancia.uuid).estado, Estado.CRIANDO)

	# ------------------------------------------------------------------ esquema

	def test_versao_do_esquema_padrao_e_a_conhecida(self):
		self.assertEqual(self.registro.versao_do_esquema(), reg.ESQUEMA)
		self.assertEqual(self.registro.colisoes_de_uuid(), 0)

	def test_registro_mais_novo_nao_e_gravado_mas_e_lido(self):
		instancia = self.criar()
		self.repo.gravar("meta", "esquema", {"versao_esquema": 99})

		self.assertEqual(self.registro.versao_do_esquema(), 99)
		self.assertEqual(self.registro.obter(instancia.uuid), instancia)

		for operacao in (
			lambda: self.criar("Nova"),
			lambda: self.registro.renomear(instancia.uuid, "Outro"),
			lambda: self.registro.mudar_estado(instancia.uuid, Estado.PARADA),
			lambda: self.registro.aposentar(instancia.uuid),
			lambda: self.registro.descartar_criacao(instancia.uuid),
		):
			with self.subTest(), self.assertRaises(reg.RegistroMaisNovo):
				operacao()

		self.assertEqual(self.registro.obter(instancia.uuid).estado, Estado.CRIANDO)

	# ------------------------------------------------------------------ concorrência

	def test_varios_sodas_criando_ao_mesmo_tempo_nao_repetem_porta_nem_uuid(self):
		if not self.COMPARTILHA:
			self.skipTest("o adaptador em memória não tem instâncias independentes")

		erros = []

		def trabalhar(numero):
			try:
				registro = self.novo_registro(self.reabrir_repositorio())

				for i in range(6):
					registro.criar(
						f"Soda {numero} instância {i}", perfil_de_banco="padrao", tipo_de_banco="mariadb"
					)
			except Exception as erro:
				erros.append(repr(erro))

		fios = [threading.Thread(target=trabalhar, args=(n,)) for n in range(4)]

		for fio in fios:
			fio.start()

		for fio in fios:
			fio.join()

		self.assertEqual(erros, [])
		instancias = self.novo_registro(self.reabrir_repositorio()).listar()
		self.assertEqual(len(instancias), 24)
		self.assertEqual(len({i.porta for i in instancias}), 24, "porta repetida")
		self.assertEqual(len({i.uuid for i in instancias}), 24, "UUID repetido")
		self.assertEqual(len({i.host for i in instancias}), 24, "host repetido")


class TestRegistroEmMemoria(ContratoDoRegistro, unittest.TestCase):
	COMPARTILHA = False

	def novo_repositorio(self):
		return RepositorioEmMemoria()

	def reabrir_repositorio(self):
		return self.repo


class _EmArquivo:
	def setUp(self):
		self._pasta = tempfile.TemporaryDirectory()
		self.addCleanup(self._pasta.cleanup)
		self.pasta = Path(self._pasta.name)
		super().setUp()


class TestRegistroEmJson(_EmArquivo, ContratoDoRegistro, unittest.TestCase):
	def novo_repositorio(self):
		return RepositorioJson(self.pasta / "registro.json")

	def reabrir_repositorio(self):
		return RepositorioJson(self.pasta / "registro.json")


class TestRegistroEmSqlite(_EmArquivo, ContratoDoRegistro, unittest.TestCase):
	def novo_repositorio(self):
		return RepositorioSqlite(self.pasta / "registro.sqlite")

	def reabrir_repositorio(self):
		return RepositorioSqlite(self.pasta / "registro.sqlite")


if __name__ == "__main__":
	unittest.main()
