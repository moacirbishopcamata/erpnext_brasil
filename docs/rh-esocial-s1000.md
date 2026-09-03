# eSocial S-1000 (evtInfoEmpregador) — Informações do Empregador/Contribuinte/Órgão Público

Módulo: `erpnext_brasil/folha/esocial_s1000.py`. Testes: `erpnext_brasil/tests/test_esocial_s1000.py`
(28 testes).

## Por que este evento, agora

`docs/rh-estado-esocial.md` registrava o S-1000 como pendência desde a implementação do S-1010
("a peça de configuração que faltava para o S-1200 fazer sentido" citava o S-1010, mas supunha o
próprio cadastro do empregador já feito). O S-1000 é logicamente anterior a todo o resto do bloco
eSocial: é o evento que declara a classificação tributária do contribuinte perante o sistema.

## `ideEvento` mais simples que os demais — achado real

Lido diretamente em `tipos.xsd` (`T_ideEvento_exclusao`): só `tpAmb`/`procEmi`/`verProc`, sem
`indRetif`/`nrRecibo`. O nome do tipo (`_exclusao`) não indica que o evento é uma exclusão — vem de
ter sido introduzido para eventos de tabela, cuja correção é uma nova operação sobre o período de
validade, não uma retificação no sentido do S-2200/S-1200.

## Operação como `xs:choice` real: `inclusao`/`alteracao`/`exclusao`

Confirmado no XSD (`evtInfoEmpregador.xsd`): as três operações são mutuamente exclusivas, cada uma
com seu próprio `idePeriodo` (`iniValid` obrigatório, `fimValid` opcional, "AAAA-MM"). Só
`inclusao`/`alteracao` carregam `infoCadastro`; `exclusao` é só `idePeriodo` — o XSD não permite
`infoCadastro` numa exclusão. Modelado como três funções de montagem separadas
(`montar_inclusao`/`montar_alteracao`/`montar_exclusao`), não uma função genérica com `if`.

## Campos de `infoCadastro` cobertos

`classTrib` (Tabela 08 da RFB, 2 dígitos — catálogo não verificado, mesma decisão já tomada para os
registros "código+valor" da ECF), `indCoop`, `indConstr`, `indDesFolha`, `indOpcCP`, `indPorte`,
`indOptRegEletron`, `cnpjEFR`, `dtTrans11096`, `indTribFolhaPisPasep`, `indPertIRRF` — todos com
enumeração literal confirmada no XSD, exceto `classTrib`.

## Fora de escopo, deliberadamente

- **`dadosIsencao`** — só para `classTrib=80` (entidades imunes/isentas), CEBAS/portaria/lei de
  concessão — regime raro, sem cadastro correspondente neste projeto.
- **`novaValidade`** — variante rara do fluxo de `alteracao` (aceita quando o chamador a fornece,
  sem função de conveniência dedicada) — mesma decisão do campo homônimo do S-1010.
- **`infoOrgInternacional`** — exclusivo de organismos internacionais (natureza jurídica grupo
  `[5]`), fora do domínio deste projeto.
- Regras de dependência cruzada com a natureza jurídica do declarante (ex.: `indCoop` só
  não-zero para natureza 214-3; `cnpjEFR` obrigatório para Administração Pública) — dependem de
  `Company.br_natureza_juridica` (já modelado para a ECF), cruzamento que fica para a camada de
  integração, não para a função pura de montagem.

## Fonte

`github.com/nfephp-org/sped-esocial`, `schemes/v_S_01_03_00/evtInfoEmpregador.xsd` e `tipos.xsd` —
não a fonte primária oficial, mesma advertência já registrada para os outros módulos eSocial deste
projeto.
