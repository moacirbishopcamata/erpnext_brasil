# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Eventos do CT-e: cancelamento (`tpEvento` 110111, `evCancCTe`), carta de correção
(`tpEvento` 110110, `evCCeCTe`), comprovante de entrega (`tpEvento` 110180, `evCECTe`),
EPEC (`tpEvento` 110113, `evEPECCTe`), cancelamento do comprovante de entrega (`tpEvento`
110181, `evCancCECTe`), insucesso na entrega (`tpEvento` 110190, `evIECTe`), cancelamento
do insucesso na entrega (`tpEvento` 110191, `evCancIECTe`), informações da GTV (`tpEvento`
110170, `evGTV`), prestação do serviço em desacordo (`tpEvento` 610110, `evPrestDesacordo`),
seu cancelamento (`tpEvento` 610111, `evCancPrestDesacordo`) e registro multimodal
(`tpEvento` 110160, `evRegMultimodal`) — o último dos onze eventos do CT-e v4.00.

Por que existe
--------------
Fecha mais uma peça de infraestrutura do CT-e, no mesmo espírito de `fiscal/documento/
evento.py` (NF-e). Verificado campo a campo contra o XSD literal (`evCancCTe_v4.00.xsd`,
36 linhas — lido inteiro — e `eventoCTeTiposBasico_v4.00.xsd`, `nfephp-org/sped-cte`), não
suposto por analogia com a NF-e — que, como os incrementos anteriores do CT-e já mostraram
repetidas vezes (`modal`, `procEmi`, `ideEvento`), às vezes bate e às vezes diverge.

`tpEvento` idêntico, `detEvento` idêntico — mas dois pontos genuinamente divergentes
------------------------------------------------------------------------------------------
O código do evento (`"110111"`) e o corpo de `detEvento` (`descEvento`="Cancelamento",
`nProt`, `xJust`) são **idênticos** aos da NF-e — confirmado, não copiado às cegas. Dois
pontos, porém, divergem de verdade:

1. **Limite da justificativa**: `TJust` do CT-e é `minLength=15, maxLength=255` — a NF-e usa
   `256` (`estado.JUSTIFICATIVA_MAXIMA`). Um caractere de diferença que reaproveitar a
   constante da NF-e teria deixado passar despercebido até uma justificativa de exatamente
   256 caracteres ser rejeitada pela SEFAZ.
2. **Onde a versão do evento mora**: a NF-e tem um elemento `verEvento` dentro de
   `infEvento`, fixo em `"1.00"` — independente da versão do próprio leiaute da NF-e. O CT-e
   **não tem** esse elemento; a versão vive só como atributo `detEvento/@versaoEvento`
   (confirmado, padrão `"4.NN"`) e, no nível do `evento` inteiro, `@versao` (tipo
   `TVerEvento`, valor fixo `"4.00"`) — a mesma versão do leiaute do CT-e, não uma numeração
   de evento independente como a NF-e usa.

`@Id` tem 53 dígitos, não 52 — `nSeqEvento` entra com 3 dígitos, não 2
------------------------------------------------------------------------------------------
Confirmado por leitura direta: o padrão é `ID[0-9]{53}` (contra `ID[0-9]{52}` da NF-e). A
composição é a mesma (`"ID" + tpEvento(6) + chave(44) + nSeqEvento`), mas o `nSeqEvento`
dentro do `@Id` do CT-e usa **3** dígitos com zero à esquerda (`"001"`), não 2 (`"01"`) — a
diferença de um dígito no padrão do `@Id` bate exatamente com essa mudança de largura.

A carta de correção do CT-e não é texto livre — é uma lista estruturada de alterações
------------------------------------------------------------------------------------------
Achado real, verificado em `evCCeCTe_v4.00.xsd` (98 linhas, lido inteiro): diferente da NF-e
(`xCorrecao`, texto livre de 15 a 1000 caracteres), a CC-e do CT-e é `infCorrecao`, uma lista
repetível (`maxOccurs="unbounded"`) de correções campo a campo — cada item tem `grupoAlterado`
(o grupo do XSD, ex. `"ide"`, 1-20 caracteres), `campoAlterado` (o nome do campo, 1-20
caracteres), `valorAlterado` (o novo valor, 1-500 caracteres) e `nroItemAlterado` (opcional, o
índice quando o campo corrigido está numa lista — "o índice inicia sempre em 1"). Modelar isso
como texto livre (copiando a forma da NF-e) perderia a estrutura que o schema exige.

`xCondUso` cita uma base legal diferente da NF-e — não é o mesmo texto com nome trocado
------------------------------------------------------------------------------------------
A NF-e cita o § 1º-A do art. 7º do Convênio S/N de 15/12/1970. O CT-e cita o **Art. 58-B do
Convênio SINIEF 06/89** — uma norma diferente, com texto integralmente diferente (a lista de
restrições também muda: a NF-e fala em "remetente ou destinatário", o CT-e em "emitente,
tomador, remetente ou destinatário" — mais uma parte porque o CT-e tem mais papéis
envolvidos). `XCONDUSO_CCE_CTE` é uma constante nova, não um reaproveitamento com o nome
trocado.

Reuso: `assinar_evento` e `EventoInvalido` de `evento.py`, sem alteração
------------------------------------------------------------------------------
`assinar_evento` já era genérica (não hardcoda `NAMESPACE_NFE`, só lê o que o dicionário
`evento` já tem) — reaproveitada direto. `EventoInvalido` também: mensagem + campo, nenhuma
lógica específica de NF-e embutida.

Comprovante de entrega (`tpEvento` 110180) — código próprio, sem equivalente na NF-e
------------------------------------------------------------------------------------------
Verificado em `evCECTe_v4.00.xsd` (108 linhas, lido inteiro): quem recebeu a carga confirma
o recebimento — `nProt` (protocolo do CT-e), `dhEntrega`, `nDoc`/`xNome` (documento e nome de
quem recebeu), `latitude`/`longitude` opcionais (coordenadas do ponto de entrega, confirmadas
como string de 6 casas decimais, não decimal puro — `TLatitude`/`TLongitude`), `hashEntrega`
(obrigatório) e `dhHashEntrega`. `infEntrega` (opcional, até 2000) referencia as NF-e
efetivamente entregues — mesma chave de acesso já validada em `fiscal.cte.montar_infnfe`,
reaproveitada aqui via `ler_chave`.

