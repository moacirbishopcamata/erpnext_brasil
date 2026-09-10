# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""A decisão de contingência separa o que chega parecido e exige resposta oposta.

Teste-âncora: `test_rejeicao_nao_entra_em_contingencia`. Indisponibilidade, rejeição e
bloqueio por consumo indevido chegam ao mesmo `except` de quem faz a chamada, e confundir
qualquer par produz dano concreto:

- rejeição tratada como indisponibilidade → cupom entregue ao consumidor de um documento
  que a SEFAZ já recusou;
- bloqueio tratado como indisponibilidade → mesma coisa, e ainda esconde o 656;
- indisponibilidade tratada como rejeição → venda recusada com a SEFAZ apenas fora do ar.

Segundo eixo: emitente Pessoa Física não pode contingenciar, porque o QR Code que ele
precisaria (versão 3, assinatura) não está implementado e o da versão 2 é rejeição 444 para
CPF. Recusar a venda é o único dano reversível.

Módulo puro: roda sem bench.
"""

import unittest

from erpnext_brasil.fiscal.contingencia_nfce import (
	Acao,
	Resultado,
	decidir,
	pode_emitir_em_contingencia,
)


class TestDecisaoDeContingencia(unittest.TestCase):
	def test_sem_resposta_entra_em_contingencia(self):
		"""O caso que a contingência existe para atender: a venda não pode parar."""
		self.assertIs(Acao.CONTINGENCIAR, decidir(Resultado.SEM_RESPOSTA))

	def test_rejeicao_nao_entra_em_contingencia(self):
		"""Teste-âncora. Houve resposta: o documento está errado, e contingenciar apenas
		adia a mesma recusa — com o cupom já na mão do consumidor."""
		self.assertIs(Acao.RECUSAR, decidir(Resultado.REJEITADA))

	def test_bloqueio_por_consumo_indevido_nao_entra_em_contingencia(self):
		"""Nada saiu, e emitir off-line aqui esconderia o 656 de quem precisa esperar."""
		self.assertIs(Acao.RECUSAR, decidir(Resultado.BLOQUEADO))

	def test_autorizada_conclui(self):
		self.assertIs(Acao.CONCLUIR, decidir(Resultado.AUTORIZADA))

	def test_so_um_resultado_leva_a_contingencia(self):
		"""Trava de conjunto: se um `Resultado` novo aparecer, ele **não** cai em
		contingência por omissão. O padrão do módulo é recusar, e essa é a escolha segura —
		mas ela precisa ser deliberada, não herdada."""
		contingenciam = [r for r in Resultado if decidir(r) is Acao.CONTINGENCIAR]

		self.assertEqual([Resultado.SEM_RESPOSTA], contingenciam)

	def test_todo_resultado_tem_acao(self):
		"""Nenhum membro do enum fica sem decisão — um `None` silencioso aqui seria lido
		como 'siga o fluxo normal' por quem chama."""
		for resultado in Resultado:
			with self.subTest(resultado=resultado):
				self.assertIn(decidir(resultado), tuple(Acao))


class TestEmitentePessoaFisica(unittest.TestCase):
	def test_pessoa_fisica_nao_contingencia(self):
		"""Segundo eixo. O QR Code v2 é rejeição 444 para CPF, e o v3 não está
		implementado: emitir produziria cupom entregue e irrecuperável."""
		self.assertIs(
			Acao.RECUSAR,
			decidir(Resultado.SEM_RESPOSTA, emitente_pessoa_fisica=True),
		)

	def test_pessoa_juridica_contingencia(self):
		"""O contraste que prova que o teste acima mede o emitente, e não outra coisa."""
		self.assertIs(
			Acao.CONTINGENCIAR,
			decidir(Resultado.SEM_RESPOSTA, emitente_pessoa_fisica=False),
		)

	def test_pessoa_fisica_nao_muda_os_outros_desfechos(self):
		"""A restrição é sobre **poder contingenciar**, não sobre vender. Autorizada
		continua concluindo para Pessoa Física — confundir isso impediria o Produtor Rural
		de emitir NFC-e normalmente."""
		self.assertIs(
			Acao.CONCLUIR,
			decidir(Resultado.AUTORIZADA, emitente_pessoa_fisica=True),
		)

	def test_disponibilidade_e_legivel_sozinha(self):
		"""A pergunta tem nome próprio para poder ser feita antes da venda, na tela, e não
		só no desfecho de uma transmissão que já falhou."""
		self.assertTrue(pode_emitir_em_contingencia(emitente_pessoa_fisica=False))
		self.assertFalse(pode_emitir_em_contingencia(emitente_pessoa_fisica=True))


if __name__ == "__main__":
	unittest.main()
