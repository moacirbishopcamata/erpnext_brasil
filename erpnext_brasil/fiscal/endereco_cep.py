# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Consulta de CEP e de logradouro no ViaCEP — a parte que não depende de rede nem de Frappe.

Por que existe
--------------
A NF-e, o CT-e e o MDF-e **recusam** um endereço sem logradouro, número, bairro, código IBGE do
município, município, UF e CEP (`integracao/nfe_documento._grupo_endereco`), e o SPED e a ECF leem as
mesmas colunas. Hoje tudo isso é digitado à mão. O ViaCEP (https://viacep.com.br) devolve quase todos a
partir do CEP — inclusive o **código IBGE de 7 dígitos**, o dado mais fácil de errar na digitação.

Este módulo só sabe *montar a pergunta*, *ler a resposta* e *decidir o que cabe no cadastro*. Quem faz a
chamada HTTP é `integracao/consulta_cep.py`, e por isso aqui não há `requests`, nem cache, nem Frappe.

O que a resposta real do serviço ensinou (colhida em 2026-10-10, não escrita de memória)
-----------------------------------------------------------------------------------------
- **CEP inexistente volta HTTP 200** com `{"erro": "true"}` — o valor é o *texto* `"true"`, e a página
  de documentação fala em booleano. Aceitam-se os dois. É resultado normal de consulta (`None`), não falha.
- **CEP malformado volta HTTP 400 com uma página HTML**, não JSON. A documentação manda validar antes de
  consultar, e é o que `normalizar_cep` e `url_por_logradouro` fazem: o que o serviço recusaria nem sai.
- **`complemento` não é o complemento do cliente.** Para `01001-000` vem `"lado ímpar"`, uma nota sobre a
  faixa de numeração do CEP. Gravá-lo em `address_line2` mandaria "lado ímpar" para o `xCpl` da nota.
  Por isso **nunca** preenche o cadastro.
- **`ibge` pode vir vazio** em alguns CEPs; só um código de exatamente 7 dígitos é aceito.
- **Busca por logradouro** exige UF, cidade e logradouro (os dois últimos com ao menos 3 caracteres) e
  devolve no máximo 50 resultados.
- **`+` e `%20` não são iguais.** No logradouro, `+` busca por palavras (`Domingos+José` achou 3 ruas) e `%20`
  exige a frase (2 ruas); na cidade, `+` devolve uma página de erro. Daí `%20` na cidade e `+` no logradouro,
  que é a forma do exemplo da própria documentação.

Regra de ouro: sugestão preenche lacuna, nunca corrige
--------------------------------------------------------
`lacunas` só propõe campos que estão **vazios** no cadastro; o valor salvo manda sobre o cadastro externo
(que pode estar defasado ou ser mais genérico que o endereço real). O que o cadastro externo contradiz
(`divergencias`: UF, município e código IBGE) é **avisado**, nunca trocado em silêncio. Logradouro e bairro
não entram na comparação: "Rua X" e "R. X" são o mesmo lugar, e comparar texto de rua só geraria alarme falso.

Fonte e limites
---------------
Documentação e comportamento do próprio serviço (a base informava 1.608.385 CEPs em 2026-10-10; fontes
IBGE, GIA/ICMS de SP, Anatel e SIAFI). O serviço é gratuito e **não publica SLA nem limite de requisições**,
e avisa que "uso massivo para validação de bases de dados locais" pode levar ao bloqueio por tempo
indeterminado — por isso a camada de integração consulta sob demanda, faz cache e degrada sem rede.

Funções puras: nenhuma dependência do Frappe.
"""

import json
import unicodedata
from dataclasses import dataclass
from urllib.parse import quote

from erpnext_brasil.fiscal.ufs import SIGLAS, resolver_uf

__all__ = [
	"CAMPOS_DO_ENDERECO",
	"LIMITE_DE_RESULTADOS",
	"URL_BASE",
	"CepInvalido",
	"Divergencia",
	"EnderecoCep",
	"RespostaCepInvalida",
	"campos_do_endereco",
	"divergencias",
	"formatar_cep",
	"interpretar_busca",
	"interpretar_cep",
	"lacunas",
	"normalizar_cep",
	"url_por_cep",
	"url_por_logradouro",
]

URL_BASE = "https://viacep.com.br/ws"
LIMITE_DE_RESULTADOS = 50
"""O limite que o próprio serviço declara por consulta de logradouro."""

_MINIMO_DA_BUSCA = 3
_MAXIMO_DA_BUSCA = 100

CAMPOS_DO_ENDERECO = (
	"pincode",
	"address_line1",
	"br_bairro",
	"city",
	"state",
	"br_codigo_municipio_ibge",
)
"""Os campos do `Address` que a consulta sabe preencher — os mesmos que `_grupo_endereco` exige.

⚠️ `address_line2` e `br_numero_endereco` ficam de fora **de propósito**: o número e o complemento são do
cliente, e o `complemento` do ViaCEP não é isso (ver a docstring do módulo)."""


class CepInvalido(ValueError):
	"""A consulta que o serviço recusaria (HTTP 400) — barrada antes de sair."""


class RespostaCepInvalida(ValueError):
	"""O que voltou não é uma resposta do ViaCEP (página de erro, JSON de outra forma, lixo)."""


@dataclass(frozen=True)
class EnderecoCep:
	"""Um endereço como o serviço o devolveu, já aparado."""

	cep: str
	"""No formato `01001-000`, o que o usuário vê e o que a validação do app já aceita."""
	logradouro: str
	bairro: str
	cidade: str
	uf: str
	codigo_municipio: str
	"""Os 7 dígitos do IBGE, ou vazio quando a resposta não trouxe um código utilizável."""
	estado: str = ""
	ddd: str = ""


@dataclass(frozen=True)
class Divergencia:
	"""O cadastro diz uma coisa e o ViaCEP outra. Quem decide é o usuário."""

	campo: str
	atual: str
	sugerido: str


def normalizar_cep(texto) -> str:
	"""Os 8 dígitos do CEP, sem máscara — ou `CepInvalido`."""
	digitos = "".join(ch for ch in str(texto or "") if ch.isdigit())
	sobra = "".join(ch for ch in str(texto or "") if not ch.isdigit() and ch not in " .-")

	if len(digitos) != 8 or sobra or set(digitos) == {"0"}:
		raise CepInvalido(f"CEP deve ter 8 dígitos, recebido {texto!r}")

	return digitos


def formatar_cep(digitos: str) -> str:
	return f"{digitos[:5]}-{digitos[5:]}"


def url_por_cep(cep) -> str:
	return f"{URL_BASE}/{normalizar_cep(cep)}/json/"


def _trecho(texto, rotulo: str, espaco_como_mais: bool = False) -> str:
	"""Um pedaço de caminho de URL vindo do usuário: aparado, medido e codificado por inteiro.

	`safe=""` codifica também `/`, `?` e `#`, para que o texto digitado não consiga abrir o caminho.

	O espaço depende do segmento, e foi conferido ao vivo (2026-10-10): no **logradouro**, `+` faz o
	serviço buscar por palavras (`Domingos+José` achou 3 ruas, uma delas "José Domingos Varella") e `%20`
	exige a frase exata (2 ruas); na **cidade**, `+` devolve uma página de erro em vez de JSON. Um `+` que o
	usuário digitou é dado e vira `%2B`; só o espaço vira `+`."""
	limpo = " ".join(str(texto or "").split())

	if len(limpo) < _MINIMO_DA_BUSCA:
		raise CepInvalido(f"{rotulo} precisa de ao menos {_MINIMO_DA_BUSCA} caracteres, recebido {texto!r}")

	if len(limpo) > _MAXIMO_DA_BUSCA:
		raise CepInvalido(f"{rotulo} passa de {_MAXIMO_DA_BUSCA} caracteres")

	codificado = quote(limpo, safe="")

	return codificado.replace("%20", "+") if espaco_como_mais else codificado


def url_por_logradouro(uf, cidade, logradouro) -> str:
	sigla = str(uf or "").strip().upper()

	if sigla not in SIGLAS:
		raise CepInvalido(f"UF desconhecida: {uf!r}")

	cidade_na_url = _trecho(cidade, "Cidade")
	logradouro_na_url = _trecho(logradouro, "Logradouro", espaco_como_mais=True)

	return f"{URL_BASE}/{sigla}/{cidade_na_url}/{logradouro_na_url}/json/"


def _carregar(corpo):
	if isinstance(corpo, bytes | bytearray):
		corpo = bytes(corpo).decode("utf-8", errors="replace")

	if not isinstance(corpo, str):
		return corpo

	try:
		return json.loads(corpo)
	except ValueError as e:
		raise RespostaCepInvalida("A resposta não é JSON — o serviço devolveu uma página de erro?") from e


def _com_erro(dados) -> bool:
	"""`{"erro": "true"}` (o que o serviço manda) ou `{"erro": true}` (o que a página descreve)."""
	return isinstance(dados, dict) and str(dados.get("erro", "")).strip().lower() == "true"


def _texto(dados: dict, chave: str) -> str:
	return str(dados.get(chave) or "").strip()


def _endereco(dados) -> EnderecoCep:
	if not isinstance(dados, dict) or not _texto(dados, "cep"):
		raise RespostaCepInvalida("Resposta sem CEP — não é um endereço do ViaCEP")

	digitos = "".join(ch for ch in _texto(dados, "cep") if ch.isdigit())

	if len(digitos) != 8:
		raise RespostaCepInvalida(f"CEP da resposta malformado: {dados.get('cep')!r}")

	ibge = _texto(dados, "ibge")

	return EnderecoCep(
		cep=formatar_cep(digitos),
		logradouro=_texto(dados, "logradouro"),
		bairro=_texto(dados, "bairro"),
		cidade=_texto(dados, "localidade"),
		uf=_texto(dados, "uf").upper(),
		codigo_municipio=ibge if len(ibge) == 7 and ibge.isdigit() else "",
		estado=_texto(dados, "estado"),
		ddd=_texto(dados, "ddd"),
	)


def interpretar_cep(corpo) -> EnderecoCep | None:
	"""O endereço da consulta por CEP, ou `None` quando o CEP não existe na base."""
	dados = _carregar(corpo)

	if _com_erro(dados):
		return None

	if isinstance(dados, list):
		raise RespostaCepInvalida("Consulta por CEP devolveu uma lista — esperava um endereço só")

	return _endereco(dados)


def interpretar_busca(corpo) -> list[EnderecoCep]:
	"""Os endereços da busca por logradouro (vazia quando nada casa), no máximo `LIMITE_DE_RESULTADOS`."""
	dados = _carregar(corpo)

	if _com_erro(dados):
		return []

	if not isinstance(dados, list):
		raise RespostaCepInvalida("Busca por logradouro devolveu algo que não é uma lista")

	return [_endereco(item) for item in dados[:LIMITE_DE_RESULTADOS]]


def campos_do_endereco(endereco: EnderecoCep) -> dict[str, str]:
	"""O endereço nos nomes de campo do `Address`, **sem** os valores vazios."""
	todos = {
		"pincode": endereco.cep,
		"address_line1": endereco.logradouro,
		"br_bairro": endereco.bairro,
		"city": endereco.cidade,
		"state": endereco.uf,
		"br_codigo_municipio_ibge": endereco.codigo_municipio,
	}

	return {campo: valor for campo, valor in todos.items() if valor}


def _vazio(valor) -> bool:
	return not str(valor or "").strip()


def lacunas(atual: dict, endereco: EnderecoCep) -> dict[str, str]:
	"""Só o que o cadastro **não tem**. Valor já informado nunca entra aqui."""
	return {campo: valor for campo, valor in campos_do_endereco(endereco).items() if _vazio(atual.get(campo))}


def _sem_acento(texto: str) -> str:
	base = unicodedata.normalize("NFKD", str(texto or ""))

	return "".join(ch for ch in base if not unicodedata.combining(ch)).casefold().strip()


def divergencias(atual: dict, endereco: EnderecoCep) -> list[Divergencia]:
	"""O que o cadastro preenchido contradiz no ViaCEP: UF, município e código IBGE.

	Campo vazio não é divergência (é lacuna). "São Paulo" e "SP" são o mesmo estado, e a grafia de
	acento e caixa do município não conta — `state` e `city` são texto livre no Frappe.
	"""
	achadas = []

	uf = atual.get("state")
	if not _vazio(uf) and endereco.uf and (resolver_uf(uf) or str(uf).strip().upper()) != endereco.uf:
		achadas.append(Divergencia("state", str(uf).strip(), endereco.uf))

	cidade = atual.get("city")
	if not _vazio(cidade) and endereco.cidade and _sem_acento(cidade) != _sem_acento(endereco.cidade):
		achadas.append(Divergencia("city", str(cidade).strip(), endereco.cidade))

	codigo = "".join(ch for ch in str(atual.get("br_codigo_municipio_ibge") or "") if ch.isdigit())
	if codigo and endereco.codigo_municipio and codigo != endereco.codigo_municipio:
		achadas.append(Divergencia("br_codigo_municipio_ibge", codigo, endereco.codigo_municipio))

	return achadas