`hashEntrega` é um cálculo real, não um campo de texto livre
------------------------------------------------------------------------------
Confirmado no XSD: `base64Binary` de comprimento **20 bytes** — exatamente o tamanho de um
digest SHA-1 (não coincidência: a documentação do campo descreve o hash como "SHA1 no formato
Base64 resultante da concatenação: Chave de acesso do CT-e + Base64 da imagem capturada da
entrega"). `calcular_hash_entrega` implementa esse cálculo de verdade — `hashlib.sha1` sobre
`chave + imagem_base64` (concatenação de texto, não de bytes brutos: a "imagem capturada" já
entra como sua própria representação Base64, string), devolvendo o digest de 20 bytes
recodificado em Base64 (28 caracteres com padding).

EPEC (`tpEvento` 110113) — código próprio, e um `toma4` que não é o `toma4` da `ide`
------------------------------------------------------------------------------------------
Verificado em `evEPECCTe_v4.00.xsd` (161 linhas, lido inteiro). EPEC é a prévia enviada em
contingência (o emitente avisa a existência do CT-e antes de conseguir autorização de verdade)
— carrega um resumo do documento: `xJust`, `vICMS`/`vICMSST` (opcional)/`vTPrest`/`vCarga`,
`modal` (mesmas seis opções já usadas em `fiscal.cte.MODAL_*`), `UFIni`/`UFFim`, `tpCTe`
(**restrito a `"0"` — só CT-e Normal**, diferente do `tpCTe` da `ide`, que aceita `0`/`1`/`3`)
e `dhEmi`.

**Achado real, não suposto**: o grupo chamado `toma4` aqui **não é** o `toma4` de
`fiscal.cte.montar_toma4` — tem o mesmo nome, forma parecida, mas `toma` aceita `"0"`-`"4"`
(qualquer papel: remetente/expedidor/recebedor/destinatário/outros), não fixo em `"4"` como no
`toma4` real do `ide` (que só serve para "Outros"). É uma versão resumida/genérica do
tomador para a prévia de contingência, sem `xNome`/`enderToma`/`email` — só `toma`, `UF`,
CNPJ/CPF e `IE` opcional. Reaproveitar `fiscal.cte.TomadorOutros`/`montar_toma4` aqui exigiria
ou inventar dados que o EPEC não pede, ou aceitar `papel` fixo em `"4"` quando o XSD permite
qualquer um — por isso `TomadorEpec`/`montar_tomador_epec` são um tipo à parte.

Cancelamento do comprovante de entrega (`tpEvento` 110181) e cancelamento do insucesso na
entrega (`tpEvento` 110191) — "CE" é Comprovante de Entrega, não Carta de Correção
------------------------------------------------------------------------------------------
**Achado real, não suposto pelo nome do arquivo**: `evCancCECTe_v4.00.xsd` (36 linhas, lido
inteiro) descreve, no seu próprio texto (`xs:documentation`), o "cancelamento do comprovante
de entrega eletrônico do CT-e" — a sigla `CE` aqui é **Comprovante de Entrega** (o evento
`evCECTe`, `tpEvento` 110180, desta mesma frente), **não** Carta de Correção (`evCCeCTe`,
que tem sua própria sigla `CCe`, diferente). O nome do arquivo, por analogia solta com
`evCancCTe`/`evCCeCTe`, sugeriria "cancelamento da carta de correção" — leitura do XSD
confirma que não é isso. Corpo simples: `descEvento` fixo ("Cancelamento do Comprovante de
Entrega do CT-e"), `nProt` (protocolo do próprio CT-e) e `nProtCE` (protocolo do evento de
comprovante de entrega que está sendo cancelado) — os dois do tipo `TProt`.

`evCancIECTe_v4.00.xsd` (36 linhas, lido inteiro) é **estruturalmente idêntico**, confirmado
campo a campo: mesmo `descEvento` fixo (texto diferente, "Cancelamento do Insucesso de
Entrega do CT-e"), mesmo `nProt`, e `nProtIE` no lugar de `nProtCE` (protocolo do evento de
insucesso na entrega cancelado). Por ser uma segunda instância real (não hipotética) do mesmo
formato — cancelar um evento de entrega informando o protocolo do CT-e e o protocolo do
evento cancelado —, os dois reaproveitam `_montar_evento_cancelamento_protocolo`, uma função
privada só deste módulo, em vez de duplicar a mesma validação duas vezes.

Insucesso na entrega (`tpEvento` 110190, `evIECTe`) — quase gêmeo do comprovante de entrega,
com duas divergências reais
------------------------------------------------------------------------------------------
Verificado em `evIECTe_v4.00.xsd` (126 linhas, lido inteiro): estrutura muito parecida com
`evCECTe` (comprovante de entrega) — `nProt`, `latitude`/`longitude` opcionais, hash
opcional (`hashTentativaEntrega`)/`dhHashTentativaEntrega`, `infEntrega` (mesma forma,
reaproveitada via `_montar_inf_entrega_nfe`). Campos próprios: `dhTentativaEntrega`
(obrigatório), `nTentativa` (opcional, `[0-9]{3}`), `tpMotivo` (enum "1"-"4": recebedor não
encontrado / recusa do recebedor / endereço inexistente / outros) e `xJustMotivo`
(obrigatório **só** quando `tpMotivo="4"`, regra de negócio do próprio texto do XSD, não do
`minOccurs` sozinho).

**Achado real**: `xJustMotivo` usa o tipo `TString` (`minLength=15, maxLength=256`), **não**
`TJust` (`minLength=15, maxLength=255`, usado no cancelamento e no EPEC deste mesmo
documento) — o limite aqui é **256**, igual ao da NF-e, não 255 como os outros textos livres
do CT-e. Reaproveitar `JUSTIFICATIVA_MAXIMA_CTE` (255) teria rejeitado um texto de 256
caracteres que o XSD aceita — por isso este evento valida com seu próprio limite
(`XJUSTMOTIVO_MAXIMO_IE_CTE = 256`), não a constante do cancelamento.

**Achado real 2**: diferente de `evCECTe`, onde `hashEntrega` é **obrigatório**, aqui
`hashTentativaEntrega` é **opcional** (`minOccurs="0"`) — faz sentido: uma tentativa
malsucedida pode não ter conseguido capturar imagem nenhuma do local. O cálculo, quando
informado, é o mesmo SHA-1+Base64 de `calcular_hash_entrega` — reaproveitado sem alteração
(o nome do campo muda, o algoritmo não).

Informações da GTV (`tpEvento` 110170, `evGTV`) — para o CT-e de transporte de valores
------------------------------------------------------------------------------------------
Verificado em `evGTV_v4.00.xsd` (255 linhas, lido inteiro): registra os documentos GTV
(Guia de Transporte de Valores, o documento que acoberta o transporte de numerário/cheque/
moeda para o setor de valores) efetivamente transportados por um CT-e. `infGTV` é uma lista
(`maxOccurs="unbounded"`) — um único evento pode reportar várias GTV. Cada item tem `nDoc`
(número, 1-20 caracteres), `id` (identificador para diferenciar GTV de mesmo número — AIDF
ou identificador interno), `serie`/`subserie` (opcionais, 1-3), `dEmi`, `nDV` (dígito
verificador, exatamente 1 caractere), `qCarga` (quantidade de volumes/malotes),
`infEspecie` (lista, ao menos uma — tipo de espécie 1-Numerário/2-Cheque/3-Moeda/4-Outros,
com `vEspecie` opcional), `rem`/`dest` (remetente/destinatário — mesma forma exata:
CNPJ/CPF, IE opcional, UF, `xNome`), `placa`/`UF`(do veículo)/`RNTRC` (todos opcionais).

**Achado real**: `descEvento` tem **duas** enumerações válidas no XSD — `"Informações da
GTV"` (com acento) e `"Informacoes da GTV"` (sem acento) — não é erro de digitação deste
projeto, é o próprio schema aceitando as duas grafias. Este módulo sempre **grava** a forma
acentuada (`"Informações da GTV"`), consistente com o restante do projeto, mas documenta a
divergência para quem for validar contra um XML de terceiro que use a grafia sem acento.

**Reuso**: `validar_rntrc`/`RntrcInvalido` de `fiscal.cte_rodoviario` (mesmo `RNTRC`,
mesmo padrão `[0-9]{8}|ISENTO`, sem inventar validação nova). `rem`/`dest` compartilham a
mesma forma exata no XSD — modelados com um único tipo, `ParteGtv`, montado por uma única
função, em vez de duas classes idênticas com nomes diferentes.

**Fora de escopo, documentado**: `CNPJ` de `rem`/`dest` é `TCnpjOpc`, que aceita
`"00000000000000"` para remetente/destinatário não estabelecido no Brasil — `validar_cnpj`
deste projeto rejeita ativamente CNPJ com todos os dígitos iguais (incluindo zeros), por
desenho (ver `fiscal/validators.py`). Este evento não abre uma exceção para esse caso —
GTV de remetente/destinatário estrangeiro não é suportado por enquanto.

