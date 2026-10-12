# Rede municipal de Porto Velho e o LAM (Laboratório Central Municipal)

Levantamento de 2026-10-12 a partir do CNES, para o change `laboratorio-sus-ciclo-completo`. Pergunta: quais unidades de saúde de
Porto Velho (RO), incluindo distritos e Baixo Madeira, utilizam os serviços do LAM.

## Resposta curta

**O CNES público não registra quem usa os serviços do LAM.** O vínculo de serviço terceiro existe no layout do arquivo de serviços
especializados (campos `TERCEIRO` e `CNESTERC`), mas está **vazio em todos os registros** dos arquivos que baixei: Rondônia em
08/2026 (10.834 linhas), 08/2025, 08/2024 e 08/2023, e Rio de Janeiro em 08/2026 (69.645 linhas). Logo, dá para listar a **rede
municipal provável** (mesma mantenedora do LAM), mas **não** provar o uso. A prova virá do próprio módulo, que registra a CNES de
cada unidade solicitante em cada requisição.

## Fontes e método

| Item | Fonte | Observação |
|---|---|---|
| Estabelecimentos de Porto Velho (2.280) | API de dados abertos do CNES (`apidadosabertos.saude.gov.br/cnes/estabelecimentos`, município 110020) | Todas as naturezas; nome, tipo, bairro, coordenadas |
| Serviços especializados (SR) | FTP do DATASUS, `CNES/200508_/Dados/SR/SRRO2608.dbc` (competência 08/2026) | Arquivo `.dbc` decodificado com leitor próprio em Python (PKWare DCL); validado: 10.834 registros e campos legíveis |
| LAM | CNES **6462995**, "Laboratório Central Municipal LAM", tipo 67, bairro Embratel, gestão municipal | Mantenedora CNPJ 05.903.125/0001-45 |
| Rede | Unidades de Porto Velho (110020) com a **mesma mantenedora** do LAM no arquivo SR | 102 unidades |

O LAM declara no CNES os serviços 120, 141 e 145 (este último com 13 classificações). Pela Tabela Unificada SIGTAP de 09/2026 (FTP do
DATASUS, `tb_servico`): **120 = Serviço de Diagnóstico por Anatomia Patológica e/ou Citopatologia**, **141 = Serviço de Vigilância em
Saúde** e **145 = Serviço de Diagnóstico por Laboratório Clínico** (confirmado).

### O que a lista é e o que não é

- **É** o conjunto de unidades mantidas pela mesma entidade do LAM (a gestão municipal de saúde): o público provável do LAM.
- **Não é** prova de uso: uma UBS pode mandar amostra a outro laboratório, e uma unidade fora da lista pode mandar ao LAM.
- A coluna "Serviço 145" indica que a unidade declara o código 145 no CNES. **Se 145 for mesmo laboratório (hipótese não confirmada)**, essas
  unidades têm menos razão de depender do LAM. Postos pequenos com "sim" sugerem que o código pode significar outra coisa: **não use a coluna como fato**.
- **Coordenadas do CNES são pouco confiáveis**: muitas unidades distintas repetem o mesmo ponto (por volta de -8,76 / -63,90), que parece
  um valor padrão. Só Calama e São Carlos têm coordenadas que parecem próprias. Não use as coordenadas para localizar as unidades.
- O campo de bairro vem truncado do CNES (por exemplo, "Distrito Cujubim Gra").
- Baixo Madeira foi classificado por evidência no cadastro (unidade fluvial e distritos de Calama, Nazaré e São Carlos). Unidades de
  "zona rural" ficaram à parte, com coordenadas, porque o cadastro não diz a localidade. **A confirmar com a secretaria.**

## Totais

| Grupo | Unidades |
|---|---|
| Sede (zona urbana) | 85 |
| Distritos | 6 |
| Baixo Madeira | 4 |
| Zona rural (localização a confirmar) | 7 |
| **Total** | **102** |

## Sede (zona urbana) (85)

