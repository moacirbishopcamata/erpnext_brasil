# Consumo indevido: o erro da SEFAZ em que tentar de novo é a pior ação

`cStat 656 — Consumo indevido pelo aplicativo da empresa` **bloqueia o CNPJ por uma hora**,
com desbloqueio automático. O gatilho mais comum é reconsultar um documento depois de um
`cStat 137` (*"Nenhum documento localizado"*) sem esperar: o aplicativo lê "não achei" como
"tente de novo", e a SEFAZ lê a insistência como abuso.

## ⚠️ A regra que inverte o reflexo natural

> *"Se retomar a consulta antes de completar 1 (uma) hora, o tempo é zerado e a contagem
> reiniciará."*

Cada tentativa dentro da janela empurra o fim do bloqueio **uma hora para frente**. Um laço
de retentativa — a reação de qualquer sistema diante de erro de transmissão — mantém a
empresa bloqueada **indefinidamente**, e quanto mais o operador insiste, pior fica.

É o caso raro em que a resposta certa a um erro é **não fazer nada**. E é por isso que o
desenho inteiro gira em torno de uma palavra: a guarda é **preventiva**.

| | O que faz | Reinicia o relógio? |
|---|---|---|
| Requisição **recusada localmente** | nunca chega à SEFAZ | ❌ não |
| Requisição que **sai** durante a janela | a SEFAZ rejeita de novo | ✅ sim, mais uma hora |

A diferença entre esperar uma hora e esperar para sempre é a guarda rodar **antes** da
chamada de rede. Uma verificação feita depois da resposta seria correta, passaria em
qualquer teste de unidade, e não impediria nada.

## O ponto único

`TransporteSefaz` tem cinco operações que falam com a SEFAZ — `transmitir`, `consultar`,
`cancelar`, `corrigir`, `inutilizar` —, e todas constroem o contexto antes de sair:

```python
def _contexto(self) -> ContextoSefaz:
    if self._guarda is not None:
        self._guarda(self._cnpj_emitente, self._ambiente)   # ← aqui

    self._preparar_arquivos_tls()
    ...
```

Uma guarda, não cinco. Repeti-la em cada método seria cinco chances de esquecer na sexta —
mesma lógica do patch no protótipo do leitor de código de barras.

**Antes do TLS de propósito:** preparar certificado para uma requisição que não pode sair é
trabalho jogado fora, e o custo real é o outro — a requisição que sai reinicia a hora.

Na volta, os quatro pontos de retorno passam por `_registrar`, que anota o bloqueio se o
`cStat` for 656. Receber um 656 significa que **alguma requisição escapou da guarda**: se
nada tivesse saído, não haveria o que rejeitar.

## 🔴 A regressão que a suíte pegou

A primeira versão importou `integracao/consumo_indevido` no topo de `transporte_sefaz.py`.
**Derrubou 25 testes de uma vez.**

O motivo: `transporte_sefaz` é um adaptador **livre de `frappe`** — é isso que permite
testar a orquestração inteira sem bench. Importar um módulo que depende do Frappe tornou o
adaptador não-importável fora de um site.

A correção não foi contornar o teste: foi **injetar**, como a classe já fazia com `sessao` e
`dormir`. `guarda` e `registrador` chegam prontos de quem constrói o transporte
(`emissao_nfe.py`, `eventos_nfe.py`), que já vive do lado do Frappe.

O resultado é melhor do que a primeira versão: a dependência ficou explícita no construtor
em vez de escondida num import. **A suíte não atrapalhou o trabalho — corrigiu o desenho.**

Padrão `None` = sem guarda. Não é omissão: é o que mantém o adaptador utilizável em teste.
Um teste separado exige que os dois pontos de construção reais **liguem** os dois — injeção
que ninguém injeta é guarda que nunca roda, com o agravante de o desligamento parecer
intencional.

## Onde o bloqueio mora

DocType `Bloqueio Sefaz`, um registro por `(CNPJ, ambiente)`, com `autoname` de chave única.

**Por que não em cache**, que seria mais curto: perder a chave — Redis reiniciado, cache
limpo num deploy — liberaria a transmissão antes da hora, que é precisamente o que reinicia
a contagem. O dado tem de sobreviver ao que o sistema faz consigo mesmo.

Produção e homologação bloqueiam **de forma independente**: um bloqueio em teste não pode
parar a emissão real.