Prestação em desacordo (`tpEvento` 610110) e seu cancelamento (`tpEvento` 610111) —
achado real: primeiro `tpEvento` fora da família `110xxx`
------------------------------------------------------------------------------------------
Verificado em `evPrestDesacordo_v4.00.xsd` (49 linhas, lido inteiro) e
`evCancPrestDesacordo_v4.00.xsd` (32 linhas, lido inteiro). **Achado real, confirmado, não
suposto**: todos os oito eventos anteriores desta frente têm `tpEvento` no padrão `110xxx`
(cancelamento, CC-e, comprovante de entrega, EPEC, cancelamento do comprovante de entrega,
insucesso na entrega, cancelamento do insucesso na entrega, GTV). Este é o primeiro no
padrão **`610xxx`** — `"610110"` e `"610111"`. O prefixo diferente não muda nada na
composição do `@Id` (ainda 6 dígitos de `tpEvento`), mas é um lembrete de que não dá para
supor a faixa de código de um evento pelo padrão dos anteriores — cada tipo de evento do
CT-e tem seu próprio código, sem relação sequencial garantida com os demais.

`evPrestDesacordo` (o tomador reporta desacordo com a prestação): `indDesacordoOper` é uma
enumeração de **um único valor** (`"1"`) — campo aparentemente supérfluo (só existe um valor
possível), mantido porque é assim que o XSD define. `xObs` (observações do tomador,
15-255 caracteres) segue o mesmo padrão de "duas grafias" já visto em `evGTV` para
`descEvento` (`"Prestação"`/`"Prestacao"`) — este módulo grava a forma acentuada.

`evCancPrestDesacordo` **diverge da forma dos cancelamentos anteriores**: `evCancCECTe`/
`evCancIECTe` carregam dois protocolos (`nProt` do CT-e + o protocolo do evento cancelado).
Este cancelamento carrega **só um**, `nProtEvPrestDes` (o protocolo do `evPrestDesacordo`
sendo cancelado) — sem `nProt` do CT-e. Por isso **não** reaproveita
`_montar_evento_cancelamento_protocolo` (que exige os dois protocolos); é uma função própria.

Registro multimodal (`tpEvento` 110160, `evRegMultimodal`) — o último dos onze eventos do
CT-e v4.00
------------------------------------------------------------------------------------------
Verificado em `evRegMultimodal_v4.00.xsd` (51 linhas, lido inteiro). Volta ao padrão
`110xxx` (`"110160"`) — não segue a exceção `610xxx` do evento anterior, confirmando de
novo que não dá para prever o código de um evento pelo padrão do vizinho. `descEvento` tem
**uma única** grafia válida ("Registro Multimodal") — diferente de `evGTV`/
`evPrestDesacordo`, que aceitavam duas. `xRegistro` (texto livre sobre o registro no
multimodal) vai até **1000** caracteres — o maior limite de texto livre entre os eventos do
CT-e nesta frente (os demais ficam em 255/256). `nDoc` (opcional) é o "número do documento
lançado no CT-e Multimodal" — **achado real**: apesar do comprimento (1-44) coincidir com o
de uma chave de acesso, o XSD tipa como `[0-9]{1,44}` solto, não como `TChDFe` (o tipo usado
em `chNFe`/`chCTe` em todo lugar que é de fato uma chave) — este módulo não valida `nDoc`
como chave de acesso (sem dígito verificador, sem decompor UF/CNPJ/modelo), só confere que
é uma string numérica de até 44 dígitos, fiel ao que o schema realmente pede.

