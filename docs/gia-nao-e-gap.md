# GIA: investigada e descartada — não é um gap real

Item de backlog desde 2026-08-31 ("GIA — estadual, SP — layout varia por UF"). Antes de
implementar, verificado se a obrigação ainda está vigente — mesma disciplina que reformulou o
item "DCTFWeb" (`docs/rh-esocial-s1299.md`) em vez de implementar um leiaute inexistente.

## Achado decisivo: extinção nacional em curso, não peculiaridade de um estado

- **São Paulo** — Portaria SRE 02/2025: dispensa **100% dos contribuintes do RPA** da entrega
  da GIA a partir de janeiro de 2026. Já em vigor na data de hoje desta investigação
  (2026-08-31).
- **Minas Gerais** — Portaria SRE 285/2026: dispensa obrigatória do DAPI 1 (equivalente
  mineiro da GIA) a partir de julho de 2026. Também já em vigor.
- **Rio de Janeiro** — Resolução SEFAZ nº 37/2019: dispensou a GIA-ICMS desde **2019** — a mais
  antiga das três, mostra que a tendência não é recente.

Nos três maiores estados verificados, a apuração migrou para a **EFD-ICMS/IPI** — que este
projeto **já implementa** (`docs/sped-fiscal.md`).

## Escopo da verificação, declarado

Não foram investigados os 24 estados restantes individualmente — seria um esforço
desproporcional para um item de backlog que já mostrou o padrão claramente nos três maiores
mercados do país (SP, MG, RJ). Se um estado específico ainda exigir GIA de verdade quando este
app for usado numa empresa desse estado, é um levantamento pontual a fazer então — não uma
obrigação genérica a implementar hoje.

## Conclusão

Implementar GIA agora seria construir uma obrigação em extinção nacional, não preencher um gap
real. Fechado sem código — mesmo tratamento já dado a RAIS/CAGED (substituídos pelo eSocial,
ver `docs/rh-estado-esocial.md`).

## Fontes

- Portaria SRE 02/2025 (SP), consultada via `portal.fazenda.sp.gov.br` e cobertura
  especializada (contabeis.com.br, legisweb.com.br), em 2026-08-31.
- Portaria SRE 285/2026 (MG), consultada via `fazenda.mg.gov.br` e cobertura especializada
  (totvs.com/blog, mgcontecnica.com.br), em 2026-08-31.
- Resolução SEFAZ nº 37/2019 (RJ), citada por `portal.fazenda.rj.gov.br`, em 2026-08-31.
