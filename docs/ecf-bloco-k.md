# ECF: Bloco K (Saldos das Contas Contábeis e Referenciais)

Segunda fatia "importada direto da ECD", depois do Bloco J (`docs/ecf-bloco-j.md`) —
mesma fonte já registrava que a ECF importa tanto o plano de contas (Bloco J) quanto os
saldos (Bloco K) da ECD.

## `K155` tem os mesmos valores financeiros de `I155`, mas o indicador D/C tem outro nome

Confirmado em `documentacao.senior.com.br/.../bloco-k.htm`: `K155` (saldos detalhados,
depois do encerramento de resultado) tem `REG`, `COD_CTA`, `COD_CCUS`, `VL_SLD_INI`,
`IND_VL_SLD_INI`, `VL_DEB`, `VL_CRED`, `VL_SLD_FIN`, `IND_VL_SLD_FIN` — os sete campos
financeiros são idênticos, na mesma ordem, ao `I155` da ECD (`ecd_i150.py`).

**Achado real de divergência de nome, não de valor**: os dois campos indicadores se
chamam `IND_DC_INI`/`IND_DC_FIN` na ECD e `IND_VL_SLD_INI`/`IND_VL_SLD_FIN` na ECF — mesmo
significado (`"D"`/`"C"`, nunca em branco), nome de campo diferente. O padrão é
internamente consistente (`VL_SLD_INI` → `IND_VL_SLD_INI`, `VL_SLD_FIN` →
`IND_VL_SLD_FIN` — o nome do indicador ecoa o nome do valor que ele qualifica), diferente
da convenção genérica `IND_DC_*` da ECD — não é erro de leitura da fonte, é uma escolha de
nomenclatura real e diferente entre os dois leiautes.

Por isso `montar_k155` **não** delega cegamente trocando só `REG` (como
`montar_j050`/`montar_j051` fazem para o Bloco J) — reconstrói o dicionário renomeando os
dois campos indicadores, mantendo os outros sete exatamente como `montar_i155` os calcula
(mesma aritmética de saldo D/C, mesmo `ContaDesconhecida`).

## O que fica de fora deste primeiro incremento do Bloco K

- **`K030`** (identificação do período e método de apuração de IRPJ/CSLL) — este projeto
  não modela ainda qual método de apuração a empresa usa; fica para quando o núcleo de
  Lucro Real (Blocos L/M/N) entrar.
- **`K156`** (mapeamento referencial dos saldos finais) — mesmo papel de `J051`/`I051`
  para o Bloco K, candidato a incremento seguinte.
- **`K355`/`K356`** (saldos das contas de resultado **antes** do encerramento) — exige
  distinguir "antes" e "depois" do encerramento de resultado, que este projeto não
  modela (só produz o saldo final de cada conta).
- **`K915`/`K935`** (justificativa de divergência de saldo) — sem dado real para gerar
  isso ainda.

## Arquivos

- `erpnext_brasil/contabil/ecf_bloco_k.py` — `montar_k001`, `montar_k155`, `montar_k990`.
- `erpnext_brasil/tests/test_ecf_bloco_k.py` — 6 testes.

## Fontes

- `documentacao.senior.com.br/goup/5.10.3/menu_controladoria/sped/contabil-fiscal-ecf/
  bloco-k.htm`, consultada em 2026-09-03 — mesmo padrão de confiança já aceito para o
  Bloco J.