Funções puras: nenhuma dependência do Frappe.
"""

import base64
import hashlib
from dataclasses import dataclass

from erpnext_brasil.fiscal.cte import (
	MODAL_AEREO,
	MODAL_AQUAVIARIO,
	MODAL_DUTOVIARIO,
	MODAL_FERROVIARIO,
	MODAL_MULTIMODAL,
	MODAL_RODOVIARIO,
	NAMESPACE_CTE,
	TIPO_CTE_NORMAL,
)
from erpnext_brasil.fiscal.cte_rodoviario import RntrcInvalido, validar_rntrc
from erpnext_brasil.fiscal.documento.chave_acesso import ler_chave, validar_chave
from erpnext_brasil.fiscal.documento.evento import EventoInvalido, assinar_evento
from erpnext_brasil.fiscal.validators import validar_cnpj, validar_cpf_cnpj

__all__ = [
	"DESC_EVENTO_GTV",
	"ESPECIE_GTV_CHEQUE",
	"ESPECIE_GTV_MOEDA",
	"ESPECIE_GTV_NUMERARIO",
	"ESPECIE_GTV_OUTROS",
	"DESC_EVENTO_REGISTRO_MULTIMODAL",
	"INDICADOR_DESACORDO_OPERACAO",
	"JUSTIFICATIVA_MAXIMA_CTE",
	"JUSTIFICATIVA_MINIMA_CTE",
	"MOTIVO_INSUCESSO_ENDERECO_INEXISTENTE",
	"MOTIVO_INSUCESSO_OUTROS",
	"MOTIVO_INSUCESSO_RECEBEDOR_NAO_ENCONTRADO",
	"MOTIVO_INSUCESSO_RECUSA_RECEBEDOR",
	"TIPO_EVENTO_CANCELAMENTO_COMPROVANTE_ENTREGA_CTE",
	"TIPO_EVENTO_CANCELAMENTO_CTE",
	"TIPO_EVENTO_CANCELAMENTO_INSUCESSO_ENTREGA_CTE",
	"TIPO_EVENTO_CANCELAMENTO_PRESTACAO_DESACORDO_CTE",
	"TIPO_EVENTO_COMPROVANTE_ENTREGA_CTE",
	"TIPO_EVENTO_CORRECAO_CTE",
	"TIPO_EVENTO_EPEC_CTE",
	"TIPO_EVENTO_GTV_CTE",
	"TIPO_EVENTO_INSUCESSO_ENTREGA_CTE",
	"TIPO_EVENTO_PRESTACAO_DESACORDO_CTE",
	"TIPO_EVENTO_REGISTRO_MULTIMODAL_CTE",
	"TOMADOR_EPEC_DESTINATARIO",
	"TOMADOR_EPEC_EXPEDIDOR",
	"TOMADOR_EPEC_OUTROS",
	"TOMADOR_EPEC_RECEBEDOR",
	"TOMADOR_EPEC_REMETENTE",
	"XCONDUSO_CCE_CTE",
	"XJUSTMOTIVO_MAXIMO_IE_CTE",
	"XJUSTMOTIVO_MINIMO_IE_CTE",
	"XOBS_MAXIMO_DESACORDO_CTE",
	"XOBS_MINIMO_DESACORDO_CTE",
	"XREGISTRO_MAXIMO_MULTIMODAL_CTE",
	"XREGISTRO_MINIMO_MULTIMODAL_CTE",
	"CorrecaoCte",
	"EspecieGtv",
	"EventoInvalido",
	"InfGtv",
	"ParteGtv",
	"TomadorEpec",
	"assinar_evento",
	"calcular_hash_entrega",
	"montar_env_evento_cte",
	"montar_evento_cancelamento_comprovante_entrega_cte",
	"montar_evento_cancelamento_cte",
	"montar_evento_cancelamento_insucesso_entrega_cte",
	"montar_evento_cancelamento_prestacao_desacordo_cte",
	"montar_evento_comprovante_entrega_cte",
	"montar_evento_correcao_cte",
	"montar_evento_epec_cte",
	"montar_evento_gtv_cte",
	"montar_evento_insucesso_entrega_cte",
	"montar_evento_prestacao_desacordo_cte",
	"montar_evento_registro_multimodal_cte",
	"montar_parte_gtv",
	"montar_tomador_epec",
]

TIPO_EVENTO_CANCELAMENTO_CTE = "110111"
TIPO_EVENTO_CORRECAO_CTE = "110110"
TIPO_EVENTO_COMPROVANTE_ENTREGA_CTE = "110180"
TIPO_EVENTO_EPEC_CTE = "110113"
TIPO_EVENTO_CANCELAMENTO_COMPROVANTE_ENTREGA_CTE = "110181"
TIPO_EVENTO_INSUCESSO_ENTREGA_CTE = "110190"
TIPO_EVENTO_CANCELAMENTO_INSUCESSO_ENTREGA_CTE = "110191"
TIPO_EVENTO_GTV_CTE = "110170"

# Achado real: o XSD aceita as duas grafias ("Informações"/"Informacoes") -- ver docstring
# do módulo. Este projeto sempre grava a forma acentuada.
DESC_EVENTO_GTV = "Informações da GTV"

ESPECIE_GTV_NUMERARIO = "1"
ESPECIE_GTV_CHEQUE = "2"
ESPECIE_GTV_MOEDA = "3"
ESPECIE_GTV_OUTROS = "4"

_ESPECIES_GTV_VALIDAS = {
	ESPECIE_GTV_NUMERARIO, ESPECIE_GTV_CHEQUE, ESPECIE_GTV_MOEDA, ESPECIE_GTV_OUTROS,
}

# Achado real: primeiro tpEvento fora da família "110xxx" desta frente -- ver docstring.
TIPO_EVENTO_PRESTACAO_DESACORDO_CTE = "610110"
TIPO_EVENTO_CANCELAMENTO_PRESTACAO_DESACORDO_CTE = "610111"

# indDesacordoOper é uma enumeração de um único valor no XSD -- mantido por fidelidade ao
# schema, não porque faça sentido sozinho.
INDICADOR_DESACORDO_OPERACAO = "1"

XOBS_MINIMO_DESACORDO_CTE = 15
XOBS_MAXIMO_DESACORDO_CTE = 255

TIPO_EVENTO_REGISTRO_MULTIMODAL_CTE = "110160"
DESC_EVENTO_REGISTRO_MULTIMODAL = "Registro Multimodal"

# xRegistro é o texto livre de maior limite entre os eventos do CT-e nesta frente (1000,
# não 255/256) -- ver docstring do módulo.
XREGISTRO_MINIMO_MULTIMODAL_CTE = 15
XREGISTRO_MAXIMO_MULTIMODAL_CTE = 1000

MOTIVO_INSUCESSO_RECEBEDOR_NAO_ENCONTRADO = "1"
MOTIVO_INSUCESSO_RECUSA_RECEBEDOR = "2"
MOTIVO_INSUCESSO_ENDERECO_INEXISTENTE = "3"
MOTIVO_INSUCESSO_OUTROS = "4"

_MOTIVOS_INSUCESSO_VALIDOS = {
	MOTIVO_INSUCESSO_RECEBEDOR_NAO_ENCONTRADO, MOTIVO_INSUCESSO_RECUSA_RECEBEDOR,
	MOTIVO_INSUCESSO_ENDERECO_INEXISTENTE, MOTIVO_INSUCESSO_OUTROS,
}

# `xJustMotivo` do evIECTe usa TString (15-256), não TJust (15-255, usada em cancelamento/
# EPEC) -- achado real, ver docstring do módulo.
XJUSTMOTIVO_MINIMO_IE_CTE = 15
XJUSTMOTIVO_MAXIMO_IE_CTE = 256

# `toma` do `toma4` do EPEC — aceita os 5 papéis, diferente do `toma4` real do `ide`
# (que só serve para "4"-Outros). Ver docstring do módulo.
TOMADOR_EPEC_REMETENTE = "0"
TOMADOR_EPEC_EXPEDIDOR = "1"
TOMADOR_EPEC_RECEBEDOR = "2"
TOMADOR_EPEC_DESTINATARIO = "3"
TOMADOR_EPEC_OUTROS = "4"

_TOMADORES_EPEC_VALIDOS = {
	TOMADOR_EPEC_REMETENTE, TOMADOR_EPEC_EXPEDIDOR, TOMADOR_EPEC_RECEBEDOR,
	TOMADOR_EPEC_DESTINATARIO, TOMADOR_EPEC_OUTROS,
}

# `modal` do EPEC — mesmas seis opções de `fiscal.cte.MODAL_*`, reaproveitadas por valor
# (não pelo nome do módulo, para este arquivo não depender de um `_MODAIS_VALIDOS`
# privado de outro módulo).
_MODAIS_VALIDOS_EPEC = {
	MODAL_RODOVIARIO, MODAL_AEREO, MODAL_AQUAVIARIO,
	MODAL_FERROVIARIO, MODAL_DUTOVIARIO, MODAL_MULTIMODAL,
}
_VERSAO_LEIAUTE_CTE = "4.00"

# `TJust` do CT-e — diverge do máximo de 256 da NF-e (`estado.JUSTIFICATIVA_MAXIMA`).
JUSTIFICATIVA_MINIMA_CTE = 15
JUSTIFICATIVA_MAXIMA_CTE = 255

# Texto fixo de `xCondUso` da CC-e do CT-e — confirmado caractere a caractere em
# `evCCeCTe_v4.00.xsd`. Base legal diferente da NF-e (Art. 58-B do Convênio SINIEF 06/89,
# não o Art. 7º do Convênio S/N de 1970) — não é o mesmo texto com o nome do documento
# trocado, ver docstring do módulo.
XCONDUSO_CCE_CTE = (
	"A Carta de Correção é disciplinada pelo Art. 58-B do CONVÊNIO/SINIEF 06/89: Fica "
	"permitida a utilização de carta de correção, para regularização de erro ocorrido na "
	"emissão de documentos fiscais relativos à prestação de serviço de transporte, desde "
	"que o erro não esteja relacionado com: I - as variáveis que determinam o valor do "
	"imposto tais como: base de cálculo, alíquota, diferença de preço, quantidade, valor "
	"da prestação;II - a correção de dados cadastrais que implique mudança do emitente, "
	"tomador, remetente ou do destinatário;III - a data de emissão ou de saída."
)


def _formatar_id_cte(chave: str, tipo_evento: str, numero_sequencia: int) -> str:
	"""`"ID" + tpEvento + chave(44) + nSeqEvento(3, com zero à esquerda)` — 3 dígitos,
	não 2 como na NF-e (`evento._formatar_id`); confirmado pelo padrão `ID[0-9]{53}`."""
	return f"ID{tipo_evento}{chave}{numero_sequencia:03d}"


@dataclass(frozen=True)
class CorrecaoCte:
	"""Um item de `infCorrecao` — uma correção campo a campo (não texto livre, ver
	docstring do módulo)."""

	grupo_alterado: str
	campo_alterado: str
	valor_alterado: str
	numero_item_alterado: int | None = None

	def __post_init__(self):
		if not (1 <= len(self.grupo_alterado) <= 20):
			raise EventoInvalido(
				f"grupoAlterado deve ter de 1 a 20 caracteres, recebido {self.grupo_alterado!r}",
				"grupo_alterado",
			)

		if not (1 <= len(self.campo_alterado) <= 20):
			raise EventoInvalido(
				f"campoAlterado deve ter de 1 a 20 caracteres, recebido {self.campo_alterado!r}",
				"campo_alterado",
			)

		if not (1 <= len(self.valor_alterado) <= 500):
			raise EventoInvalido(
				f"valorAlterado deve ter de 1 a 500 caracteres, recebido {self.valor_alterado!r}",
				"valor_alterado",
			)

		if self.numero_item_alterado is not None and not (1 <= self.numero_item_alterado <= 99):
			raise EventoInvalido(
				f"nroItemAlterado deve estar entre 1 e 99 (o índice começa em 1), "
				f"recebido {self.numero_item_alterado}",
				"numero_item_alterado",
			)


def _montar_inf_correcao(correcao: CorrecaoCte) -> dict:
	item = {
		"grupoAlterado": correcao.grupo_alterado,
		"campoAlterado": correcao.campo_alterado,
		"valorAlterado": correcao.valor_alterado,
	}

	if correcao.numero_item_alterado is not None:
		item["nroItemAlterado"] = str(correcao.numero_item_alterado)

	return item


def montar_evento_cancelamento_cte(
	chave_acesso: str,
	protocolo: str,
	justificativa: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do cancelamento do CT-e.

	Mesma costura de `evento.montar_evento_cancelamento`, com as divergências
	confirmadas no XSD do CT-e: `chCTe` no lugar de `chNFe`, `versaoEvento` como
	atributo de `detEvento` no lugar do elemento `verEvento`, `@Id` de 53 dígitos, e
	limite de justificativa de 255 caracteres.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	texto_justificativa = (justificativa or "").strip()

	if not (JUSTIFICATIVA_MINIMA_CTE <= len(texto_justificativa) <= JUSTIFICATIVA_MAXIMA_CTE):
		raise EventoInvalido(
			f"A justificativa deve ter de {JUSTIFICATIVA_MINIMA_CTE} a "
			f"{JUSTIFICATIVA_MAXIMA_CTE} caracteres, recebidos {len(texto_justificativa)}",
			"justificativa",
		)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização é obrigatório para cancelar", "protocolo")

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_cte(chave, TIPO_EVENTO_CANCELAMENTO_CTE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_CANCELAMENTO_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_CTE,
			"descEvento": "Cancelamento",
			"nProt": protocolo_limpo,
			"xJust": texto_justificativa,
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


def montar_evento_correcao_cte(
	chave_acesso: str,
	correcoes: list[CorrecaoCte],
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) da carta de correção do CT-e.

	`correcoes` é a lista de alterações campo a campo (`infCorrecao`) — não um texto
	livre como na NF-e (ver docstring do módulo). O XSD não impede repetir a mesma
	correção anterior numa carta nova (diferente da regra de negócio da NF-e, onde a
	CC-e nova precisa reunir o histórico inteiro em texto) — aqui cada carta é a lista
	completa de alterações que ela reporta, e é responsabilidade de quem chama decidir
	se isso inclui correções já reportadas antes.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	if not correcoes:
		raise EventoInvalido("A carta de correção precisa de ao menos uma correção", "correcoes")

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_cte(chave, TIPO_EVENTO_CORRECAO_CTE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_CORRECAO_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_CTE,
			"descEvento": "Carta de Correção",
			"infCorrecao": [_montar_inf_correcao(c) for c in correcoes],
			"xCondUso": XCONDUSO_CCE_CTE,
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


def calcular_hash_entrega(chave_acesso: str, imagem_base64: str) -> str:
	"""Calcula `hashEntrega`: SHA-1 de `chave + imagem_base64` (concatenação de texto),
	recodificado em Base64 — confirmado no XSD (`base64Binary` de 20 bytes, o tamanho
	exato de um digest SHA-1).

	`imagem_base64` é a imagem já capturada (assinatura eletrônica, foto) na sua
	própria representação Base64 — este módulo não decide como ela foi capturada nem
	codificada, só concatena a string com a chave e aplica o hash.
	"""
	chave = validar_chave(chave_acesso)
	digest = hashlib.sha1((chave + imagem_base64).encode("utf-8")).digest()

	return base64.b64encode(digest).decode("ascii")


def _validar_coordenada(valor: float, minimo: float, maximo: float, campo: str) -> str:
	if not (minimo <= valor <= maximo):
		raise EventoInvalido(f"{campo} deve estar entre {minimo} e {maximo}, recebido {valor}", campo)

	return f"{valor:.6f}"


def _montar_inf_entrega_nfe(chaves_nfe: list[str]) -> list[dict]:
	"""Monta `infEntrega` (lista de `chNFe`) — mesma forma/mesmas regras em `evCECTe`
	(comprovante de entrega) e `evIECTe` (insucesso na entrega): até 2000 chaves, só
	NF-e (modelo 55), só faz sentido para CT-e de tipo de serviço Normal (regra de
	negócio que este módulo não verifica — quem chama sabe o tipo do CT-e)."""
	if len(chaves_nfe) > 2000:
		raise EventoInvalido(
			f"infEntrega admite no máximo 2000 NF-e, recebidas {len(chaves_nfe)}", "chaves_nfe_entregues"
		)

	infs = []

	for chave_nfe in chaves_nfe:
		decomposta = ler_chave(chave_nfe)

		if decomposta.modelo != "55":
			raise EventoInvalido(
				f"infEntrega só aceita chave de NF-e (modelo 55), recebida chave de modelo "
				f"{decomposta.modelo} ({decomposta.documento})",
				"chaves_nfe_entregues",
			)

		infs.append({"chNFe": decomposta.valor})

	return infs


def montar_evento_comprovante_entrega_cte(
	chave_acesso: str,
	protocolo: str,
	data_entrega: str,
	numero_documento_recebedor: str,
	nome_recebedor: str,
	imagem_base64: str,
	data_hash: str,
	cnpj_autor: str,
	data_evento: str,
	latitude: float | None = None,
	longitude: float | None = None,
	chaves_nfe_entregues: list[str] | None = None,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do comprovante de entrega do CT-e.

	`hashEntrega` é calculado aqui, não recebido pronto — `calcular_hash_entrega` é
	chamada internamente com a mesma `chave_acesso` e `imagem_base64`, para não haver
	risco de o hash informado divergir da chave que o evento realmente referencia
	(mesma disciplina de `nfe.montar_ide` derivar `cDV` da chave, nunca aceitá-lo em
	paralelo).

	`chaves_nfe_entregues` alimenta `infEntrega` — só faz sentido para CT-e com tipo
	de serviço Normal (confirmado na documentação do próprio campo); este módulo não
	verifica isso, é responsabilidade de quem chama saber se o CT-e é desse tipo.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização é obrigatório", "protocolo")

	if not (2 <= len(numero_documento_recebedor) <= 20):
		raise EventoInvalido(
			f"nDoc deve ter de 2 a 20 caracteres, recebido {numero_documento_recebedor!r}",
			"numero_documento_recebedor",
		)

	if not (2 <= len(nome_recebedor) <= 60):
		raise EventoInvalido(
			f"xNome deve ter de 2 a 60 caracteres, recebido {nome_recebedor!r}", "nome_recebedor"
		)

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	det_evento: dict = {
		"@versaoEvento": _VERSAO_LEIAUTE_CTE,
		"descEvento": "Comprovante de Entrega do CT-e",
		"nProt": protocolo_limpo,
		"dhEntrega": data_entrega,
		"nDoc": numero_documento_recebedor,
		"xNome": nome_recebedor,
	}

	if latitude is not None:
		det_evento["latitude"] = _validar_coordenada(latitude, -90.0, 90.0, "latitude")

	if longitude is not None:
		det_evento["longitude"] = _validar_coordenada(longitude, -180.0, 180.0, "longitude")

	det_evento["hashEntrega"] = calcular_hash_entrega(chave, imagem_base64)
	det_evento["dhHashEntrega"] = data_hash

	if chaves_nfe_entregues:
		det_evento["infEntrega"] = _montar_inf_entrega_nfe(chaves_nfe_entregues)

	inf_evento = {
		"@Id": _formatar_id_cte(chave, TIPO_EVENTO_COMPROVANTE_ENTREGA_CTE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_COMPROVANTE_ENTREGA_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": det_evento,
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


@dataclass(frozen=True)
class TomadorEpec:
	"""`toma4` do EPEC — não é `fiscal.cte.TomadorOutros` (ver docstring do módulo):
	`papel` aceita qualquer um dos 5 valores, e não há `xNome`/`enderToma`/`email`."""

	papel: str
	uf: str
	cnpj_cpf: str
	inscricao_estadual: str = ""

	def __post_init__(self):
		if self.papel not in _TOMADORES_EPEC_VALIDOS:
			raise EventoInvalido(
				f"toma do EPEC deve ser um de {sorted(_TOMADORES_EPEC_VALIDOS)}, "
				f"recebido {self.papel!r}",
				"papel",
			)


def montar_tomador_epec(tomador: TomadorEpec) -> dict:
	"""Monta o `toma4` do EPEC — CNPJ/CPF exclusivo, mesma validação de
	`fiscal.cte.montar_toma4`, `IE` opcional."""
	try:
		documento = validar_cpf_cnpj(tomador.cnpj_cpf)
	except ValueError as e:
		raise EventoInvalido(f"CPF/CNPJ do tomador do EPEC inválido: {e}", "cnpj_cpf") from e

	grupo: dict = {"toma": tomador.papel, "UF": tomador.uf}
	grupo["CNPJ" if len(documento) == 14 else "CPF"] = documento

	if tomador.inscricao_estadual.strip():
		grupo["IE"] = tomador.inscricao_estadual.strip()

	return {"toma4": grupo}


def montar_evento_epec_cte(
	chave_acesso: str,
	justificativa: str,
	valor_icms,
	valor_total_prestacao,
	valor_carga,
	tomador: TomadorEpec,
	modal: str,
	uf_inicio: str,
	uf_fim: str,
	data_emissao_cte: str,
	cnpj_autor: str,
	data_evento: str,
	valor_icms_st=None,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do EPEC — a prévia enviada em
	contingência, antes da autorização de verdade do CT-e.

	`tpCTe` não é parâmetro: o XSD só aceita `"0"` (CT-e Normal) neste evento —
	confirmado (`xs:length value="1"` + uma única `xs:enumeration`), diferente do
	`tpCTe` da `ide`, que aceita `0`/`1`/`3`.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	texto_justificativa = (justificativa or "").strip()

	if not (JUSTIFICATIVA_MINIMA_CTE <= len(texto_justificativa) <= JUSTIFICATIVA_MAXIMA_CTE):
		raise EventoInvalido(
			f"A justificativa deve ter de {JUSTIFICATIVA_MINIMA_CTE} a "
			f"{JUSTIFICATIVA_MAXIMA_CTE} caracteres, recebidos {len(texto_justificativa)}",
			"justificativa",
		)

	if modal not in _MODAIS_VALIDOS_EPEC:
		raise EventoInvalido(
			f"modal deve ser um de {sorted(_MODAIS_VALIDOS_EPEC)}, recebido {modal!r}", "modal"
		)

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	det_evento: dict = {
		"@versaoEvento": _VERSAO_LEIAUTE_CTE,
		"descEvento": "EPEC",
		"xJust": texto_justificativa,
		"vICMS": str(valor_icms),
	}

	if valor_icms_st is not None:
		det_evento["vICMSST"] = str(valor_icms_st)

	det_evento["vTPrest"] = str(valor_total_prestacao)
	det_evento["vCarga"] = str(valor_carga)
	det_evento.update(montar_tomador_epec(tomador))
	det_evento["modal"] = modal
	det_evento["UFIni"] = uf_inicio
	det_evento["UFFim"] = uf_fim
	det_evento["tpCTe"] = TIPO_CTE_NORMAL
	det_evento["dhEmi"] = data_emissao_cte

	inf_evento = {
		"@Id": _formatar_id_cte(chave, TIPO_EVENTO_EPEC_CTE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_EPEC_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": det_evento,
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


def _montar_evento_cancelamento_protocolo(
	chave_acesso: str,
	protocolo: str,
	protocolo_evento_cancelado: str,
	campo_protocolo_evento: str,
	desc_evento: str,
	tipo_evento: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int,
	ambiente: str,
) -> dict:
	"""Forma comum a `evCancCECTe` e `evCancIECTe` — cancela um evento de entrega
	(comprovante ou insucesso) informando o protocolo do CT-e e o protocolo do evento
	que está sendo cancelado. Confirmado estruturalmente idêntico entre os dois XSDs
	(só o nome do campo do segundo protocolo e o texto de `descEvento` mudam) — reuso
	real, não especulativo."""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização do CT-e é obrigatório", "protocolo")

	protocolo_evento_limpo = (protocolo_evento_cancelado or "").strip()

	if not protocolo_evento_limpo:
		raise EventoInvalido(
			"O protocolo do evento a cancelar é obrigatório", "protocolo_evento_cancelado"
		)

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_cte(chave, tipo_evento, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": tipo_evento,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_CTE,
			"descEvento": desc_evento,
			"nProt": protocolo_limpo,
			campo_protocolo_evento: protocolo_evento_limpo,
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


def montar_evento_cancelamento_comprovante_entrega_cte(
	chave_acesso: str,
	protocolo: str,
	protocolo_comprovante_entrega: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do cancelamento do comprovante de
	entrega do CT-e.

	Achado real, não suposto pelo nome do arquivo (`evCancCECTe`): "CE" aqui é
	Comprovante de Entrega (o `evCECTe`, `tpEvento` 110180), não Carta de Correção (o
	`evCCeCTe`, que tem sigla própria `CCe`) — confirmado pelo texto do próprio XSD
	("cancelamento do comprovante de entrega eletrônico do CT-e"). `protocolo` é o
	protocolo de autorização do CT-e; `protocolo_comprovante_entrega` é o protocolo do
	evento de comprovante de entrega que está sendo cancelado — dois protocolos
	distintos, não o mesmo valor repetido.
	"""
	return _montar_evento_cancelamento_protocolo(
		chave_acesso=chave_acesso,
		protocolo=protocolo,
		protocolo_evento_cancelado=protocolo_comprovante_entrega,
		campo_protocolo_evento="nProtCE",
		desc_evento="Cancelamento do Comprovante de Entrega do CT-e",
		tipo_evento=TIPO_EVENTO_CANCELAMENTO_COMPROVANTE_ENTREGA_CTE,
		cnpj_autor=cnpj_autor,
		data_evento=data_evento,
		numero_sequencia=numero_sequencia,
		ambiente=ambiente,
	)


