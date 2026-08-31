# eSocial S-2200: Admissão de Trabalhador

Segunda fatia não periódica do eSocial (depois de S-1010) — pré-requisito lógico do
S-1200: não existe folha de um trabalhador que nunca foi admitido.

## Confiança desigual por campo — declarada, não escondida

Diferente do S-1010, onde as quatro tabelas de incidência vieram inteiras do XSD, o
S-2200 tem muito mais domínios que são tabelas nacionais grandes (referenciadas de
arquivos externos ao `evtAdmissao.xsd`) — não trazidas para este projeto. Este
incremento distingue três níveis de confiança, explícitos no código:

| Confiança | Campos | Como foi confirmado |
|---|---|---|
| **Alta** — enumeração literal citada com a tag XSD | `tpAdmissao` (1-7), `indAdmissao` (1-3) | A ferramenta de busca reproduziu `<xs:enumeration value="...">` com `<xs:documentation>` de cada valor |
| **Intermediária** — enumeração citada, mas sem a tag literal | `tpRegPrev` (1-4) | Uma fonte descreveu a faixa, sem reproduzir o XSD verbatim |
| **Só formato** — tabela nacional não trazida | `sexo`, `racaCor`, `grauInstr`, `tpRegTrab`, `natAtividade`, `codCateg`, `unidSalFixo`, `tpSalario` | Aceitos como dígito/inteiro dentro de uma faixa genérica, sem validar contra o domínio real |

Uma primeira tentativa de ler a estrutura inteira devolveu termos vagos como
"domínio tabelado"/"enumerações típicas" em vez de valores literais — sinal de que a
ferramenta estava resumindo, não extraindo. Uma segunda pergunta, mirada
especificamente em `tpAdmissao`/`indAdmissao`, trouxe as tags XSD literais — por
isso só esses dois entraram como "alta confiança".

## `ideEvento` deste evento não é o do S-1200

Lido diretamente em `tipos.xsd` (`T_ideEvento_trab_admissao`): `indRetif`,
`nrRecibo`, `tpAmb`, `procEmi`, `verProc` — **sem** `perApur`/`indApuracao` (fazem
sentido só em evento periódico; S-2200 não é um). Por isso este módulo define seu
próprio `IdeEvento`, mesma decisão de não reaproveitar `esocial_s1200.IdeEvento` já
tomada para outras peças "parecidas mas não iguais" no bloco eSocial.

Achado extra: `procEmi` aqui é `TS_procEmi_sem_8` — o nome do tipo já denuncia que o
valor `8` é excluído do domínio válido **neste evento específico**, diferente do
`procEmi` genérico (dígito 0-9 livre) do S-1200. Testado explicitamente
(`test_proc_emi_8_e_erro_neste_evento`).

## O que fica de fora, deliberadamente

- **`infoEstatutario`** — a outra metade do `choice` de `infoRegimeTrab` (servidor
  estatutário); só `infoCeletista` (CLT) é modelado.
- **Endereço, dependentes, dados bancários, aviso prévio, contrato por prazo
  determinado, condições de trabalho especiais** — grupos adicionais do evento real
  não lidos nesta rodada.
- **Persistência/lookup das tabelas nacionais** de sexo/raça-cor/grau de
  instrução/regime trabalhista/natureza de atividade/categoria/tipo de salário.
- **Serialização XML/assinatura/envio** — mesmo padrão dos outros eventos: modelado
  só o agregado de negócio.

## Arquivos

- `folha/esocial_s2200.py` — `IdeEvento`, `Trabalhador`, `Vinculo`, `InfoCeletista`,
  `InfoContrato`; camada pura, sem Frappe, testável sem bench.

## Fontes

- `github.com/nfephp-org/sped-esocial`, `schemes/v_S_01_03_00/evtAdmissao.xsd` e
  `tipos.xsd` — XSDs literais para a estrutura geral e `ideEvento`. Mesma família do
  `nfephp-org/sped-nfe` já usada para a NF-e, não a fonte primária oficial.
  Consultado em 2026-08-31.
- Duas consultas separadas ao mesmo XSD com granularidade diferente — a primeira
  (visão geral) devolveu termos vagos para vários campos; a segunda (mirada em
  `tpAdmissao`/`indAdmissao`) trouxe as tags `xs:enumeration` literais — registrado
  como o próprio processo de calibrar confiança por campo, não só o resultado.
