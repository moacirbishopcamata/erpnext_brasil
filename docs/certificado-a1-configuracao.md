# Certificado A1 e ambiente SEFAZ — configuráveis pela interface

Pedido direto do usuário: *"Para certificados tipo A1, deve ser possível sua inserção via
configurações"* e *"Qualquer outro tipo de 'chave' ou URL para validação deve estar em
configurações"*.

## O que já existia, e o que faltava

`integracao/transporte_sefaz.py::TransporteSefaz.__init__` já aceitava o certificado como
bytes crus (`pfx: bytes`) e a senha como texto puro — nunca exigiu um caminho de arquivo no
disco (`_preparar_arquivos_tls` só escreve os PEM derivados num diretório temporário depois
de já ter o certificado em memória, via `cryptography`). O que faltava era **o lado do
ERPNext**: de onde esses bytes/senha vêm. Antes deste incremento, não existia nenhum jeito
de configurar isso pela interface — transmitir de verdade exigia escrever código Python
passando o `.pfx` na mão.

## O que foi implementado

### Campos novos em `Company` (`setup/custom_fields.py`)

- **`br_certificado_a1`** (`Attach`) — o arquivo `.pfx`/`.p12` do certificado digital.
- **`br_senha_certificado_a1`** (`Password`) — a senha do certificado. O Frappe
  criptografa valores de campo `Password` automaticamente (tabela `__Auth`); nunca fica em
  texto puro no banco, mesma garantia que qualquer outra senha do sistema.
- **`br_ambiente_sefaz`** (`Select`, "Produção"/"Homologação") — **padrão "Homologação"**,
  nunca "Produção" de fábrica: uma instalação nova nunca transmite de verdade sem alguém
  trocar essa opção conscientemente.

### `integracao/certificado_a1.py` — a leitura

- `carregar_certificado_da_empresa(company)` devolve `(pfx_bytes, senha)`, prontos para
  `TransporteSefaz(pfx, senha, ...)`. Levanta `CertificadoA1Ausente` (nunca devolve
  certificado parcial) quando falta o arquivo, a senha, ou os dois — falhar alto aqui é
  melhor que `TransporteSefaz` tentar abrir um PKCS#12 vazio e devolver um erro de
  criptografia sem contexto nenhum de qual campo está faltando.
- `ambiente_sefaz_da_empresa(company)` traduz o `Select` (`"Produção"`/`"Homologação"`)
  para os valores que `TransporteSefaz`/`autorizadores_*.endpoint` esperam
  (`"producao"`/`"homologacao"`) — qualquer valor diferente de `"Produção"` (incluindo
  vazio) resolve para `"homologacao"`, o padrão seguro.

## Por que `Company`, e não um doctype de configuração separado

O certificado A1 é emitido **por CNPJ** — é a identidade digital daquele CNPJ perante a
Receita/SEFAZ. `Company` já é o cadastro que carrega o CNPJ (`tax_id`) e o resto dos dados
fiscais deste app (`regime_tributario`, `inscricao_estadual`, `chave_pix`). Um doctype de
configuração à parte duplicaria a amarração "qual CNPJ" que `Company` já resolve sozinho,
sem ganho nenhum.

## O que foi deliberadamente **não** movido para configurações

Levantamento feito antes de implementar, não suposto: os únicos outros dados externos
fixos no projeto são as **tabelas de autorizador por UF**
(`fiscal/documento/autorizadores_sefaz.py`/`autorizadores_cte.py`/`autorizadores_mdfe.py`,
ver `docs/transporte-nativo-sefaz.md`/`docs/cte-mdfe-autorizadores.md`) — URLs oficiais do
SEFAZ de cada UF, lidas do Portal Nacional/`nfephp-org` e verificadas campo a campo contra
a fonte. Essas **não** viram campo configurável: são infraestrutura fixa definida pelo
governo, não um segredo do usuário — torná-las editáveis pela UI trocaria uma tabela
verificada por um campo de texto livre que um erro de digitação deixaria enviando
declaração fiscal para lugar nenhum, sem nenhum ganho real de flexibilidade (a UF de cada
`Company`/documento já decide sozinha qual endpoint usar). Nenhuma outra chave de API,
token ou URL de validação de terceiro foi encontrada hardcoded no projeto.

## Sem teste dedicado

`certificado_a1.py` depende de `frappe.get_doc`/`get_password`, que só funcionam dentro de
um site real — não testável sem bench, mesma disciplina já aplicada a todo o resto de
`integracao/` (`party.py`, `cte_extracao.py`, `chave_acesso_documento.py`).

## O que ainda falta

Nenhum `doc_event`/fluxo ainda **chama** `carregar_certificado_da_empresa`/
`ambiente_sefaz_da_empresa` para de fato instanciar `TransporteSefaz` e transmitir — os
campos e a leitura existem, mas a orquestração de "quando transmitir" continua não
implementada, mesma pendência já registrada para NF-e (`docs/transporte-nativo-sefaz.md`,
seção "Ainda por implementar") e agora também para CT-e/MDF-e. Não testável de ponta a
ponta sem um certificado A1 real e ambiente de homologação da SEFAZ.
