## 1. Levantamento de fontes

- [x] 1.1 Ler `docs/gaps.md` e extrair itens abertos (gaps de costura, módulos sem bench, operação) — verificar que cada item tem classificação (✅/⚠️/❌/🔧) e referência ao change correspondente
- [x] 1.2 Ler `docs/estado-da-tropicalizacao.md` e cruzar com gaps.md — identificar afirmações desatualizadas ou contraditórias
- [x] 1.3 Listar todos os changes ativos (`openspec list --json`) e mapear quais gaps cada um cobre — verificar que nenhum gap ficou sem change quando deveria ter
- [x] 1.4 Verificar `openspec list --specs` para confirmar que as specs existentes (cte-operacional, mdfe-operacional) refletem o estado real

## 2. Consolidação por domínio

- [x] 2.1 Criar `docs/avaliacao-tropicalizacao.md` com seção "Documentos Fiscais" (NF-e, NFC-e, CT-e, MDF-e) — classificar cada um e referenciar change/task
- [x] 2.2 Adicionar seção "Apuração e Contabilidade" (ICMS, IPI, PIS/COFINS, EFD, ECF, ECD, EFD-Reinf) — verificar se algum item está bloqueado
- [x] 2.3 Adicionar seção "RH e eSocial" (S-1000 a S-2299, INSS, IRRF, FGTS) — mapear progresso e dependências
- [x] 2.4 Adicionar seção "Financeiro" (boleto, PIX, NFS-e) — identificar o que está pronto vs. o que falta
- [x] 2.5 Adicionar seção "Infraestrutura" (bench tests, certificado A1, SEFAZ real) — registrar bloqueios externos

## 3. Priorização

- [x] 3.1 Classificar cada item por eixo "bloqueio de uso real" × "cascata de trabalho futuro" — registrar justificativa em uma coluna de observações
- [x] 3.2 Identificar os 5 itens de maior impacto que ainda não têm change — candidatos a novos changes
- [x] 3.3 Verificar se há itens que ficaram bloqueados por dependência externa (certificado A1, homologação SEFAZ) e documentar como desbloquear

## 4. Validação e fechamento

- [x] 4.1 Conferir que `docs/avaliacao-tropicalizacao.md` tem data de atualização e referência a `gaps.md` como fonte canônica
- [x] 4.2 Rodar a suíte pura (2847 testes OK) e de arquitetura (5 testes OK) para garantir que nenhuma alteração documental quebrou nada
- [ ] 4.3 Commitar o change `avaliar-tropicalizacao` com mensagem `docs(openspec): avaliação consolidada da tropicalização do ERPNext`