O `commit` do registro é explícito, e isso não é descuido: a rejeição costuma vir num
caminho que termina em exceção, e o rollback da transação levaria o bloqueio junto —
deixando o app sem saber que está bloqueado, o pior dos estados possíveis.

`liberado_em` é **derivado** do início pelo controller, nunca digitado: dois campos de data
independentes divergiriam, e a divergência apareceria como uma emissão liberada cedo demais.

## A mensagem diz o que não fazer

```
O CNPJ 11.222.333/0001-81 está bloqueado pela SEFAZ por consumo indevido (cStat 656)
no ambiente producao. A liberação é automática em 07/09/2026 11:00 — faltam cerca de
43 minuto(s).

Não tente transmitir antes disso. Cada tentativa dentro da janela reinicia a contagem
de uma hora, e o bloqueio recomeça do zero.
```

Dizer só "bloqueado" seria informação pela metade: a reação natural de quem vê erro de
transmissão é tentar de novo, e aqui isso custa mais uma hora.

A exceção é **tipada** (`BloqueadoPorConsumoIndevido`, passada em `exc=`) — aplicação direta
da lei "erros úteis": quem chama precisa distinguir *"espere"* de *"a nota está errada"*. A
primeira não deve ser repetida de forma alguma; a segunda, depois de corrigida.

## Validação em bench v16

Exercitado em `v16.localhost`, os cinco cenários:

```
1. cStat 100  -> não bloqueia, guarda passa
2. cStat 656  -> bloqueia; liberado em 2026-09-08 06:01:54
3. guarda     -> recusa com BloqueadoPorConsumoIndevido e a mensagem certa
4. ambiente   -> "producao" segue liberado (o bloqueio era em "homologacao")
5. registro   -> cnpj 11222333000181 | company Empresa Teste 656
                 bloqueado_em 05:01:54 | liberado_em 06:01:54 | diferença 1:00:00
```

O CNPJ é gravado **limpo** e a derivação de `liberado_em` sai exata.

### 🔴 O risco que só a execução mostrou

A primeira rodada estourou em `MandatoryError: [Bloqueio Sefaz]: company` — o site de teste
não tinha `Company` cadastrada.

Fácil de descartar como "problema do ambiente", e seria o erro. O que a falha mostrou é
estrutural: **`company` é obrigatório, e a gravação do bloqueio acontece dentro do caminho
da resposta da SEFAZ.** Se ela falhar por qualquer motivo, a exceção sobe, derruba a
transmissão **e** o bloqueio fica sem registro — o CNPJ está bloqueado na SEFAZ e o app não
sabe. A próxima tentativa estende a hora.

Ou seja: o campo obrigatório que a restrição por empresa exige criava exatamente o desfecho
que a docstring deste módulo já declarava como o pior.

A correção não foi afrouxar o campo — a restrição por empresa importa. Foi envolver a
persistência: falhou, registra alto em `Error Log` com o CNPJ, o `cStat` e o aviso de que
**transmitir de novo estende o bloqueio**, e devolve `False`. Deixar a exceção subir seria
trocar um problema por outro maior.

`log_error` e não `print`: é falha que ninguém vê acontecer, e precisa de trilha.

## O que não se faz, declarado

- **Não adivinha consumo indevido.** Quem diz é a SEFAZ, no `cStat`. Uma heurística local
  ("consultei demais") criaria bloqueio que a SEFAZ não impôs, parando emissão legítima.
- **Não desbloqueia à mão.** O desbloqueio é automático. Um botão "liberar agora" seria um
  botão de **estender** o bloqueio — daí o registro ser somente leitura.
- **Não repete a requisição depois.** Reenfileirar para daqui a uma hora seria conveniente e
  perigoso: se a causa do consumo indevido persistir, o app volta a bater e o ciclo
  recomeça. Quem retoma é uma pessoa que viu a mensagem.
- **Não cobre CT-e e MDF-e ainda.** A regra é a mesma e os web services também, mas o
  transporte deles é outro caminho de código; ligar a guarda lá é trabalho a fazer.

## Fontes

- Portal da NF-e — Notas Técnicas e Manual de Orientação do Contribuinte.
- SEFAZ-ES, comunicado sobre controle automático de consumo indevido: bloqueio de uma hora,
  desbloqueio automático, e a contagem que reinicia a cada tentativa antecipada.