| CNES | Unidade | Tipo | Bairro / localidade | Serviço 145 (hipótese: laboratório) | Coordenadas |
|---|---|---|---|---|---|
| 6365469 | Caps Ad | CAPS | Agenor De Carvalho | não | -8.7536, -63.8629 |
| 2806495 | Caps Do Municipio De Porto Velho Tres Marias | CAPS | Sao Cristovao | não | -8.7665, -63.8752 |
| 7089937 | Caps Infanto Juvenil | CAPS | Sao Cristovao | não | -8.7625, -63.9039 |
| 2552914 | Centro De Especialidades Medicas Dr Alfredo Silva | Clínica/Ambulatório especializado | Nova Porto Velho | sim | -8.7589, -63.8745 |
| 7016557 | Centro De Especialidades Medicas Dr Rafael Vaz E Silva | Clínica/Ambulatório especializado | Nossa Sha Das Gracas | sim | -8.7660, -63.8849 |
| 2802708 | Centro Especializado Em Reabilitacao Cer | Clínica/Ambulatório especializado | Pedrinhas | não | -8.7478, -63.9064 |
| 5599334 | Centro Municipal De Especialidades Odontologicas Zona Leste1 | Clínica/Ambulatório especializado | Tancredo Neves | não | -8.7626, -63.8374 |
| 5599253 | Centro Municipal De Especialidades Odontologicas Zona Leste2 | Clínica/Ambulatório especializado | Socialista | não | -8.7611, -63.8274 |
| 5599245 | Centro Municipal De Especialidades Odontologicas Zona Sul | Clínica/Ambulatório especializado | Jardim Eldorado | não | -8.7927, -63.8810 |
| 4169859 | Cerest Porto Velho | Clínica/Ambulatório especializado | Sao Cristovao | não | -8.7439, -63.8855 |
| 6863868 | Servico De Atendimento Especializada Sae | Clínica/Ambulatório especializado | Sao Cristovao | não | -8.7586, -63.8949 |
| 3970442 | Hospital Maternidade Mae Esperanca | Hospital Especializado | Embratel | sim | -8.7541, -63.8819 |
| 0038105 | Laboratorio Municipal De Citologia | Laboratório de saúde pública | Embratel | não | -8.7520, -63.8822 |
| 6462995 | Laboratorio Central Municipal Lam | Laboratório municipal | Embratel | sim | -8.7512, -63.8824 |
| 2807483 | P S Agrovila Nova Alianca | Posto de Saúde | Embratel | não | -8.7619, -63.9040 |
| 2807343 | Ps Cachoeira Do Teotonio Porto Velho | Posto de Saúde | Cachoeira Do Teotoni | não | -8.7619, -63.9040 |
| 2807408 | Ps Demarcacao | Posto de Saúde | Rio Machado Baixo Ma | não | -8.7622, -63.9039 |
| 9044310 | Ps Lago Do Cunia | Posto de Saúde | Baixo Madeira | não | -8.7622, -63.9039 |
| 2808099 | Ps Papagaios | Posto de Saúde | Baixo Madeira | não | -8.7621, -63.9040 |
| 2369931 | Ps Sao Jose | Posto de Saúde | Baixo Madeira Rio Ma | não | -8.5343, -63.4689 |
| 2808226 | Ps Sao Miguel | Posto de Saúde | Sao Miguel Baixo Mad | sim | -8.7622, -63.9040 |
| 8511748 | Samu Mt 01 | SAMU | Embratel | não | -8.7543, -63.8815 |
| 8511993 | Samu Mt 02 | SAMU | Embratel | não | -8.7542, -63.8816 |
| 8512078 | Samu Mt 03 | SAMU | Embratel | não | -8.7541, -63.8817 |
| 8512094 | Samu Mt 04 | SAMU | Embratel | não | -8.7543, -63.8817 |
| 2808439 | Samu Usa Unidade De Suporte Avancado Porto Velho | SAMU | Embratel | não | -8.7544, -63.8817 |
| 6950450 | Samu Usb 1 Unidade De Suporte Basico Porto Velho | SAMU | Embratel | não | -8.7545, -63.8818 |
| 6950469 | Samu Usb 2 Unidade De Suporto Basico Porto Velho | SAMU | Embratel | não | -8.7542, -63.8818 |
| 6950477 | Samu Usb 3 Unidade De Suporte Basico Porto Velho | SAMU | Embratel | não | -8.7542, -63.8817 |
| 6950485 | Samu Usb 4 Unidade De Suporte Basico Porto Velho | SAMU | Embratel | não | -8.7902, -63.6938 |
| 7122128 | Samu Usb 5 Unidade De Suporte Basico Porto Velho | SAMU | Embratel | não | -8.7902, -63.6938 |
| 7124244 | Samu Usb 6 Unidade De Suporte Basico Porto Velho | SAMU | Embratel | não | -8.7542, -63.8812 |
| 2494051 | Centro De Saude Areal Da Floresta Porto Velho | UBS/Centro de Saúde | Areal Da Floresta | não | -8.7835, -63.8839 |
| 6670709 | Centro De Saude Manoel Amorim De Matos | UBS/Centro de Saúde | Cohab Floresta | não | -8.7928, -63.8809 |
| 2806916 | Centro De Saude Mauricio Bustani | UBS/Centro de Saúde | Liberdade | não | -8.7524, -63.8878 |
| 9975616 | Servicos De Praticas Integrativas E Complementares Em Saude | UBS/Centro de Saúde | Embratel | não | -8.7514, -63.8823 |
| 2806568 | Unidade De Saude Da Familia Agenor De Carvalho Porto Velho | UBS/Centro de Saúde | Agenor De Carvalho | não | -8.7616, -63.8640 |
| 5695880 | Unidade De Saude Da Familia Aponia | UBS/Centro de Saúde | Aponia | não | -8.7417, -63.8563 |
| 2806592 | Unidade De Saude Da Familia Caladinho | UBS/Centro de Saúde | Caladinho | sim | -8.8053, -63.8776 |
| 9577866 | Unidade De Saude Da Familia Castanheiras | UBS/Centro de Saúde | Castanheira | sim | -8.7890, -63.8682 |
| 6582915 | Unidade De Saude Da Familia De Alianca | UBS/Centro de Saúde | Estrada Da Penal | sim | -8.7620, -63.9039 |
| 5822793 | Unidade De Saude Da Familia De Sao Sebastiao | UBS/Centro de Saúde | Sao Sebastiao 1 | sim | -8.7387, -63.9082 |
| 2802716 | Unidade De Saude Da Familia Dr Renato Medeiros | UBS/Centro de Saúde | Cidade Do Lobo | não | -8.8056, -63.8878 |
| 2806789 | Unidade De Saude Da Familia Ernande C Coutinho | UBS/Centro de Saúde | Esp Da Comunidade | não | -8.7499, -63.8466 |
| 2806797 | Unidade De Saude Da Familia Fortaleza Do Abuna | UBS/Centro de Saúde | Dist Fortaleza Do Ab | não | -8.7621, -63.9040 |
| 6670547 | Unidade De Saude Da Familia Hamilton Raulino Gondin | UBS/Centro de Saúde | Tancredo Neves | não | -8.7591, -63.8385 |
| 6670814 | Unidade De Saude Da Familia Jose Adelino Da Silva | UBS/Centro de Saúde | Ulisses Guimaraes | sim | -8.7789, -63.8022 |
| 6386512 | Unidade De Saude Da Familia Mariana | UBS/Centro de Saúde | Mariana | sim | -8.7715, -63.8208 |
| 2802961 | Unidade De Saude Da Familia Nova California | UBS/Centro de Saúde | Dist Nova Califonia | sim | -8.7650, -63.9015 |
| 2494531 | Unidade De Saude Da Familia Nova Floresta | UBS/Centro de Saúde | Nova Horizonte | sim | -8.8015, -63.8937 |
| 2806673 | Unidade De Saude Da Familia Nova Mutum | UBS/Centro de Saúde | Dist Mutum Parana | sim | -8.7621, -63.9040 |
| 7928769 | Unidade De Saude Da Familia Novo Engenho Velho | UBS/Centro de Saúde | Dist Sao Sebastiao | sim | -8.7618, -63.9041 |
| 2493942 | Unidade De Saude Da Familia Osvaldo Piana | UBS/Centro de Saúde | Areal | sim | -8.7774, -63.8987 |
| 2496577 | Unidade De Saude Da Familia Pedacinho De Chao | UBS/Centro de Saúde | Padacinho De Chao | não | -8.7435, -63.8829 |
| 7280408 | Unidade De Saude Da Familia Rio Pardo | UBS/Centro de Saúde | Assent Rio Pardo | não | -9.6306, -63.9663 |
| 2494558 | Unidade De Saude Da Familia Ronaldo Aragao | UBS/Centro de Saúde | Nacional | sim | -8.7325, -63.9077 |
| 6246524 | Unidade De Saude Da Familia Santo Antonio | UBS/Centro de Saúde | Triangulo | não | -8.8040, -63.9272 |
| 5695899 | Unidade De Saude Da Familia Socialista | UBS/Centro de Saúde | Socialista | sim | -8.7617, -63.8275 |
| 4930363 | Unidade De Saude Da Familia Tres Marias | UBS/Centro de Saúde | Igarape | não | -8.7696, -63.8501 |
| 3521532 | Unidade De Saude Da Familia Uniao Bandeirantes | UBS/Centro de Saúde | Dist Uniao Bandeiran | sim | -8.7620, -63.9042 |
| 6021999 | Unidade De Saude Da Familia Vila Princesa | UBS/Centro de Saúde | Vila Princesa | não | -8.7765, -63.8910 |
| 2806991 | Unidade De Saude Da Familia Vista Alegre Do Abuna | UBS/Centro de Saúde | Dist Vista Alegre Do | sim | -8.7650, -63.9014 |
| 4001028 | Pronto Atendimento Ana Adelaide | UPA / Pronto atendimento | Pedrinhas | sim | -8.7481, -63.9060 |
| 2494078 | Pronto Atendimento Jose Adelino Da Silva | UPA / Pronto atendimento | Marcos Freire | sim | -8.7689, -63.8314 |
| 4954017 | Sala De Estabilizacao De Uniao Bandeirantes | UPA / Pronto atendimento | Dist Uniao Bandeiran | não | -9.7073, -64.5312 |
| 8291462 | Sala De Estabilizacao De Vista Alegre Do Abuna | UPA / Pronto atendimento | Vista Alegre Do Abun | não | -8.7650, -63.9017 |
| 2496461 | Upa Zona Leste | UPA / Pronto atendimento | Tancredo Neves | sim | -8.7631, -63.8440 |
| 2680017 | Upa Zona Sul | UPA / Pronto atendimento | Cohab Floresta | sim | -8.7876, -63.8780 |
| 8395365 | Vacimovel De Porto Velho | Unidade móvel terrestre | Centro | não | -8.7650, -63.9017 |
| 0112003 | Centro De Infomacoes Estrategicas Em Vigilancia Em Saude | Vigilância em Saúde | Pedrinhas | não | -8.7481, -63.9047 |
| 5792495 | Divisao De Controle De Vetores Dcv | Vigilância em Saúde | Cascalheiras | não | -8.7845, -63.8388 |
| 4455134 | Divisao De Controle De Zoonoses De Porto Velho | Vigilância em Saúde | Cascalheiras | não | -8.7849, -63.8382 |
| 4450434 | Divisao De Pesquisa E Diagnostico E Zoonoses E Entomologia | Vigilância em Saúde | Cascalheira | não | -8.7803, -63.8395 |
| 4477650 | Divisao De Vigilancia Epidemiologica Dve | Vigilância em Saúde | Centro | não | -8.7788, -63.8983 |
| 2807041 | Divisao De Vigilancia Licenciamento E Risco Sanitario Dvisa | Vigilância em Saúde | Centro | não | -8.7650, -63.9015 |
| 9547282 | Servico De Inspecao Municipal Sim | Vigilância em Saúde | Jk Ii | não | -8.7736, -63.8374 |
| 7935609 | Centro De Referencia Da Saude Da Crianca | tipo 39 | Nossa Senhora Das Gr | não | -8.7677, -63.8926 |
| 3521567 | Centro De Referencia Da Saude Da Mulher | tipo 39 | Sao Cristovao | não | -8.7586, -63.8872 |
| 0037494 | Creami | tipo 39 | Tancredo Neves | não | -8.7621, -63.8374 |
| 7890761 | Central De Abastecimento Farmaceutico Caf Semusa | tipo 43 | Jardim Eldorado | não | -8.7806, -63.8715 |
| 8148406 | Departamento De Atencao Basica Dab | tipo 68 | Centro | não | -8.7648, -63.9014 |
| 6482732 | Secretaria Municipal De Saude | tipo 68 | Areal | não | -8.7649, -63.9015 |
| 6944655 | Samu Central De Regulacao Medicas Das Urgencia De P Velho | tipo 76 | Embratel | não | -8.7542, -63.8817 |
| 6060048 | Central Municipal De Regulacao Do Acesso | tipo 81 | Centro | não | -8.7652, -63.9013 |
| 0213241 | Central De Rede De Frio Porto Velho | tipo 84 | Eldorado | não | -8.7847, -63.8687 |

