# Copyright (c) 2026, ERPNext Brasil contributors
# License: MIT. See license.txt

"""Cherry — a interface. Só tkinter (stdlib): nenhuma dependência nova na máquina de quem
desenvolve, mesma disciplina que manteve `openpyxl` e `signxml` fora do app.

Toda escrita passa por `config.py`; esta camada só coleta o que o usuário digitou, chama a
função certa e mostra o resultado.

As decisões de UX seguem o *UX checklist for desktop applications* da Microsoft e as
heurísticas de Nielsen (ver `docs/cherry.md`, com as fontes):

- **uma instrução principal por aba**, imperativa, e abas com nome específico;
- **sucesso sem modal** — barra de estado mais uma marca "✓" que some sozinha; caixa de
  diálogo só para problema, e sem vocabulário que culpe ("não foi possível", nunca "erro");
- **confirmação só com consequência**: trocar o banco de um bench que já tem sites;
- **teclado de verdade**: foco inicial no primeiro campo, Enter aciona a ação da aba,
  teclas de acesso nos botões;
- **padrões seguros**: senha oculta, `developer_mode` desligado, sugestão nunca sobrescreve
  valor digitado.
"""

from __future__ import annotations

import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from scripts.cherry import __version__
from scripts.cherry import config as cfg

PREFERENCIAS = Path.home() / ".cherry.json"
"""Só caminho do bench, distro e geometria da janela — nunca senha. A senha vai para o
`common_site_config.json` quando o usuário manda, e para lugar nenhum antes disso."""

LIMPEZA_DA_AREA_DE_TRANSFERENCIA_MS = 60_000
"""Depois de quanto tempo o comando `bench new-site` copiado sai da área de transferência. O comando
leva a senha de root do banco; deixá-lo lá indefinidamente expõe o segredo a qualquer programa que
leia a área de transferência (CH-04 da revisão do Cherry)."""

DURACAO_DA_MARCA_MS = 2500
"""Quanto tempo o "✓ gravado" fica visível. Curto o bastante para não virar ruído, longo o
bastante para ser lido — a confirmação visual que o projeto exige de toda ação."""


