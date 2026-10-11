# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Testes da identidade (UUID, descritivo, host), da alocação de portas e da verificação de porta livre.

Além dos casos nomeados, há testes de **entrada aleatória com semente fixa**: o nome do host precisa ser sempre um
rótulo DNS válido, qualquer que seja o descritivo, e a chave de unicidade precisa ser estável (idempotente).
"""

import random
import socket
import string
import unittest
import uuid

from erpnext_brasil.sistema.rede import porta_livre
from erpnext_brasil.soda import identidade as ident
from erpnext_brasil.soda import portas as pt

UUID_A = "12345678-1234-4234-8234-123456789abc"
UUID_B = "87654321-4321-4321-8321-cba987654321"


class TestDescritivo(unittest.TestCase):
	def test_limpa_e_colapsa_espacos(self):
		self.assertEqual(ident.validar_descritivo("  NF-e   em   homologação  "), "NF-e em homologação")

	def test_limites_de_tamanho_incluem_os_extremos(self):
		self.assertEqual(ident.validar_descritivo("abc"), "abc")
		self.assertEqual(len(ident.validar_descritivo("a" * 60)), 60)

		for ruim in ("ab", "a" * 61, "", "  ", "a b"[:2]):
			with self.subTest(tamanho=len(ruim)), self.assertRaises(ident.DescritivoInvalido):
				ident.validar_descritivo(ruim)

	def test_caractere_de_controle_e_recusado(self):
		for ruim in ("linha\nquebrada", "com\ttab", "nulo\x00x", "del\x7fx"):
			with self.subTest(ruim=repr(ruim)), self.assertRaises(ident.DescritivoInvalido):
				ident.validar_descritivo(ruim)

	def test_precisa_de_letra_ou_digito(self):
		for ruim in ("---", "...", "   !!!   "):
			with self.subTest(ruim=ruim), self.assertRaises(ident.DescritivoInvalido):
				ident.validar_descritivo(ruim)

	def test_nao_texto_e_recusado(self):
		for ruim in (None, 123, b"abc", ["abc"]):
			with self.subTest(ruim=ruim), self.assertRaises(ident.DescritivoInvalido):
				ident.validar_descritivo(ruim)


class TestChaveDeUnicidade(unittest.TestCase):
	def test_ignora_caixa_acento_e_espacos(self):
		iguais = [
			"NF-e em Homologação",
			"nf-e em homologacao",
			"NF-E   EM   HOMOLOGAÇÃO",
			"Nf-e em homologaçao",
		]
		self.assertEqual(len({ident.chave_de_unicidade(d) for d in iguais}), 1)

	def test_descritivos_diferentes_tem_chaves_diferentes(self):
		self.assertNotEqual(
			ident.chave_de_unicidade("Folha de pagamento"), ident.chave_de_unicidade("Folha de ponto")
		)

	def test_e_idempotente_em_entrada_aleatoria(self):
		sorteio = random.Random(20261011)
		alfabeto = string.ascii_letters + string.digits + " áéíóúãõçÁÉÍÓÚÃÕÇ-_.!"

		for _ in range(500):
			texto = "".join(sorteio.choice(alfabeto) for _ in range(sorteio.randint(3, 60)))

			try:
				chave = ident.chave_de_unicidade(texto)
			except ident.DescritivoInvalido:
				continue

			self.assertEqual(ident.chave_de_unicidade(chave), chave, texto)


class TestSlugEHost(unittest.TestCase):
	def test_slug_sem_acento_em_minusculas_e_com_hifen(self):
		self.assertEqual(ident.slug("NF-e em homologação!"), "nf-e-em-homologacao")

	def test_slug_limita_o_tamanho_sem_hifen_na_ponta(self):
		slug = ident.slug("a" * 29 + " " + "b" * 10)
		self.assertLessEqual(len(slug), 30)
		self.assertFalse(slug.endswith("-"))

	def test_slug_de_texto_sem_ascii_nao_fica_vazio(self):
		self.assertEqual(ident.slug("日本語"), "instancia")

	def test_host_tem_o_trecho_do_uuid_e_o_dominio(self):
		self.assertEqual(ident.nome_do_host("Teste da NF-e!", UUID_A), "teste-da-nf-e-12345678.localhost")

	def test_hosts_diferem_quando_os_uuids_diferem(self):
		self.assertNotEqual(
			ident.nome_do_host("Mesmo nome", UUID_A), ident.nome_do_host("Mesmo nome", UUID_B)
		)

	def test_host_e_sempre_um_rotulo_dns_valido_em_entrada_aleatoria(self):
		import re

		sorteio = random.Random(42)
		alfabeto = string.ascii_letters + string.digits + " áéíóúãõç-_.!?/\\日本"
		valido = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.localhost")
		total = 0

		for _ in range(1000):
			texto = "".join(sorteio.choice(alfabeto) for _ in range(sorteio.randint(3, 60)))

			try:
				host = ident.nome_do_host(texto, str(uuid.UUID(int=sorteio.getrandbits(128), version=4)))
			except ident.DescritivoInvalido:
				continue

			total += 1
			self.assertIsNotNone(valido.fullmatch(host), (texto, host))
			self.assertLessEqual(len(host.split(".")[0]), 63)

		self.assertGreater(total, 500, "o gerador aleatório quase só produziu descritivos inválidos")


class TestUuid(unittest.TestCase):
	def test_forma_canonica_em_minusculas(self):
		self.assertEqual(ident.normalizar_uuid(UUID_A.upper()), UUID_A)
		self.assertEqual(ident.normalizar_uuid(f"  {UUID_A}  "), UUID_A)

	def test_recusa_o_que_nao_e_uuid_v4_canonico(self):
		recusados = [
			"{" + UUID_A + "}",
			UUID_A.replace("-", ""),
			str(uuid.uuid1()),
			str(uuid.UUID(int=0)),
			"isto não é um uuid",
			"",
			"12345678-1234-1234-8234-123456789abc",  # versão 1
			"12345678-1234-4234-1234-123456789abc",  # variante errada
		]

		for ruim in recusados:
			with self.subTest(ruim=ruim), self.assertRaises(ident.UuidInvalido):
				ident.normalizar_uuid(ruim)

	def test_recusa_nao_texto(self):
		for ruim in (None, 5, uuid.UUID(UUID_A), b"x"):
			with self.subTest(ruim=ruim), self.assertRaises(ident.UuidInvalido):
				ident.normalizar_uuid(ruim)

	def test_abreviar_devolve_oito_hexadecimais(self):
		self.assertEqual(ident.abreviar(UUID_A), "12345678")

	def test_sorteio_sem_colisao(self):
		sorteio = ident.sortear_uuid(set(), gerar=lambda: uuid.UUID(UUID_A))
		self.assertEqual((sorteio.uuid, sorteio.colisoes), (UUID_A, 0))

	def test_sorteio_pula_os_ja_usados_e_conta_as_colisoes(self):
		fila = iter([uuid.UUID(UUID_A), uuid.UUID(UUID_A), uuid.UUID(UUID_B)])
		sorteio = ident.sortear_uuid({UUID_A}, gerar=lambda: next(fila))
		self.assertEqual((sorteio.uuid, sorteio.colisoes), (UUID_B, 2))

	def test_sorteio_esgotado_e_denunciado(self):
		with self.assertRaises(ident.UuidEsgotado):
			ident.sortear_uuid({UUID_A}, gerar=lambda: uuid.UUID(UUID_A), tentativas=5)

	def test_gerador_que_devolve_lixo_e_recusado(self):
		with self.assertRaises(ident.UuidInvalido):
			ident.sortear_uuid(set(), gerar=lambda: uuid.UUID(int=0))

	def test_o_gerador_padrao_produz_uuids_validos_e_distintos(self):
		vistos = {ident.sortear_uuid(set()).uuid for _ in range(200)}
		self.assertEqual(len(vistos), 200)
		self.assertTrue(all(ident.normalizar_uuid(u) == u for u in vistos))


class TestFaixaEAlocacao(unittest.TestCase):
	def livre(self, ocupadas=()):
		return lambda porta: porta not in set(ocupadas)

	def test_faixa_valida_contem_e_itera(self):
		faixa = pt.FaixaDePortas(8100, 8102)
		self.assertEqual(list(faixa), [8100, 8101, 8102])
		self.assertIn(8101, faixa)
		self.assertNotIn(8103, faixa)
		self.assertNotIn("8101", faixa)

	def test_faixa_invalida_e_recusada(self):
		for inicio, fim in ((80, 90), (9000, 8000), (8000, 70000), (0, 10)):
			with self.subTest(faixa=(inicio, fim)), self.assertRaises(ValueError):
				pt.FaixaDePortas(inicio, fim)

	def test_reservadas_cobrem_banco_redis_e_bench(self):
		for porta in (3306, 5432, 6379, 8001, 9001, 6788, 8080, 11000, 13999):
			self.assertIn(porta, pt.RESERVADAS, porta)

		self.assertNotIn(14000, pt.RESERVADAS)
		self.assertNotIn(8100, pt.RESERVADAS)

	def test_sem_escolha_devolve_a_menor_livre(self):
		self.assertEqual(pt.alocar(pt.FAIXA_PADRAO, {}, self.livre()), 8100)

	def test_pula_registradas_reservadas_e_ocupadas(self):
		faixa = pt.FaixaDePortas(8100, 8110)
		escolhida = pt.alocar(faixa, {8100: "A"}, self.livre({8101}), reservadas=frozenset({8102}))
		self.assertEqual(escolhida, 8103)

	def test_faixa_esgotada(self):
		faixa = pt.FaixaDePortas(8100, 8101)

		with self.assertRaises(pt.FaixaEsgotada) as contexto:
			pt.alocar(faixa, {8100: "A", 8101: "B"}, self.livre())

		self.assertIn("amplie a faixa", str(contexto.exception))

	def test_escolha_livre_e_aceita(self):
		self.assertEqual(pt.alocar(pt.FAIXA_PADRAO, {}, self.livre(), escolhida=8555), 8555)

	def test_escolha_fora_da_faixa_mas_nao_reservada_e_aceita(self):
		self.assertEqual(pt.alocar(pt.FAIXA_PADRAO, {}, self.livre(), escolhida=20000), 20000)

	def test_escolha_reservada_e_recusada_com_sugestao(self):
		with self.assertRaises(pt.PortaRecusada) as contexto:
			pt.alocar(pt.FAIXA_PADRAO, {}, self.livre(), escolhida=3306)

		self.assertIn("reservada", contexto.exception.motivo)
		self.assertEqual(contexto.exception.sugestao, 8100)
		self.assertEqual(contexto.exception.porta, 3306)

	def test_escolha_de_outra_instancia_nomeia_quem_a_tem(self):
		with self.assertRaises(pt.PortaRecusada) as contexto:
			pt.alocar(pt.FAIXA_PADRAO, {8200: "Folha"}, self.livre(), escolhida=8200)

		self.assertIn("Folha", contexto.exception.motivo)

	def test_escolha_ocupada_nomeia_o_ocupante_quando_se_sabe(self):
		with self.assertRaises(pt.PortaRecusada) as contexto:
			pt.alocar(
				pt.FAIXA_PADRAO,
				{},
				self.livre({8300}),
				escolhida=8300,
				quem_ocupa=lambda porta: "node.exe (pid 4242)",
			)

		self.assertIn("node.exe", contexto.exception.motivo)

	def test_escolha_ocupada_sem_ocupante_conhecido(self):
		with self.assertRaises(pt.PortaRecusada) as contexto:
			pt.alocar(pt.FAIXA_PADRAO, {}, self.livre({8300}), escolhida=8300)

		self.assertIn("outro programa", contexto.exception.motivo)

	def test_escolha_invalida_e_recusada(self):
		for ruim in (True, "8100", 80, 70000, 1023):
			with self.subTest(ruim=ruim), self.assertRaises(pt.PortaRecusada):
				pt.alocar(pt.FAIXA_PADRAO, {}, self.livre(), escolhida=ruim)

	def test_sem_sugestao_quando_a_faixa_esta_cheia(self):
		faixa = pt.FaixaDePortas(8100, 8101)

		with self.assertRaises(pt.PortaRecusada) as contexto:
			pt.alocar(faixa, {8100: "A", 8101: "B"}, self.livre(), escolhida=3306)

		self.assertIsNone(contexto.exception.sugestao)
		self.assertNotIn("próxima livre", str(contexto.exception))

	def test_sugestao_volta_ao_inicio_quando_nao_ha_depois(self):
		faixa = pt.FaixaDePortas(8100, 8102)

		with self.assertRaises(pt.PortaRecusada) as contexto:
			pt.alocar(faixa, {8102: "C"}, self.livre(), escolhida=3306, reservadas=frozenset({3306}))

		self.assertEqual(contexto.exception.sugestao, 8100)


class TestPortaLivre(unittest.TestCase):
	def test_porta_aberta_por_outro_programa_nao_esta_livre(self):
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ocupante:
			ocupante.bind(("127.0.0.1", 0))
			ocupante.listen()
			self.assertFalse(porta_livre(ocupante.getsockname()[1]))

	def test_porta_liberada_volta_a_estar_livre(self):
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as achado:
			achado.bind(("127.0.0.1", 0))
			numero = achado.getsockname()[1]

		self.assertTrue(porta_livre(numero))

	def test_valor_que_nao_e_porta_nao_esta_livre(self):
		for ruim in (0, -1, 65536, "80", None, True, 8.5):
			with self.subTest(ruim=ruim):
				self.assertFalse(porta_livre(ruim))


if __name__ == "__main__":
	unittest.main()
