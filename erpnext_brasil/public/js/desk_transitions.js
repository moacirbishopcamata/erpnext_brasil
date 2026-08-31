// Copyright (c) 2026, ERPNext Brasil contributors
// License: MIT. See license.txt

/*
 * Aciona o fade-in de troca de rota (ver public/css/desk_transitions.css).
 *
 * "page-change" é evento público do próprio Frappe
 * ------------------------------------------------------------
 * Não é um hook inventado: `frappe/public/js/frappe/views/container.js` já
 * dispara `$(document).trigger("page-change", this.page)` a cada troca de
 * página — confirmado lendo o código-fonte, não suposto — e é o mesmo evento
 * que a barra de ferramentas e o awesome bar do próprio Frappe já escutam. Um
 * listener a mais aqui não compete com nada, não sobrescreve nada, e não exige
 * tocar em nenhum arquivo do `frappe`/`erpnext` core.
 *
 * Um listener só, nenhum trabalho por frame
 * ------------------------------------------------------
 * Isto não é um loop de animação (`requestAnimationFrame`) — é um único
 * `$(document).on(...)` que troca uma classe CSS por troca de página. O custo
 * de rodar isto é desprezível comparado ao resto do que já acontece numa troca
 * de rota do Desk (render de formulário/lista inteiro).
 *
 * Por que remover a classe antes de reaplicar
 * ------------------------------------------------------
 * Reaplicar uma classe CSS já presente no elemento não reinicia uma animação
 * (`@keyframes`) em andamento ou já concluída — o navegador não detecta
 * mudança. Remover, forçar um reflow síncrono (`offsetWidth`, a única leitura
 * de layout deste arquivo, e é barata: um elemento só, uma vez por troca de
 * página) e só então reaplicar é o jeito padrão de reiniciar uma animação CSS
 * via JS.
 */

$(document).on("page-change", function (event, page) {
	if (!page) {
		return;
	}

	const $page = $(page);

	$page.removeClass("erpnext-brasil-fade-in");
	void page.offsetWidth; // força o reflow que reinicia a animação
	$page.addClass("erpnext-brasil-fade-in");
});
