# Integração com o `hrms`: INSS e IRRF no `Salary Slip`

Primeiro código do bloco RH que toca o Frappe/`hrms` de verdade — depois de
`docs/rh-inss.md`, `docs/rh-irrf.md` e `docs/rh-fgts.md`, que só cobrem a conta pura.

## O ponto de plugue: `apply_regional_deductions`

`docs/rh-estado-hrms.md` já tinha localizado o alvo: `SalarySlip` chama
`self.apply_regional_deductions()` — um método decorado com `@hrms.allow_regional` que
hoje é um no-op — logo depois de `set_gross_pay_and_base_gross_pay()` e antes de
`set_net_pay()`. O decorador consulta o hook `regional_overrides` (agregado de todos
os apps instalados via `frappe.get_hooks`) e, se `Company.country` do funcionário for
`"Brazil"`, chama a função registrada no lugar do no-op.

`erpnext_brasil/hooks.py` registra:

```python
regional_overrides = {
    "Brazil": {
        "hrms.payroll.doctype.salary_slip.salary_slip.apply_regional_deductions":
            "erpnext_brasil.integracao.folha.apply_regional_deductions",
    }
}
```

O caminho da função original **não inclui o nome da classe** (`SalarySlip`) —
pegadinha já registrada em `docs/rh-estado-hrms.md`, confirmada de novo aqui ao ler o
decorador (`inspect.getmodule(fn).__name__ + "." + fn.__name__`, nunca o `self`).

## Por que só INSS e IRRF, nunca FGTS, neste hook

`apply_regional_deductions` mexe em `self.deductions` — a tabela de **descontos do
empregado**, o que reduz o líquido que ele recebe. FGTS não é desconto do empregado
(`docs/rh-fgts.md`): é uma obrigação do empregador, por fora do contracheque. Incluir
uma linha de FGTS aqui mostraria ao empregado um desconto que ele nunca sofre de
verdade — o oposto do que a seção "Contexto decide comportamento" (preferências
pessoais deste projeto) pede: a representação na tela tem que comunicar o que
realmente acontece. A integração do FGTS (relatório mensal de guia, lançamento
contábil da obrigação do empregador) fica para um passo futuro, fora deste hook.

## Por que sempre INSS como dedução da base do IRRF, nunca desconto simplificado

`docs/rh-irrf.md` documenta que a escolha entre desconto simplificado e deduções
legais reais é do contribuinte. O `hrms`, hoje, não tem no `Salary Slip` um campo que
guarde essa escolha por funcionário — não existe onde ler a decisão. Por isso
`integracao/folha.py` sempre usa `calcular_inss` como a dedução que reduz a base do
IRRF: é a opção sempre disponível, sem depender de um campo que ainda não existe.
Quando/se o `hrms` ganhar esse campo, a escolha pode ser lida e `calcular_desconto_
simplificado` (`folha/irrf.py`) plugado como alternativa — sem mudar `folha/irrf.py`
em si, só a tradução em `integracao/folha.py`.

## Recomputa do zero a cada chamada, preservando o resto da tabela

`apply_regional_deductions` roda toda vez que a folha é processada — inclusive na
pré-visualização, antes de qualquer submissão. `integracao/folha.py` remove as linhas
de `INSS`/`IRRF` de uma execução anterior antes de recalcular, preservando qualquer
outro desconto configurado na estrutura salarial do funcionário — mesma disciplina de
`integracao/documento.py::_sincronizar_tabela_de_impostos`, que reescreve só a parte
da tabela de impostos que o próprio app gerou.

## `Salary Component`: criado no `after_install`/`after_migrate`, condicional ao `hrms`

Uma linha de `deductions` referencia `salary_component` (campo `Link`, obrigatório) —
precisa existir um `Salary Component` chamado `"INSS"` e outro `"IRRF"` antes que
`doc.append("deductions", ...)` funcione. `setup/install.py::criar_componentes_
salariais` cria os dois, idempotente (`frappe.db.exists` antes de inserir).

`erpnext_brasil` não lista `hrms` em `required_apps` — o bloco fiscal roda perfeitamente
sem nenhum módulo de RH instalado. Por isso `criar_componentes_salariais` primeiro
checa se o DocType `Salary Component` existe (`frappe.db.exists("DocType", ...)`) antes
de tentar criar qualquer coisa — uma instalação só-fiscal não pode quebrar por causa de
um app de RH que nem está presente.

## Estado de verificação: não exercitado contra um `Salary Slip` real

Diferente de `folha/inss.py`/`folha/irrf.py` (testados exaustivamente sem bench), este
módulo depende do Frappe e do `hrms` — não há bench disponível nesta sessão para gerar
um funcionário, uma estrutura salarial e processar uma folha de ponta a ponta. Mesma
limitação já registrada para `integracao/documento.py` e `integracao/party.py`,
nenhum dos quais tem teste automatizado pelo mesmo motivo — `test_arquitetura.py`
confirma que a suíte inteira roda sem `import frappe`, então esta camada
inevitavelmente fica fora da cobertura automatizada até haver bench.

O que foi conferido, sem poder rodar: a leitura de `doc.gross_pay` (nome do campo e
o momento exato em que é calculado, antes de `apply_regional_deductions` no fluxo de
`calculate_net_pay`) e o formato de `Salary Detail` (`salary_component`/`amount`) —
ambos lidos diretamente do código-fonte do `hrms` clonado localmente
(`hrms/payroll/doctype/salary_slip/salary_slip.py`,
`hrms/payroll/doctype/salary_detail/salary_detail.json`), não de documentação de
terceiros.

## Ainda por implementar

- **Testar contra bench real** assim que houver um disponível — é o próximo risco
  real deste incremento (campo renomeado, ordem de execução diferente da lida no
  código-fonte, validação de `Salary Component` que exija mais campos do que os
  três preenchidos aqui).
- **Escolha de regime do IRRF** (simplificado × deduções reais) por funcionário —
  bloqueado por falta de campo no `hrms` para guardar a escolha.
- **Dependentes** na base do IRRF — mesmo bloqueio.
- **FGTS**, integrado por um caminho diferente deste hook (ver acima).

## Arquivos

- `integracao/folha.py` — `apply_regional_deductions`, `SALARY_COMPONENT_INSS/IRRF`.
- `setup/install.py` — `criar_componentes_salariais`.
- `hooks.py` — `regional_overrides["Brazil"]`.

## Fontes

- `hrms/__init__.py` (`allow_regional`, `get_region`) e
  `hrms/payroll/doctype/salary_slip/salary_slip.py`
  (`apply_regional_deductions`, `set_gross_pay_and_base_gross_pay`) — código-fonte
  lido diretamente do clone local (`G:\PROJECTS\hrms`, commit `51c2d3b`), não de
  documentação de terceiros. Consultado em 2026-08-30.
- `hrms/payroll/doctype/salary_detail/salary_detail.json` — formato da linha de
  dedução (`salary_component` obrigatório, `amount`).