## Distritos (6)

| CNES | Unidade | Tipo | Bairro / localidade | Serviço 145 (hipótese: laboratório) | Coordenadas |
|---|---|---|---|---|---|
| 2806517 | Posto De Saude De Morrinhos | Posto de Saúde | Distrito Morrinhos | sim | -8.7682, -64.0213 |
| 2806541 | Unidade De Saude Da Familia Abuna | UBS/Centro de Saúde | Distrito Abuna | não | -8.7649, -63.9014 |
| 2806649 | Unidade De Saude Da Familia De Extrema | UBS/Centro de Saúde | Distrito Extrema | sim | -8.7649, -63.9015 |
| 2806886 | Unidade De Saude Da Familia Jacy Parana | UBS/Centro de Saúde | Distrito Jacy Parana | não | -8.7620, -63.9039 |
| 2806622 | Unidade De Saude Da Familia Jose Gomes Ferreira | UBS/Centro de Saúde | Distrito Cujubim Gra | sim | -8.7604, -63.9791 |
| 2808153 | Unidade De Saude Da Familia Rio Das Garcas | UBS/Centro de Saúde | Distrito Rio Das Gar | sim | -8.7623, -63.9040 |

## Baixo Madeira (4)

| CNES | Unidade | Tipo | Bairro / localidade | Serviço 145 (hipótese: laboratório) | Coordenadas |
|---|---|---|---|---|---|
| 2806576 | Unidade De Saude Da Familia Benjamim Silva | UBS/Centro de Saúde | Distrito Calama | sim | -8.2392, -63.1800 |
| 2806908 | Unidade De Saude Da Familia Maria N Da Silva | UBS/Centro de Saúde | Distrito Nazare | sim | -8.7619, -63.9040 |
| 2806967 | Unidade De Saude Da Familia Sao Carlos | UBS/Centro de Saúde | Distrito Sao Carlos | sim | -8.4362, -63.4992 |
| 3326292 | Unid De Saude Dr Floriano Riva Filho | Unidade fluvial | Centro | não | -8.7650, -63.9103 |

