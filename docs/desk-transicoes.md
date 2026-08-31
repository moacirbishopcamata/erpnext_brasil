# Transições e animações do Desk: identidade visual sem pesar no sistema

Pedido explícito do usuário: transições suaves, fade-in e de rotas, para "mostrar
identidade única e avanço técnico" — com uma condição igualmente explícita: sem
pesar no desempenho do sistema.

## Onde entra, sem tocar em nenhum arquivo do `frappe`/`erpnext`

Dois hooks padrão do Frappe, declarados em `hooks.py`:

```python
app_include_css = "/assets/erpnext_brasil/css/desk_transitions.css"
app_include_js = "/assets/erpnext_brasil/js/desk_transitions.js"
```

Injetam CSS/JS em toda página do Desk quando o app está instalado — nenhum arquivo
do `erpnext`/`frappe` precisa ser editado.

## O evento de troca de rota já existe no Frappe — não foi inventado

Achado ao ler o código-fonte de `frappe/public/js/frappe/views/container.js`:
`$(document).trigger("page-change", this.page)` já é disparado a cada troca de
página, e é o **mesmo evento** que a barra de ferramentas e o *awesome bar* do
próprio Frappe escutam internamente. Um curioso indício de que a ideia já tinha
sido cogitada pelo próprio Frappe: a linha logo antes do disparo do evento tem um
`fadeIn(300)` **comentado** (código morto, não removido) — confirma que animar a
troca de página no exato ponto onde `desk_transitions.js` se conecta é o lugar
certo, não uma invenção deste projeto.

## Por que só `opacity`/`transform` — nunca `width`/`height`/`top`/`left`

As duas únicas propriedades animadas no CSS. As duas rodam inteiramente no
compositor da GPU, sem disparar reflow/repaint de layout — decisão explícita para
não "pesar no sistema", não um acidente de estilo. Animar `width`/`margin`/`top`
produziria efeito visual parecido, mas custaria reflow a cada frame — exatamente
o tipo de custo que o pedido do usuário queria evitar.

## Um listener, nenhum trabalho por frame

`desk_transitions.js` não é um loop de animação — é um único
`$(document).on("page-change", ...)` que troca uma classe CSS a cada troca de
página. Sem `setInterval`/`requestAnimationFrame`, sem trabalho contínuo. A única
leitura de layout (`offsetWidth`) é necessária para reiniciar a animação CSS a
cada troca de rota (reaplicar uma classe já presente não reinicia um `@keyframes`
em andamento) — uma leitura, um elemento, uma vez por navegação, custo
desprezível perto do resto do que uma troca de rota do Desk já faz (renderizar um
formulário ou lista inteiros).

## `prefers-reduced-motion`: desliga tudo, não só reduz

Todas as regras de animação/transição ficam dentro de
`@media (prefers-reduced-motion: no-preference)` — quem configurou o sistema
operacional para reduzir movimento normalmente tem um motivo real (enjoo,
distúrbio vestibular), e reduzir a animação pela metade ainda causa o mesmo
problema. A guarda remove a transição inteira para esse público, não a encurta.

## O que foi animado

- **Fade-in de rota**: o container da página nova (`.page-container`) recebe um
  `@keyframes` de opacidade + leve deslocamento vertical (`translateY(6px)→0`),
  220ms, ao trocar de rota.
- **Elementos interativos comuns**: `.btn`, linhas de lista, itens de sidebar,
  itens de dropdown/*awesomplete* — transição suave de 150ms em
  `opacity`/`transform`/`background-color` entre estados que o Desk padrão já
  trocaria instantaneamente (hover, foco, clique). Nenhum elemento novo é
  criado — só a transição entre estados que já existiam.
- **Seta de `Section Break` colapsável**: suaviza o giro do ícone ao
  expandir/colapsar uma seção.

## O que não foi tocado

Nenhuma lógica de negócio, nenhum comportamento funcional — só CSS de transição e
um listener de evento que não muda o que acontece, só como aparece na tela.

## Arquivos

- `public/css/desk_transitions.css`
- `public/js/desk_transitions.js`

## Fontes

- `frappe/public/js/frappe/views/container.js` (código-fonte lido diretamente do
  clone local) — usado para confirmar o evento `"page-change"` e o ponto exato do
  ciclo de vida da página onde ele dispara. Consultado em 2026-08-31.
