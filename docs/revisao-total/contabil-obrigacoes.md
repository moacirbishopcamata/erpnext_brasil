# Revisão total — contábil e obrigações acessórias (SPED, ECD, ECF, Reinf)

Versão `0.227.0`, 2026-10-11. Cobre a tarefa 3.3 do change `revisao-total-erpnext-brasil`.

## Cobertura

- **Lido:** `integracao/geracao_efd.py` (costura da EFD) e o inventário dos 40 módulos de `contabil/`.
- **Varrido:** referência normativa no docstring e referência em teste, para os 40 módulos.
- **Não lido:** o conteúdo dos blocos EFD (0, C, D, E, H, K, 9), ECD, ECF e Reinf. Nenhum registro foi conferido contra o leiaute oficial.

## Achados

### RT-02 — `gerar_efd` sem checagem de permissão — **Alto**

Ver [`integracao.md`](integracao.md). É o achado desta frente: o ponto de entrada da EFD aceita qualquer usuário autenticado e grava com `ignore_permissions=True` (`geracao_efd.py:124`).

### RT-14 — docstring de `gerar_efd` defasada em relação ao código — **Baixo**

O docstring do método (`geracao_efd.py:93-96`) diz que o arquivo "ainda não tem os blocos D/H/K nem os cadastros do Bloco 0". O código já monta H e K (`bloco_h_do_periodo`, `bloco_k_do_periodo`) e `BLOCOS_SEM_LEITURA_DO_SITE = ("D",)` (linha 63), então o **aviso devolvido ao usuário está certo** (só o Bloco D e os cadastros do Bloco 0 faltam) e o docstring é que ficou para trás. O arquivo continua parcial e "serve para conferir a montagem no PVA, não para transmitir".

### RT-04 (parcial) — dois módulos sem fonte

`contabil/custo_aquisicao.py` e `contabil/prontidao_fiscal.py` não citam norma no docstring. O resto dos 40 cita (a lista de palavras inclui "SPED", o que torna a varredura fraca para esta frente). Ver [`fiscal-tributario.md`](fiscal-tributario.md).

## Sem achado

Todos os 40 módulos de `contabil/` são citados por algum teste da suíte pura.
