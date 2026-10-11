# Revisão total — fiscal tributário

Versão `0.227.0`, 2026-10-11. Cobre a tarefa 3.2 do change `revisao-total-erpnext-brasil`.

## Cobertura

- **Lido:** `fiscal/impostos/icms.py` (`mva_ajustada`, `calcular_difal`), `fiscal/impostos/ibs_cbs.py` (escolha da alíquota por ano).
- **Varrido:** os 137 módulos de `fiscal/`, `contabil/` e `folha/` contra referência normativa no docstring do módulo.
- **Não lido:** IPI, PIS/COFINS, apuração, CFOP, NCM e as tabelas. Nenhuma regra foi conferida contra a fonte primária (MOC, Convênio, Ajuste SINIEF) nesta revisão.

## Verificado

- `mva_ajustada` (`icms.py:119-146`) implementa `[(1 + MVA) × (1 − alíq. inter) / (1 − alíq. intra)] − 1`, que é a fórmula conhecida da MVA ajustada; confere por leitura, **sem fonte citada no código**.
- `calcular_difal` com `base_dupla` (`icms.py:199-245`) tira o ICMS de origem do valor e reembute o ICMS interno do destino; com `base_dupla=False` aplica a diferença de alíquotas direto. O docstring afirma que a base dupla é "adotada pela maioria após a LC 190/2022". **Não consegui confirmar essa afirmação contra a fonte primária** nesta revisão: fica como aviso.
- IBS/CBS levanta `ValueError` fora do ano de teste (`ibs_cbs.py:111-121`): falha alto, o desenho certo.

## Achado

### RT-04 — 23 de 137 módulos puros não citam fonte normativa — **Médio**

A convenção do projeto (`CLAUDE.md`) é que a docstring registre de onde veio cada regra fiscal e o nível de confiança. Varredura por palavras-chave (fonte, MOC, NT, Ajuste SINIEF, Convênio, Lei, Decreto, Portaria, leiaute, URL) no docstring de cada módulo. Sem nenhuma:

- **Tributos:** `fiscal/impostos/icms.py`, `ipi.py`, `pis_cofins.py`, `apuracao.py`, `fiscal/inscricao_estadual.py`, `fiscal/precificacao.py`, `contabil/custo_aquisicao.py`. São os que calculam dinheiro e alíquota; `icms.py`, `ipi.py` e `apuracao.py` têm **zero** ocorrência de "fonte" no arquivo inteiro, `pis_cofins.py` tem uma.
- **Documento:** `fiscal/documento/assinatura.py`, `estado.py`, `leitura_codigo.py`, `resposta_sefaz.py`, `situacao_fiscal.py`, `traducao_json.py`, `transmissao_registro.py`, `transporte.py`, `validade_certificado.py`.
- **Códigos e relatórios:** `fiscal/codigos/compatibilidade.py`, `repositorio.py`, `xlsx.py`, `fiscal/relatorio_bloqueios.py`, `relatorio_notas.py`, `relatorio_numeracao.py`, `contabil/prontidao_fiscal.py`.

Parte deles é infraestrutura sem regra fiscal (relatórios, transporte, XLSX), então a ausência é inofensiva ali. Os 7 de tributos são o que importa: uma alíquota, um arredondamento ou uma base errada não aparece em teste que usa o mesmo número que o código.

**A verificar:** conferir `icms.py`, `ipi.py`, `pis_cofins.py` e `apuracao.py` contra Convênio ICMS 93/2015 (redação do Convênio 236/2021), LC 190/2022, Convênio ICMS 70/97 (MVA) e a legislação de IPI e PIS/COFINS, e registrar a fonte e o nível de confiança.