class Cherry(tk.Tk):
	def __init__(self):
		_nitidez_no_windows()
		super().__init__()
		self.title(f"Cherry {__version__} — configuração do bench")
		self.minsize(760, 560)
		self.bench: cfg.Bench | None = None
		self._marca_agendada: str | None = None
		self._limpeza_agendada: str | None = None

		_tema_nativo(self)
		self._montar_barra_de_estado()
		self._montar_abas()
		self._carregar_preferencias()
		self._centralizar()
		self.campo_caminho_linux.focus_set()

	# ------------------------------------------------------------------ estrutura

	def _montar_barra_de_estado(self):
		barra = ttk.Frame(self, relief="sunken", padding=(6, 3))
		barra.pack(side="bottom", fill="x")
		self.estado = tk.StringVar(value="Escolha o bench na primeira aba para começar")
		ttk.Label(barra, textvariable=self.estado, anchor="w").pack(side="left", fill="x", expand=True)
		self.marca = tk.StringVar(value="")
		ttk.Label(barra, textvariable=self.marca, foreground="#1a7f37", width=14, anchor="e").pack(
			side="right"
		)

	def _montar_abas(self):
		self.abas = ttk.Notebook(self)
		self.abas.pack(fill="both", expand=True, padx=10, pady=(10, 4))
		self._aba_bench()
		self._aba_banco()
		self._aba_portas()
		self._aba_sites()
		self._aba_apps()
		self.abas.enable_traversal()

	def _instrucao(self, aba: ttk.Frame, texto: str, linha: int = 0, colunas: int = 3):
		"""A instrução principal da aba: o objetivo do usuário, no imperativo, sem ponto final."""
		ttk.Label(aba, text=texto, font=("", 11, "bold")).grid(
			row=linha, column=0, columnspan=colunas, sticky="w", pady=(0, 10)
		)

	def _informar(self, texto: str):
		self.estado.set(texto)

	def _confirmar_visualmente(self, texto: str = "✓ gravado"):
		"""Feedback de sucesso sem interromper: a marca aparece e some sozinha."""
		self.marca.set(texto)

		if self._marca_agendada:
			self.after_cancel(self._marca_agendada)

		self._marca_agendada = self.after(DURACAO_DA_MARCA_MS, lambda: self.marca.set(""))

	def _problema(self, erro: Exception | str):
		"""Um problema interrompe — é o único caso de caixa de diálogo modal aqui."""
		texto = str(erro)
		self.estado.set(f"Não foi possível: {texto}")
		messagebox.showerror("Cherry — não foi possível", texto, parent=self)

	def _centralizar(self):
		self.update_idletasks()
		largura, altura = max(self.winfo_width(), 760), max(self.winfo_height(), 560)
		x = (self.winfo_screenwidth() - largura) // 2
		y = (self.winfo_screenheight() - altura) // 3
		self.geometry(f"{largura}x{altura}+{x}+{y}")

	# ------------------------------------------------------------------ aba: bench

	def _aba_bench(self):
		aba = ttk.Frame(self.abas, padding=14)
		self.abas.add(aba, text="Bench", underline=0)
		self._instrucao(aba, "Escolha o bench que o Cherry vai configurar")

		self.distro = tk.StringVar(value="Ubuntu")
		self.caminho_linux = tk.StringVar(value="/home/<usuário>/frappe-bench-16")
		self.raiz_local = tk.StringVar()

		ttk.Label(aba, text="No WSL — os arquivos são editados por \\\\wsl.localhost").grid(
			row=1, column=0, columnspan=3, sticky="w"
		)
		ttk.Label(aba, text="Distro").grid(row=2, column=0, sticky="w", pady=3)
		ttk.Entry(aba, textvariable=self.distro, width=20).grid(row=2, column=1, sticky="w", pady=3)
		ttk.Label(aba, text="Caminho Linux do bench").grid(row=3, column=0, sticky="w", pady=3)
		self.campo_caminho_linux = ttk.Entry(aba, textvariable=self.caminho_linux, width=52)
		self.campo_caminho_linux.grid(row=3, column=1, sticky="we", pady=3)
		self.campo_caminho_linux.bind("<Return>", lambda _: self._usar_bench_wsl())
		ttk.Button(aba, text="Usar este bench", underline=0, command=self._usar_bench_wsl).grid(
			row=3, column=2, padx=(8, 0)
		)
		self.bind_all("<Alt-u>", lambda _: self._usar_bench_wsl())

		ttk.Separator(aba).grid(row=4, column=0, columnspan=3, sticky="we", pady=12)

		ttk.Label(aba, text="Neste computador — a pasta que contém sites/").grid(
			row=5, column=0, columnspan=3, sticky="w"
		)
		ttk.Label(aba, text="Pasta").grid(row=6, column=0, sticky="w", pady=3)
		ttk.Entry(aba, textvariable=self.raiz_local, width=52).grid(row=6, column=1, sticky="we", pady=3)
		ttk.Button(aba, text="Escolher pasta…", command=self._escolher_pasta).grid(
			row=6, column=2, padx=(8, 0)
		)

		self.resumo_bench = tk.StringVar(value="Nenhum bench carregado")
		ttk.Label(aba, textvariable=self.resumo_bench, justify="left", wraplength=680).grid(
			row=7, column=0, columnspan=3, sticky="w", pady=(14, 0)
		)
		aba.columnconfigure(1, weight=1)

	def _usar_bench_wsl(self):
		try:
			raiz = cfg.caminho_wsl(self.distro.get(), self.caminho_linux.get())
			self._carregar_bench(cfg.Bench(raiz, self.distro.get().strip(), self.caminho_linux.get().strip()))
		except cfg.CherryInvalido as erro:
			self._problema(erro)

	def _escolher_pasta(self):
		pasta = filedialog.askdirectory(title="Pasta do bench (a que contém sites/)", parent=self)

		if pasta:
			self.raiz_local.set(pasta)
			self._carregar_bench(cfg.Bench(Path(pasta)))

	def _carregar_bench(self, bench: cfg.Bench):
		if not bench.existe():
			self._problema(f"não há uma pasta sites/ em {bench.raiz}")
			return

		try:
			comum = cfg.ler_json(bench.common_config)
		except (cfg.CherryInvalido, json.JSONDecodeError) as erro:
			self._problema(f"common_site_config.json não pôde ser lido — {erro}")
			return

		self.bench = bench
		sites = bench.nomes_de_sites()
		apps = cfg.ler_apps_txt(bench.apps_txt)
		self.resumo_bench.set(
			f"Bench: {bench.raiz}\nSites: {', '.join(sites) or '(nenhum)'}\n"
			f"Apps: {', '.join(apps) or '(apps.txt vazio)'}\n"
			f"Banco padrão do bench: {comum.get('db_type', 'mariadb (implícito)')} em "
			f"{comum.get('db_host', 'localhost')}:{comum.get('db_port', '(padrão)')}"
		)
		self._preencher_banco(comum)
		self._preencher_portas(comum)
		self._preencher_sites(sites, comum.get("default_site", ""))
		self._preencher_apps(apps)
		self._salvar_preferencias()
		self._informar(f"Bench carregado: {bench.raiz}")
		self._confirmar_visualmente("✓ carregado")

	# ------------------------------------------------------------------ aba: banco

	def _aba_banco(self):
		aba = ttk.Frame(self.abas, padding=14)
		self.abas.add(aba, text="Banco de dados", underline=0)
		self._instrucao(aba, "Informe o servidor de banco de dados que os sites deste bench vão usar")

		self.tipo = tk.StringVar(value=cfg.MARIADB)
		self.host = tk.StringVar(value="127.0.0.1")
		self.porta = tk.StringVar(value=str(cfg.PORTA_PADRAO[cfg.MARIADB]))
		self.usuario_root = tk.StringVar(value="root")
		self.senha_root = tk.StringVar()
		self.mostrar_senha = tk.BooleanVar(value=False)
		self.site_novo = tk.StringVar(value="novo.localhost")
		self.senha_admin = tk.StringVar()
		self.comando_visivel = tk.BooleanVar(value=False)

		ttk.Label(aba, text="Servidor").grid(row=1, column=0, sticky="w", pady=3)
		linha = ttk.Frame(aba)
		linha.grid(row=1, column=1, sticky="w")

		for tipo in cfg.TIPOS:
			ttk.Radiobutton(
				linha, text=cfg.ROTULO[tipo], value=tipo, variable=self.tipo, command=self._ao_trocar_tipo
			).pack(side="left", padx=(0, 14))

		campos = [("Host", self.host), ("Porta", self.porta), ("Usuário administrador", self.usuario_root)]

		for i, (rotulo, variavel) in enumerate(campos, start=2):
			ttk.Label(aba, text=rotulo).grid(row=i, column=0, sticky="w", pady=3)
			campo = ttk.Entry(aba, textvariable=variavel, width=40)
			campo.grid(row=i, column=1, sticky="we", pady=3)
			campo.bind("<Return>", lambda _: self._testar_conexao())

		ttk.Label(aba, text="Senha do administrador").grid(row=5, column=0, sticky="w", pady=3)
		self.campo_senha = ttk.Entry(aba, textvariable=self.senha_root, width=40, show="•")
		self.campo_senha.grid(row=5, column=1, sticky="we", pady=3)
		self.campo_senha.bind("<Return>", lambda _: self._testar_conexao())
		ttk.Checkbutton(
			aba, text="Mostrar senha", variable=self.mostrar_senha, command=self._alternar_senha
		).grid(row=5, column=2, padx=(8, 0))

		botoes = ttk.Frame(aba)
		botoes.grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 4))
		ttk.Button(botoes, text="Testar conexão", underline=0, command=self._testar_conexao).pack(side="left")
		ttk.Button(botoes, text="Gravar no bench", underline=0, command=self._gravar_banco).pack(
			side="left", padx=(8, 0)
		)
		self.bind_all("<Alt-t>", lambda _: self._testar_conexao())
		self.bind_all("<Alt-g>", lambda _: self._gravar_banco())
		ttk.Label(
			aba,
			text="Gravar escreve db_type, db_host, db_port, root_login e root_password no common_site_config.json",
		).grid(row=7, column=0, columnspan=3, sticky="w")

		ttk.Separator(aba).grid(row=8, column=0, columnspan=3, sticky="we", pady=10)
		ttk.Checkbutton(
			aba,
			text="Mostrar o comando bench new-site para este banco",
			variable=self.comando_visivel,
			command=self._alternar_comando,
		).grid(row=9, column=0, columnspan=3, sticky="w")

		self.bloco_comando = ttk.Frame(aba)
		ttk.Label(self.bloco_comando, text="Nome do site").grid(row=0, column=0, sticky="w", pady=3)
		ttk.Entry(self.bloco_comando, textvariable=self.site_novo, width=40).grid(
			row=0, column=1, sticky="we", pady=3
		)
		ttk.Label(self.bloco_comando, text="Senha do Administrator (vazia: o bench pergunta)").grid(
			row=1, column=0, sticky="w", pady=3
		)
		ttk.Entry(self.bloco_comando, textvariable=self.senha_admin, width=40).grid(
			row=1, column=1, sticky="we", pady=3
		)
		ttk.Button(self.bloco_comando, text="Gerar e copiar", command=self._copiar_new_site).grid(
			row=1, column=2, padx=(8, 0)
		)
		self.texto_comando = tk.Text(self.bloco_comando, height=6, wrap="word")
		self.texto_comando.grid(row=2, column=0, columnspan=3, sticky="we", pady=(6, 0))
		self.bloco_comando.columnconfigure(1, weight=1)
		aba.columnconfigure(1, weight=1)

	def _alternar_comando(self):
		"""Divulgação progressiva: o comando só ocupa a tela para quem vai criar um site."""
		if self.comando_visivel.get():
			self.bloco_comando.grid(row=10, column=0, columnspan=3, sticky="we", pady=(6, 0))
		else:
			self.bloco_comando.grid_forget()

	def _ao_trocar_tipo(self):
		"""Trocar o servidor sugere porta e usuário padrão — só se os atuais forem os padrão do outro.

		Uma porta digitada à mão (3307 do container, por exemplo) é dado confirmado e não é
		sobrescrito por sugestão.
		"""
		if self.porta.get() in {str(p) for p in cfg.PORTA_PADRAO.values()}:
			self.porta.set(str(cfg.PORTA_PADRAO[self.tipo.get()]))

		if self.usuario_root.get() in ("root", "postgres"):
			self.usuario_root.set("postgres" if self.tipo.get() == cfg.POSTGRES else "root")

	def _alternar_senha(self):
		self.campo_senha.configure(show="" if self.mostrar_senha.get() else "•")

	def _banco_da_tela(self) -> cfg.Banco:
		try:
			porta = int(self.porta.get() or 0)
		except ValueError as erro:
			raise cfg.CherryInvalido(
				f"a porta precisa ser um número — recebido {self.porta.get()!r}"
			) from erro

		return cfg.Banco(
			self.tipo.get(), self.host.get(), porta, self.usuario_root.get(), self.senha_root.get()
		)

	def _preencher_banco(self, comum: dict):
		tipo = comum.get("db_type") or cfg.MARIADB

		if tipo in cfg.TIPOS:
			self.tipo.set(tipo)

		self.host.set(str(comum.get("db_host", "127.0.0.1")))
		self.porta.set(str(comum.get("db_port", cfg.PORTA_PADRAO[self.tipo.get()])))
		self.usuario_root.set(str(comum.get("root_login", "postgres" if tipo == cfg.POSTGRES else "root")))
		self.senha_root.set(str(comum.get("root_password", "")))

	def _testar_conexao(self):
		try:
			banco = self._banco_da_tela()
		except cfg.CherryInvalido as erro:
			self._problema(erro)
			return

		self._informar(f"Testando {banco.rotulo} em {banco.host}:{banco.porta}…")
		self.update_idletasks()
		resultado = cfg.testar_conexao(banco, self.bench)

		if resultado.ok:
			self._informar(f"Conectou [{resultado.nivel}] — {resultado.mensagem}")
			self._confirmar_visualmente("✓ conectou")
		else:
			self._informar(f"Não conectou [{resultado.nivel}] — {resultado.mensagem}")
			messagebox.showwarning("Cherry — não conectou", resultado.mensagem, parent=self)

	def _gravar_banco(self):
		if not self._exigir_bench():
			return

		try:
			banco = self._banco_da_tela()
		except cfg.CherryInvalido as erro:
			self._problema(erro)
			return

		atual = cfg.ler_json(self.bench.common_config).get("db_type", cfg.MARIADB)
		sites = self.bench.nomes_de_sites()

		if (
			atual != banco.tipo
			and sites
			and not messagebox.askyesno(
				"Trocar o banco padrão do bench?",
				f"Este bench já tem {len(sites)} site(s) em {cfg.ROTULO.get(atual, atual)}. Os sites existentes "
				f"continuam no banco em que foram criados; só sites novos nascerão em {banco.rotulo}.\n\n"
				"Gravar mesmo assim?",
				parent=self,
			)
		):
			self._informar("Nada gravado")
			return

		try:
			dados = cfg.atualizar_json(self.bench.common_config, banco.chaves_common_config())
		except (OSError, json.JSONDecodeError) as erro:
			self._problema(erro)
			return

		self._informar(
			f"Gravado em {self.bench.common_config}: db_type={dados['db_type']} db_host={dados['db_host']} db_port={dados['db_port']}"
		)
		self._confirmar_visualmente()

	def _copiar_new_site(self):
		try:
			comando = cfg.comando_new_site(
				self._banco_da_tela(), self.site_novo.get(), self.senha_admin.get()
			)
		except cfg.CherryInvalido as erro:
			self._problema(erro)
			return

		self.texto_comando.delete("1.0", "end")
		self.texto_comando.insert("1.0", comando)
		self.clipboard_clear()
		self.clipboard_append(comando)
		self._agendar_limpeza_da_area_de_transferencia(comando)
		segundos = LIMPEZA_DA_AREA_DE_TRANSFERENCIA_MS // 1000
		self._informar(
			f"Comando bench new-site copiado — cole no terminal do bench; a área de transferência é limpa em {segundos} s"
		)
		self._confirmar_visualmente("✓ copiado")

	def _agendar_limpeza_da_area_de_transferencia(self, comando: str):
		"""Limpa a área de transferência depois do prazo, **só** se ainda tiver o comando copiado.

		Se o usuário já copiou outra coisa, não se apaga o que não é nosso."""
		if self._limpeza_agendada:
			self.after_cancel(self._limpeza_agendada)

		self._limpeza_agendada = self.after(
			LIMPEZA_DA_AREA_DE_TRANSFERENCIA_MS, lambda: self._limpar_area_de_transferencia(comando)
		)

	def _limpar_area_de_transferencia(self, comando: str):
		self._limpeza_agendada = None

		try:
			atual = self.clipboard_get()
		except tk.TclError:
			return  # vazia, ou com algo que não é texto: nada nosso para apagar

		if atual == comando:
			self.clipboard_clear()
			self._informar("Área de transferência limpa — o comando com a senha não está mais nela")

	# ------------------------------------------------------------------ aba: portas e redis

	CHAVES_PORTAS = (
		("webserver_port", "Porta do servidor web"),
		("socketio_port", "Porta do socketio"),
		("redis_cache", "Redis do cache (redis://host:porta)"),
		("redis_queue", "Redis da fila"),
		("redis_socketio", "Redis do socketio"),
		("file_watcher_port", "Porta do file watcher"),
	)

	def _aba_portas(self):
		aba = ttk.Frame(self.abas, padding=14)
		self.abas.add(aba, text="Portas e Redis", underline=0)
		self._instrucao(aba, "Defina as portas deste bench — dois benches nunca compartilham o mesmo Redis")
		self.portas: dict[str, tk.StringVar] = {}

		for i, (chave, rotulo) in enumerate(self.CHAVES_PORTAS, start=1):
			self.portas[chave] = tk.StringVar()
			ttk.Label(aba, text=rotulo).grid(row=i, column=0, sticky="w", pady=3)
			campo = ttk.Entry(aba, textvariable=self.portas[chave], width=40)
			campo.grid(row=i, column=1, sticky="we", pady=3)
			campo.bind("<Return>", lambda _: self._gravar_portas())

		self.developer_mode = tk.BooleanVar()
		ttk.Checkbutton(
			aba,
			text="developer_mode — grava relatórios e DocTypes salvos pela tela no disco do app",
			variable=self.developer_mode,
		).grid(row=8, column=0, columnspan=2, sticky="w", pady=(8, 4))
		ttk.Button(aba, text="Gravar no bench", underline=0, command=self._gravar_portas).grid(
			row=9, column=0, sticky="w", pady=(8, 0)
		)
		aba.columnconfigure(1, weight=1)

	def _preencher_portas(self, comum: dict):
		for chave, _ in self.CHAVES_PORTAS:
			self.portas[chave].set(str(comum.get(chave, "")))

		self.developer_mode.set(bool(comum.get("developer_mode")))

	def _gravar_portas(self):
		if not self._exigir_bench():
			return

		alteracoes: dict = {}

		for chave, rotulo in self.CHAVES_PORTAS:
			valor = self.portas[chave].get().strip()

			if not valor:
				alteracoes[chave] = None
			elif chave.endswith("_port"):
				try:
					alteracoes[chave] = int(valor)
				except ValueError:
					self._problema(f"{rotulo} precisa ser um número — recebido {valor!r}")
					return
			else:
				alteracoes[chave] = valor

		alteracoes["developer_mode"] = 1 if self.developer_mode.get() else None

		try:
			cfg.atualizar_json(self.bench.common_config, alteracoes)
		except (OSError, json.JSONDecodeError) as erro:
			self._problema(erro)
			return

		self._informar("Portas, Redis e developer_mode gravados no common_site_config.json")
		self._confirmar_visualmente()

	# ------------------------------------------------------------------ aba: sites

	def _aba_sites(self):
		aba = ttk.Frame(self.abas, padding=14)
		self.abas.add(aba, text="Sites", underline=0)
		self._instrucao(aba, "Escolha um site para ver o banco dele e liberar os testes")

		self.lista_sites = tk.Listbox(aba, height=9, exportselection=False)
		self.lista_sites.grid(row=1, column=0, rowspan=4, sticky="ns")
		self.lista_sites.bind("<<ListboxSelect>>", lambda _: self._mostrar_site())

		self.detalhe_site = tk.Text(aba, height=12, width=60, wrap="none", state="disabled")
		self.detalhe_site.grid(row=1, column=1, columnspan=2, sticky="nsew", padx=(12, 0))

		self.allow_tests = tk.BooleanVar()
		ttk.Checkbutton(
			aba, text="allow_tests — exigido por bench run-tests", variable=self.allow_tests
		).grid(row=2, column=1, sticky="w", pady=(6, 2), padx=(12, 0))
		ttk.Button(aba, text="Gravar no site", command=self._gravar_site).grid(
			row=3, column=1, sticky="w", padx=(12, 0)
		)
		ttk.Button(aba, text="Tornar o site padrão do bench", command=self._tornar_padrao).grid(
			row=4, column=1, sticky="w", pady=(4, 0), padx=(12, 0)
		)
		self.site_padrao = tk.StringVar(value="Site padrão (default_site): nenhum")
		ttk.Label(aba, textvariable=self.site_padrao).grid(
			row=5, column=0, columnspan=3, sticky="w", pady=(10, 0)
		)
		aba.columnconfigure(1, weight=1)
		aba.rowconfigure(1, weight=1)

	def _preencher_sites(self, sites: list[str], padrao: str):
		self.lista_sites.delete(0, "end")

		for site in sites:
			self.lista_sites.insert("end", site)

		self.site_padrao.set(
			f"Site padrão (default_site): {padrao or 'nenhum — sem ele, bench serve responde 404 em toda rota'}"
		)

	def _site_selecionado(self) -> str | None:
		selecao = self.lista_sites.curselection()

		return self.lista_sites.get(selecao[0]) if selecao else None

	def _mostrar_site(self):
		site = self._site_selecionado()

		if not site or not self.bench:
			return

		dados = dict(cfg.ler_json(self.bench.site_config(site)))

		for chave in ("db_password", "root_password", "encryption_key"):
			if chave in dados:
				dados[chave] = "***"

		self.allow_tests.set(bool(dados.get("allow_tests")))
		self.detalhe_site.configure(state="normal")
		self.detalhe_site.delete("1.0", "end")
		self.detalhe_site.insert("1.0", json.dumps(dados, indent=1, sort_keys=True, ensure_ascii=False))
		self.detalhe_site.configure(state="disabled")

	def _gravar_site(self):
		site = self._site_selecionado()

		if not self._exigir_bench() or not site:
			self._informar("Selecione um site na lista")
			return

		cfg.atualizar_json(
			self.bench.site_config(site), {"allow_tests": True if self.allow_tests.get() else None}
		)
		self._mostrar_site()
		self._informar(f"{site}: allow_tests {'ligado' if self.allow_tests.get() else 'removido'}")
		self._confirmar_visualmente()

	def _tornar_padrao(self):
		site = self._site_selecionado()

		if not self._exigir_bench() or not site:
			self._informar("Selecione um site na lista")
			return

		cfg.atualizar_json(self.bench.common_config, {"default_site": site, "serve_default_site": True})
		self.site_padrao.set(f"Site padrão (default_site): {site}")
		self._informar(f"default_site={site} gravado — currentsite.txt não é mais suportado pelo Frappe")
		self._confirmar_visualmente()

	# ------------------------------------------------------------------ aba: apps.txt

	def _aba_apps(self):
		aba = ttk.Frame(self.abas, padding=14)
		self.abas.add(aba, text="apps.txt", underline=0)
		self._instrucao(aba, "Liste os apps que o bench pode instalar, um por linha", colunas=1)
		ttk.Label(
			aba,
			text="O Cherry grava sempre com quebra de linha final — sem ela o último app some "
			"(docs/banco-do-bench-v16.md, 4b)",
			wraplength=680,
		).grid(row=1, column=0, sticky="w")
		self.texto_apps = tk.Text(aba, height=10, width=40)
		self.texto_apps.grid(row=2, column=0, sticky="w", pady=8)
		ttk.Button(aba, text="Gravar apps.txt", command=self._gravar_apps).grid(row=3, column=0, sticky="w")

	def _preencher_apps(self, apps: list[str]):
		self.texto_apps.delete("1.0", "end")
		self.texto_apps.insert("1.0", "\n".join(apps))

	def _gravar_apps(self):
		if not self._exigir_bench():
			return

		try:
			texto = cfg.gravar_apps_txt(self.bench.apps_txt, self.texto_apps.get("1.0", "end").splitlines())
		except (cfg.CherryInvalido, OSError) as erro:
			self._problema(erro)
			return

		self._preencher_apps(texto.split())
		self._informar(f"apps.txt gravado com {len(texto.split())} app(s) e quebra de linha final")
		self._confirmar_visualmente()

	# ------------------------------------------------------------------ preferências

	def _exigir_bench(self) -> bool:
		if self.bench is None:
			self._problema("nenhum bench carregado — escolha um na aba Bench")
			self.abas.select(0)
			return False

		return True

	def _carregar_preferencias(self):
		try:
			prefs = cfg.ler_json(PREFERENCIAS)
		except (cfg.CherryInvalido, json.JSONDecodeError, OSError):
			return

		for chave, variavel in (
			("distro", self.distro),
			("caminho_linux", self.caminho_linux),
			("raiz_local", self.raiz_local),
		):
			if prefs.get(chave):
				variavel.set(prefs[chave])

		if prefs.get("geometria"):
			self.geometry(prefs["geometria"])

	def _salvar_preferencias(self):
		if self.bench is None:
			return

		try:
			cfg.gravar_json(
				PREFERENCIAS,
				{
					"distro": self.bench.distro,
					"caminho_linux": self.bench.caminho_linux,
					"raiz_local": "" if self.bench.no_wsl else str(self.bench.raiz),
					"geometria": self.geometry(),
				},
			)
		except OSError:
			pass


def _nitidez_no_windows():
	"""Sem isto, o Windows escala a janela como bitmap e o texto sai borrado em telas HiDPI."""
	if sys.platform != "win32":
		return

	try:
		import ctypes

		ctypes.windll.shcore.SetProcessDpiAwareness(1)
	except (AttributeError, OSError):
		pass


def _tema_nativo(janela: tk.Tk):
	"""Controles com a aparência do sistema, quando o Tk oferece o tema."""
	estilo = ttk.Style(janela)

	for tema in ("vista", "winnative", "clam"):
		if tema in estilo.theme_names():
			estilo.theme_use(tema)
			break


def main():
	Cherry().mainloop()


if __name__ == "__main__":
	main()
