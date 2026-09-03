# Tradução: o que o ERPNext Brasil traduz, e o que corrige

Pedido do usuário: "falta também a tradução total do ERPNext Brasil, naquilo que não está
já traduzido". O levantamento mostrou que a pergunta tem duas respostas diferentes, e a
segunda é a que importa.

## Este app não precisa ser traduzido — ele já nasce em português

Regra do projeto desde o início: rótulo, mensagem, docstring e nome de função em pt-BR
(ver as convenções em `docs/README.md`). Não existe uma versão em inglês para traduzir.
Um `locale/pt_BR.po` que traduzisse as strings deste app para português seria
identidade — entradas onde original e tradução são iguais, que não fazem nada.

O teste `test_locale.py::test_nenhuma_traducao_igual_ao_original` trava exatamente isso.

## O que faltava de verdade: **corrigir** a tradução do ERPNext

O que o usuário brasileiro vê não é só o nosso app — é o ERPNext inteiro, cuja tradução
pt-BR tem erros objetivos no vocabulário contábil e fiscal. Sem um `locale/`, o app não
tinha como corrigi-los.

### O mecanismo, verificado no código-fonte (não suposto)

`frappe/translate.py::get_translations_from_apps`:

```python
for app in apps or frappe.get_installed_apps(_ensure_on_bench=True):
    translations.update(get_translations_from_csv(lang, app) or {})
    translations.update(get_translations_from_mo(lang, app) or {})
```

Três fatos que decorrem daí:

1. as traduções de **todos os apps instalados são combinadas**;
2. a combinação é `dict.update()` — **o último app sobrescreve os anteriores**;
3. como o `erpnext_brasil` é instalado depois do `erpnext`, o que estiver no nosso
   `locale/` **prevalece**.

Também confirmado no bench: o **Frappe 15+** usa `locale/<lang>.po` (gettext), enquanto o
**ERPNext ainda usa** `translations/<lang>.csv` (formato legado) — os dois são lidos, e o
`.mo` (PO compilado) vem depois do CSV. Por isso o arquivo novo é
`erpnext_brasil/locale/pt_BR.po`, com **underscore**, não hífen.

## As correções, e a fonte de cada uma

Critério de entrada: só correção que se sustenta numa fonte objetiva. Preferência
estilística não entra — sobrescrever a tradução de outro app é poder que se usa com
parcimônia.

| Termo | ERPNext traduz | Aqui | Por quê |
|---|---|---|---|
| `Tax ID` | `Cpf/cnpj` | **CPF/CNPJ** | São siglas (Cadastro de Pessoas Físicas, Cadastro Nacional da Pessoa Jurídica) e se escrevem em caixa alta |
| `Fixed Asset` | `Ativo Fixo` | **Imobilizado** | Lei 6.404/76, Art. 178, §1º. "Ativo Fixo" é tradução literal, não é o termo do balanço brasileiro |
| `Cost of Goods Sold` | `Custo Dos Produtos Vendidos` | **Custo dos Produtos Vendidos** | Em título, preposição vai em minúscula |
| `Item Variants` | `Variantes Dos Itens` | **Variantes dos Itens** | Mesma regra |

Mais alguns termos fiscais que o núcleo simplesmente não conhece (Chave de Acesso,
Protocolo de Autorização, Certificado Digital, Regime Tributário) — esses não são
correção, são vocabulário que só existe numa instalação brasileira.

### Achado: o ERPNext se contradiz dentro do próprio arquivo

`pt-BR.csv` usa **"Ativo Fixo"** numa linha e **"Ativo Imobilizado"** em outra. Não é
questão de gosto entre duas opções válidas: é inconsistência dentro da mesma tradução, e
uma das duas está fora do vocabulário legal. `contabil/plano_de_contas.py` já usava
"Imobilizado" — agora a tela fala a mesma língua do código, que é o princípio de
linguagem ubíqua aplicado à interface.

`test_locale.py::test_imobilizado_bate_com_o_plano_de_contas` amarra os dois: se alguém
mudar o plano de contas sem mudar a tradução (ou vice-versa), o teste acusa.

### O que ficou de fora, e por quê

A auditoria encontrou **257 ocorrências** de preposição em maiúscula e **25** de `&quot;`
vazando para a tela no `pt-BR.csv` do ERPNext. Corrigi apenas as que aparecem no contexto
fiscal/contábil que este app toca.

Corrigir as 257 seria assumir a manutenção da tradução inteira do ERPNext dentro de um app
de localização fiscal — responsabilidade que não é deste projeto e que envelheceria a cada
versão do ERPNext. **O caminho certo para essas é contribuir de volta ao Crowdin do
ERPNext**, não sobrescrevê-las aqui.

## Como compilar e testar no bench

```sh
bench --site <site> compile-po-to-mo --app erpnext_brasil
bench --site <site> clear-cache
```

O `.po` é a fonte versionada; o `.mo` é gerado e não vai para o repositório.

`tests/test_locale.py` verifica o que não depende de bench: arquivo no lugar certo,
cabeçalho válido, nenhuma entrada vazia, duplicada ou idêntica ao original, e cada uma
das correções acima.