## Zona rural (localização a confirmar) (7)

| CNES | Unidade | Tipo | Bairro / localidade | Serviço 145 (hipótese: laboratório) | Coordenadas |
|---|---|---|---|---|---|
| 9044345 | Ps Nova Esperanca | Posto de Saúde | Zona Rural | não | -8.7619, -63.9040 |
| 9044329 | Ps Terra Santa | Posto de Saúde | Zona Rural | não | -8.6643, -63.8188 |
| 4068351 | Samu Usb 7 Unidade De Suporte Basico Jacy Parana | SAMU | Zona Rural | não | -9.1997, -64.3359 |
| 7270860 | Unidade De Saude Da Familia Joana Darc | UBS/Centro de Saúde | Zona Rural | não | -8.7568, -63.9614 |
| 2807424 | Unidade De Saude Da Familia Maria Camelo De Oliveira | UBS/Centro de Saúde | Zona Rural | não | -8.6533, -63.7640 |
| 7287305 | Unidade De Saude Da Familia Santa Rita | UBS/Centro de Saúde | Zona Rural | não | -8.7620, -63.9039 |
| 9743081 | Upa Jacy Parana | UPA / Pronto atendimento | Zona Rural | sim | -9.2507, -64.4030 |

## Outras unidades laboratoriais públicas do município (para não confundir com o LAM)

| CNES | Unidade | Tipo | Bairro |
|---|---|---|---|
| 6462995 | Laboratorio Central Municipal Lam | 67 | Embratel |
| 6877230 | Laboratorio Municipal Pol Osvaldo Cruz | 39 | Areal Da Floresta |
| 38105 | Laboratorio Municipal De Citologia | 80 | Embratel |
| 8241678 | Dil Divisao De Laboratorio | 80 | Embratel |
| 2496860 | Laboratorio Central Porto Velho Lacen | 80 | Costa E Silva |

## Próximos passos

1. Pedir à secretaria a **lista real de unidades que enviam amostra ao LAM** (e de quais distritos e comunidades do Baixo Madeira); 
   confrontar com esta rede.
2. Confirmar o significado dos códigos de serviço (120, 141, 145) e a localidade das unidades de zona rural.
3. Cadastrar a rede como unidades solicitantes no módulo (tarefa 14.1) e passar a registrar a CNES solicitante em toda requisição;
   em poucos meses isso substitui esta estimativa por dado de uso.
4. Se o CNES passar a preencher `TERCEIRO`/`CNESTERC`, repetir o levantamento.