def montar_evento_cancelamento_insucesso_entrega_cte(
	chave_acesso: str,
	protocolo: str,
	protocolo_insucesso_entrega: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do cancelamento do insucesso na
	entrega do CT-e (`tpEvento` 110191).

	Confirmado estruturalmente idêntico a `montar_evento_cancelamento_comprovante_
	entrega_cte` (`evCancIECTe_v4.00.xsd`, 36 linhas, lido inteiro) — só o nome do
	campo do segundo protocolo (`nProtIE`, não `nProtCE`) e o texto de `descEvento`
	mudam. `protocolo_insucesso_entrega` é o protocolo do evento de insucesso na
	entrega (`evIECTe`) que está sendo cancelado.
	"""
	return _montar_evento_cancelamento_protocolo(
		chave_acesso=chave_acesso,
		protocolo=protocolo,
		protocolo_evento_cancelado=protocolo_insucesso_entrega,
		campo_protocolo_evento="nProtIE",
		desc_evento="Cancelamento do Insucesso de Entrega do CT-e",
		tipo_evento=TIPO_EVENTO_CANCELAMENTO_INSUCESSO_ENTREGA_CTE,
		cnpj_autor=cnpj_autor,
		data_evento=data_evento,
		numero_sequencia=numero_sequencia,
		ambiente=ambiente,
	)


def montar_evento_insucesso_entrega_cte(
	chave_acesso: str,
	protocolo: str,
	data_tentativa_entrega: str,
	tipo_motivo: str,
	cnpj_autor: str,
	data_evento: str,
	numero_tentativa: int | None = None,
	justificativa_motivo: str | None = None,
	imagem_base64: str | None = None,
	data_hash: str | None = None,
	latitude: float | None = None,
	longitude: float | None = None,
	chaves_nfe_nao_entregues: list[str] | None = None,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do insucesso na entrega do CT-e.

	`justificativa_motivo` é obrigatória quando `tipo_motivo` é
	`MOTIVO_INSUCESSO_OUTROS` ("4") e proibida nos demais motivos — regra de negócio do
	próprio texto do XSD ("informar apenas para tpMotivo = 4"), não decorrente do
	`minOccurs` sozinho (que é opcional para qualquer motivo).

	`hashTentativaEntrega` é opcional aqui (diferente de `hashEntrega` no comprovante de
	entrega, que é obrigatório) — só é calculado quando `imagem_base64` é informada, via
	`calcular_hash_entrega` (mesmo algoritmo, nome de campo diferente).
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	protocolo_limpo = (protocolo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido("O protocolo da autorização é obrigatório", "protocolo")

	if tipo_motivo not in _MOTIVOS_INSUCESSO_VALIDOS:
		raise EventoInvalido(
			f"tpMotivo deve ser um de {sorted(_MOTIVOS_INSUCESSO_VALIDOS)}, recebido {tipo_motivo!r}",
			"tipo_motivo",
		)

	texto_justificativa = (justificativa_motivo or "").strip()

	if tipo_motivo == MOTIVO_INSUCESSO_OUTROS:
		if not (XJUSTMOTIVO_MINIMO_IE_CTE <= len(texto_justificativa) <= XJUSTMOTIVO_MAXIMO_IE_CTE):
			raise EventoInvalido(
				f"xJustMotivo é obrigatório para tpMotivo=4 e deve ter de "
				f"{XJUSTMOTIVO_MINIMO_IE_CTE} a {XJUSTMOTIVO_MAXIMO_IE_CTE} caracteres, "
				f"recebidos {len(texto_justificativa)}",
				"justificativa_motivo",
			)
	elif texto_justificativa:
		raise EventoInvalido(
			"xJustMotivo só é aceito quando tpMotivo=4 (Outros)", "justificativa_motivo"
		)

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	det_evento: dict = {
		"@versaoEvento": _VERSAO_LEIAUTE_CTE,
		"descEvento": "Insucesso na Entrega do CT-e",
		"nProt": protocolo_limpo,
		"dhTentativaEntrega": data_tentativa_entrega,
	}

	if numero_tentativa is not None:
		if not (1 <= numero_tentativa <= 999):
			raise EventoInvalido(
				f"nTentativa deve estar entre 1 e 999, recebido {numero_tentativa}", "numero_tentativa"
			)

		det_evento["nTentativa"] = f"{numero_tentativa:03d}"

	det_evento["tpMotivo"] = tipo_motivo

	if texto_justificativa:
		det_evento["xJustMotivo"] = texto_justificativa

	if latitude is not None:
		det_evento["latitude"] = _validar_coordenada(latitude, -90.0, 90.0, "latitude")

	if longitude is not None:
		det_evento["longitude"] = _validar_coordenada(longitude, -180.0, 180.0, "longitude")

	if imagem_base64 is not None:
		det_evento["hashTentativaEntrega"] = calcular_hash_entrega(chave, imagem_base64)
		det_evento["dhHashTentativaEntrega"] = data_hash

	if chaves_nfe_nao_entregues:
		det_evento["infEntrega"] = _montar_inf_entrega_nfe(chaves_nfe_nao_entregues)

	inf_evento = {
		"@Id": _formatar_id_cte(chave, TIPO_EVENTO_INSUCESSO_ENTREGA_CTE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_INSUCESSO_ENTREGA_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": det_evento,
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


@dataclass(frozen=True)
class EspecieGtv:
	"""Um item de `infEspecie` — tipo de espécie transportada (numerário/cheque/moeda/
	outros) e, opcionalmente, o valor transportado naquela espécie."""

	tipo_especie: str
	valor_especie: str | None = None

	def __post_init__(self):
		if self.tipo_especie not in _ESPECIES_GTV_VALIDAS:
			raise EventoInvalido(
				f"tpEspecie deve ser um de {sorted(_ESPECIES_GTV_VALIDAS)}, "
				f"recebido {self.tipo_especie!r}",
				"tipo_especie",
			)


@dataclass(frozen=True)
class ParteGtv:
	"""`rem`/`dest` da GTV compartilham exatamente a mesma forma no XSD — um único tipo,
	não duas classes idênticas com nomes diferentes."""

	cnpj_cpf: str
	uf: str
	nome: str
	inscricao_estadual: str = ""


@dataclass(frozen=True)
class InfGtv:
	"""Um item de `infGTV` — uma Guia de Transporte de Valores transportada pelo CT-e."""

	numero_documento: str
	identificador: str
	data_emissao: str
	digito_verificador: str
	quantidade_carga: str
	especies: list[EspecieGtv]
	remetente: ParteGtv
	destinatario: ParteGtv
	serie: str | None = None
	subserie: str | None = None
	placa: str | None = None
	uf_veiculo: str | None = None
	rntrc: str | None = None

	def __post_init__(self):
		if not (1 <= len(self.numero_documento) <= 20):
			raise EventoInvalido(
				f"nDoc deve ter de 1 a 20 caracteres, recebido {self.numero_documento!r}",
				"numero_documento",
			)

		if not (1 <= len(self.identificador) <= 20):
			raise EventoInvalido(
				f"id deve ter de 1 a 20 caracteres, recebido {self.identificador!r}", "identificador"
			)

		if len(self.digito_verificador) != 1:
			raise EventoInvalido(
				f"nDV deve ter exatamente 1 caractere, recebido {self.digito_verificador!r}",
				"digito_verificador",
			)

		if not self.especies:
			raise EventoInvalido("infEspecie precisa de ao menos uma espécie", "especies")

		if self.serie is not None and not (1 <= len(self.serie) <= 3):
			raise EventoInvalido(f"serie deve ter de 1 a 3 caracteres, recebido {self.serie!r}", "serie")

		if self.subserie is not None and not (1 <= len(self.subserie) <= 3):
			raise EventoInvalido(
				f"subserie deve ter de 1 a 3 caracteres, recebido {self.subserie!r}", "subserie"
			)


def montar_parte_gtv(parte: ParteGtv) -> dict:
	"""Monta `rem`/`dest` da GTV — CNPJ/CPF exclusivo, ordem exata do `xs:sequence`
	(CNPJ|CPF, IE opcional, UF, xNome).

	Fora de escopo, documentado: `TCnpjOpc` aceita `"00000000000000"` para
	remetente/destinatário não estabelecido no Brasil — `validar_cnpj` deste projeto
	rejeita ativamente CNPJ com todos os dígitos iguais, por desenho. Remetente/
	destinatário estrangeiro não é suportado por este módulo.
	"""
	try:
		documento = validar_cpf_cnpj(parte.cnpj_cpf)
	except ValueError as e:
		raise EventoInvalido(f"CPF/CNPJ da GTV inválido: {e}", "cnpj_cpf") from e

	if not (2 <= len(parte.nome) <= 60):
		raise EventoInvalido(f"xNome deve ter de 2 a 60 caracteres, recebido {parte.nome!r}", "nome")

	grupo: dict = {}
	grupo["CNPJ" if len(documento) == 14 else "CPF"] = documento

	if parte.inscricao_estadual.strip():
		grupo["IE"] = parte.inscricao_estadual.strip()

	grupo["UF"] = parte.uf
	grupo["xNome"] = parte.nome

	return grupo


def _montar_inf_gtv(inf: InfGtv) -> dict:
	grupo: dict = {"nDoc": inf.numero_documento, "id": inf.identificador}

	if inf.serie is not None:
		grupo["serie"] = inf.serie

	if inf.subserie is not None:
		grupo["subserie"] = inf.subserie

	grupo["dEmi"] = inf.data_emissao
	grupo["nDV"] = inf.digito_verificador
	grupo["qCarga"] = str(inf.quantidade_carga)

	infs_especie = []

	for especie in inf.especies:
		item: dict = {"tpEspecie": especie.tipo_especie}

		if especie.valor_especie is not None:
			item["vEspecie"] = str(especie.valor_especie)

		infs_especie.append(item)

	grupo["infEspecie"] = infs_especie
	grupo["rem"] = montar_parte_gtv(inf.remetente)
	grupo["dest"] = montar_parte_gtv(inf.destinatario)

	if inf.placa is not None:
		placa_limpa = inf.placa.strip().upper()

		if not placa_limpa:
			raise EventoInvalido("placa não pode ser vazia quando informada", "placa")

		grupo["placa"] = placa_limpa

	if inf.uf_veiculo is not None:
		grupo["UF"] = inf.uf_veiculo

	if inf.rntrc is not None:
		try:
			grupo["RNTRC"] = validar_rntrc(inf.rntrc)
		except RntrcInvalido as e:
			raise EventoInvalido(str(e), "rntrc") from e

	return grupo


def montar_evento_gtv_cte(
	chave_acesso: str,
	guias: list[InfGtv],
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) das informações da GTV do CT-e.

	`guias` é a lista de `infGTV` — um único evento pode reportar várias Guias de
	Transporte de Valores transportadas pelo mesmo CT-e (`maxOccurs="unbounded"` no
	XSD, sem limite declarado).
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	if not guias:
		raise EventoInvalido("O evento de GTV precisa de ao menos uma guia", "guias")

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_cte(chave, TIPO_EVENTO_GTV_CTE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_GTV_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_CTE,
			"descEvento": DESC_EVENTO_GTV,
			"infGTV": [_montar_inf_gtv(g) for g in guias],
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


def montar_evento_prestacao_desacordo_cte(
	chave_acesso: str,
	observacao: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) da prestação do serviço em
	desacordo (`tpEvento` 610110) — o tomador reporta desacordo com a prestação.

	`indDesacordoOper` sempre grava `INDICADOR_DESACORDO_OPERACAO` ("1"), o único
	valor que o XSD permite — não é parâmetro da função, mesma disciplina de `tpCTe`
	no EPEC (sempre fixado, não deixado para o chamador acertar por conta própria).
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	texto_observacao = (observacao or "").strip()

	if not (XOBS_MINIMO_DESACORDO_CTE <= len(texto_observacao) <= XOBS_MAXIMO_DESACORDO_CTE):
		raise EventoInvalido(
			f"xObs deve ter de {XOBS_MINIMO_DESACORDO_CTE} a {XOBS_MAXIMO_DESACORDO_CTE} "
			f"caracteres, recebidos {len(texto_observacao)}",
			"observacao",
		)

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_cte(chave, TIPO_EVENTO_PRESTACAO_DESACORDO_CTE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_PRESTACAO_DESACORDO_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_CTE,
			"descEvento": "Prestação do Serviço em Desacordo",
			"indDesacordoOper": INDICADOR_DESACORDO_OPERACAO,
			"xObs": texto_observacao,
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


def montar_evento_cancelamento_prestacao_desacordo_cte(
	chave_acesso: str,
	protocolo_prestacao_desacordo: str,
	cnpj_autor: str,
	data_evento: str,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do cancelamento da prestação em
	desacordo (`tpEvento` 610111).

	Achado real: diferente de `evCancCECTe`/`evCancIECTe` (que carregam `nProt` do
	CT-e **e** o protocolo do evento cancelado), este cancelamento carrega **só**
	`nProtEvPrestDes` — sem `nProt` do CT-e. Por isso não reaproveita
	`_montar_evento_cancelamento_protocolo` (que exige os dois protocolos); é uma
	função própria.
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	protocolo_limpo = (protocolo_prestacao_desacordo or "").strip()

	if not protocolo_limpo:
		raise EventoInvalido(
			"O protocolo do evento de prestação em desacordo a cancelar é obrigatório",
			"protocolo_prestacao_desacordo",
		)

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	inf_evento = {
		"@Id": _formatar_id_cte(
			chave, TIPO_EVENTO_CANCELAMENTO_PRESTACAO_DESACORDO_CTE, numero_sequencia
		),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_CANCELAMENTO_PRESTACAO_DESACORDO_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": {
			"@versaoEvento": _VERSAO_LEIAUTE_CTE,
			"descEvento": "Cancelamento Prestação do Serviço em Desacordo",
			"nProtEvPrestDes": protocolo_limpo,
		},
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


def montar_evento_registro_multimodal_cte(
	chave_acesso: str,
	registro: str,
	cnpj_autor: str,
	data_evento: str,
	numero_documento: str | None = None,
	numero_sequencia: int = 1,
	ambiente: str = "2",
) -> dict:
	"""Monta o elemento `evento` (grupo `TEvento`) do registro multimodal (`tpEvento`
	110160) — o último dos onze eventos do CT-e v4.00.

	`numero_documento` (`nDoc`) é opcional e, apesar do comprimento (1-44) coincidir
	com o de uma chave de acesso, **não é validado como uma** — o XSD tipa como
	`[0-9]{1,44}` solto, não `TChDFe`. Este módulo só confere que é uma string
	numérica de até 44 dígitos, fiel ao que o schema realmente pede (achado real, ver
	docstring do módulo).
	"""
	chave = validar_chave(chave_acesso)
	lida = ler_chave(chave)

	texto_registro = (registro or "").strip()

	if not (
		XREGISTRO_MINIMO_MULTIMODAL_CTE <= len(texto_registro) <= XREGISTRO_MAXIMO_MULTIMODAL_CTE
	):
		raise EventoInvalido(
			f"xRegistro deve ter de {XREGISTRO_MINIMO_MULTIMODAL_CTE} a "
			f"{XREGISTRO_MAXIMO_MULTIMODAL_CTE} caracteres, recebidos {len(texto_registro)}",
			"registro",
		)

	if not (1 <= numero_sequencia <= 20):
		raise EventoInvalido(
			f"nSeqEvento deve estar entre 1 e 20, recebido {numero_sequencia}", "numero_sequencia"
		)

	try:
		cnpj = validar_cnpj(cnpj_autor)
	except ValueError as e:
		raise EventoInvalido(f"CNPJ do autor do evento inválido: {e}", "cnpj_autor") from e

	det_evento: dict = {
		"@versaoEvento": _VERSAO_LEIAUTE_CTE,
		"descEvento": DESC_EVENTO_REGISTRO_MULTIMODAL,
		"xRegistro": texto_registro,
	}

	if numero_documento is not None:
		if not (1 <= len(numero_documento) <= 44 and numero_documento.isdigit()):
			raise EventoInvalido(
				f"nDoc deve ter de 1 a 44 dígitos, recebido {numero_documento!r}", "numero_documento"
			)

		det_evento["nDoc"] = numero_documento

	inf_evento = {
		"@Id": _formatar_id_cte(chave, TIPO_EVENTO_REGISTRO_MULTIMODAL_CTE, numero_sequencia),
		"cOrgao": lida.uf,
		"tpAmb": ambiente,
		"CNPJ": cnpj,
		"chCTe": chave,
		"dhEvento": data_evento,
		"tpEvento": TIPO_EVENTO_REGISTRO_MULTIMODAL_CTE,
		"nSeqEvento": str(numero_sequencia),
		"detEvento": det_evento,
	}

	return {"evento": {"@xmlns": NAMESPACE_CTE, "@versao": _VERSAO_LEIAUTE_CTE, "infEvento": inf_evento}}


def montar_env_evento_cte(eventos: list[dict], id_lote: str) -> dict:
	"""Monta `envEvento` do CT-e — mesma disciplina de `evento.montar_env_evento`
	(até 20 eventos por lote), com o namespace do CT-e."""
	if not eventos:
		raise EventoInvalido("O lote de eventos precisa de ao menos um evento", "eventos")

	if len(eventos) > 20:
		raise EventoInvalido(
			f"Um lote de eventos admite no máximo 20, recebidos {len(eventos)}", "eventos"
		)

	if not (id_lote or "").strip():
		raise EventoInvalido("idLote é obrigatório", "id_lote")

	return {
		"envEvento": {
			"@xmlns": NAMESPACE_CTE,
			"@versao": _VERSAO_LEIAUTE_CTE,
			"idLote": id_lote.strip(),
			"evento": [e["evento"] for e in eventos],
		}
	}
