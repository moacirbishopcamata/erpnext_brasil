# RH: estado do `frappe/hrms` antes de tropicalizar

Primeiro passo do bloco RH, confirmado pelo usuário como o próximo depois do contábil
(ver memória do projeto). Mesma disciplina já aplicada ao `erpnext` antes do fiscal:
levantar o estado real do app de terceiros antes de decidir como estender — nunca supor.

## Onde está e o que é

`frappe/hrms` já está clonado localmente em `G:\PROJECTS\hrms` (commit `51c2d3b`,
2026-08-20, branch de desenvolvimento — `__version__ = "17.0.0-dev"`). Dois módulos:
`HR` (`hrms/hr/`, 118 doctypes) e `Payroll` (`hrms/payroll/`, ~40 doctypes). RH e folha
de pagamento não existem no `erpnext` — este é o app separado que os implementa.

## Confirmado: não existe nada para o Brasil, nem aqui, nem no `erpnext`

`hrms/regional/` tem só `india/` e `united_arab_emirates/`. `erpnext/regional/` (a
mesma pasta que motivou o obstáculo de integração do plano de contas, ver
`docs/plano-de-contas.md`) tem `australia`, `italy`, `south_africa`, `turkey`,
`united_arab_emirates`, `united_states` — também sem `brazil`. Confirma o que a memória
do projeto já registrava por suposição informada: a tropicalização brasileira (INSS,
FGTS, IRRF na folha, eSocial) não existe em nenhum dos dois apps, ausência real, não
falha de busca.

## A boa notícia: `hrms` tem hook de override regional de verdade

Diferente do seletor de plano de contas do ERPNext (`chart_of_accounts.py`, que varre
uma pasta fixa dentro do próprio app — ver `docs/plano-de-contas.md`), o `hrms` **tem**
um mecanismo de hook padrão do Frappe para isso: `regional_overrides`, um dict
`{pais: {caminho_da_função_original: caminho_da_função_de_substituição}}` que
`frappe.get_hooks("regional_overrides", {})` agrega de **todos os apps instalados** —
`erpnext_brasil` pode registrar o seu, sem tocar em `hrms`, exatamente como um app de
terceiros deve funcionar.

### Como funciona (`hrms/__init__.py`)

```python
def get_region(company=None):
    """País usado para resolver os overrides: flag > Company.country > System Settings."""
    ...

def allow_regional(fn):
    """Decorator: torna uma função substituível por região via o hook `regional_overrides`."""
    @functools.wraps(fn)
    def caller(*args, **kwargs):
        overrides = frappe.get_hooks("regional_overrides", {}).get(get_region())
        function_path = f"{inspect.getmodule(fn).__name__}.{fn.__name__}"
        if not overrides or function_path not in overrides:
            return fn(*args, **kwargs)
        return frappe.get_attr(overrides[function_path][-1])(*args, **kwargs)  # último app instalado ganha
    return caller
```

`get_region()` usa `Company.country` — o país da empresa, não do usuário nem do
sistema — confirmado como `"Brazil"` (nome exato do doctype `Country` do Frappe core,
`frappe/geo/country_info.json`, código `br`, moeda `BRL`) — **não** `"Brasil"`. Um
`regional_overrides = {"Brazil": {...}}` errado por causa desse detalhe (`"Brasil"` em
vez de `"Brazil"`) nunca dispararia, silenciosamente — pegadinha a testar explicitamente
quando a implementação chegar.

**Pegadinha do `function_path`**: para um método decorado dentro de uma classe (caso de
`SalarySlip.apply_regional_deductions`, abaixo), o caminho **não inclui o nome da
classe** — `inspect.getmodule(fn).__name__` é só o módulo, `fn.__name__` é só o nome do
método. O caminho correto é
`"hrms.payroll.doctype.salary_slip.salary_slip.apply_regional_deductions"`, não
`"...salary_slip.SalarySlip.apply_regional_deductions"`.

### Pontos de extensão já existentes (buscados em `hrms/`)

| Função original | Onde | Para quê |
|---|---|---|
| `SalarySlip.apply_regional_deductions` | `payroll/doctype/salary_slip/salary_slip.py` | **O ponto principal**: "Hook point for region-specific salary slip deductions" — no-op por padrão, chamado antes de fechar os totais do holerite. É aqui que INSS/IRRF/FGTS entrariam. |
| `apply_surcharge_with_marginal_relief` | `payroll/doctype/income_tax_slab/income_tax_slab.py` | Ajuste de imposto de renda por faixa — hoje só "marginal relief" (conceito específico do IR indiano), mas o ponto de extensão em si é genérico. |
| `calculate_annual_eligible_hra_exemption`, `calculate_hra_exemption_for_period`, `calculate_tax_with_marginal_relief` | `hr/utils.py` | Específicos do imposto de renda indiano (isenção de aluguel — HRA — não existe equivalente direto no IRRF brasileiro) — não diretamente reaproveitáveis, mas confirmam o padrão. |

`apply_regional_deductions` é o único genuinamente necessário para uma primeira versão:
é onde o holerite brasileiro precisaria descontar INSS e IRRF (e o eSocial mais adiante
precisaria dos mesmos números).

## `Salary Component` já tem fórmula/condição — possível ponto de partida

`Payroll > Salary Component` (o doctype que define cada verba/desconto do holerite) já
tem campos `formula` e `condition` (código Python avaliado em tempo de execução) e
`amount_based_on_formula`. Uma primeira aproximação de INSS/IRRF **poderia** começar
como Salary Components com fórmula, sem precisar do hook `apply_regional_deductions` —
mas a tabela progressiva do INSS (faixas com alíquota efetiva, não marginal simples) e
o desconto por dependente do IRRF têm regras específicas demais para uma fórmula de uma
linha só; decisão de design a tomar quando a implementação real começar, não aqui.

## Escopo do que falta (citado da memória do projeto, não pesquisado agora)

INSS (contribuição previdenciária do empregado, tabela progressiva que muda por
Portaria Interministerial, geralmente anual), FGTS (8% sobre a remuneração — encargo do
**empregador**, não desconto do holerite, recolhido separadamente, não aparece como
dedução do trabalhador), IRRF na folha (tabela progressiva mensal, desconto
simplificado ou por dependente, também reajustada por lei/instrução normativa), e
eSocial (a obrigação acessória digital que substituiu CAGED/RAIS/GFIP — provavelmente o
maior item de todos, com leiaute de eventos próprio, análogo ao EFD-Reinf que ficou
bloqueado por falta de fonte acessível no bloco fiscal, ver `docs/README.md`).

**Nenhuma tabela, alíquota ou regra de cálculo foi pesquisada ou implementada neste
incremento** — isto é só o levantamento de estado (mesmo objetivo do CLAUDE.md do
`erpnext` antes do fiscal: entender o terreno antes de construir nele). A implementação
de qualquer tabela precisa da mesma disciplina já aplicada ao fiscal: fonte primária
(lei, portaria, instrução normativa vigente), nunca de memória.

## Ainda por levantar

- Confirmar se `hrms` já tem algum conceito de "Country" ligado a outros campos de
  `Company`/`Employee` que precisariam existir antes de qualquer override funcionar de
  verdade (ex.: CPF do funcionário, categoria de INSS).
- Verificar se `bench get-app hrms` já foi executado em algum bench local, ou se ainda
  precisa ser instalado antes de qualquer teste com Frappe de verdade.
- Levantar o leiaute do eSocial (fonte oficial, provavelmente também com o mesmo risco
  de inacessibilidade já visto para outras fontes `gov.br` neste projeto).

## Fontes

- `hrms` (repositório local, `G:\PROJECTS\hrms`, commit `51c2d3b`) — código-fonte lido
  diretamente: `hrms/__init__.py`, `hrms/hooks.py`, `hrms/regional/`,
  `hrms/payroll/doctype/salary_slip/salary_slip.py`,
  `hrms/payroll/doctype/income_tax_slab/income_tax_slab.py`, `hrms/hr/utils.py`,
  `hrms/payroll/doctype/salary_component/salary_component.json`.
- `erpnext/regional/` (repositório local) — confirmação da mesma ausência do lado do
  ERPNext.
- `frappe/geo/country_info.json` (repositório local) — nome exato do país (`"Brazil"`).
- Consultado em 2026-08-30.
