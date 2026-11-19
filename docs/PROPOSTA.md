# O fechamento do mês — proposta

Este documento responde à pergunta do case: como a Medipreço deveria cobrar os clientes de um jeito simples, escalável e auditável?

**A resposta, em um parágrafo.** A nota de cada mês deve ser calculada pela regra que está no contrato do cliente, sobre o que estava cadastrado no sistema no momento do fechamento. Depois de fechada, a nota não muda: o que o RH do cliente informa depois vale dali para a frente. Para isso funcionar, proponho três coisas. Cada contrato é descrito numa ficha de regras, com as mesmas poucas escolhas para todos. O sistema calcula a nota a partir da ficha e do histórico da base, sem planilha. E cada nota guarda a explicação do próprio número: quem foi cobrado, por qual regra e o que mudou.

O documento segue esta ordem: o que encontrei nos dados (seção 1), a escolha que sustenta a proposta (2), como ela vira sistema (3), o que muda para cada área (4), o caminho do contrato até a nota paga (5), as escolhas de escopo (6 e 7), as dúvidas que os contratos deixam (8), o que construí (9) e como usei a IA (10).

Para ver o protótipo funcionando: `python3 prototipo/servidor.py` (instruções no `README.md`).

## 1. O que os dados mostram

Antes de propor qualquer coisa, comparei as duas coisas que o kit traz: o que cada um dos seis contratos manda cobrar e as 28 notas que a Medipreço emitiu de agosto a outubro. O resultado explica as quatro falas do enunciado.

- **Todos os clientes são contados do mesmo jeito.** Em 27 dos 28 itens de nota, a quantidade cobrada é a contagem da base às 9h do dia de corte, qualquer que seja o contrato. É a "foto" que o enunciado descreve.
- **Quatro dos seis contratos pedem outra coisa.** A Faro paga proporcional aos dias de cada pessoa. O Grupo Cedro paga pelo maior número de vidas do mês e quer uma nota por empresa. A Delta paga por toda vida que esteve ativa ao menos um dia. A Bravo paga antecipado e tem direito a um acerto no mês seguinte. Nada disso é executado hoje.
- **O único item que não bate com a foto é um erro manual.** Na nota de setembro da Bravo foram cobradas 499 vidas, num contrato que cobra só os titulares (332). São R$ 2.505,00 a mais, e nada no processo percebeu. É a fala do financeiro: "se eu erro uma linha, ninguém percebe até o cliente reclamar".
- **Onde o contrato pede mesmo uma foto, o valor está certo e falta a explicação.** É o caso do RH no enunciado. A Aurora foi cobrada por 737 vidas, que é o que o contrato manda: a base no dia 26. O RH viu 718 no dia 31 porque 19 saídas entraram num arquivo que ele mesmo enviou no dia 27. A nota não dizia isso.

O dinheiro em jogo é pequeno: foram faturados R$ 75,6 mil em outubro, e as diferenças são de poucos por cento, ora a favor da Medipreço, ora do cliente. O custo maior é outro: dois dias de fechamento à mão, contestações que o CS não consegue responder e modelos de cobrança vendidos que a operação não executa.

## 2. A escolha central: vale o que estava cadastrado no fechamento

O enunciado avisa que enxergar o mês inteiro "não resolve, sozinho, como cobrar por ele". Esta seção explica por quê, e qual é a minha resposta.

**O problema.** Toda mudança na base tem duas datas: a data em que ela aconteceu, segundo o RH, e a data em que ela chegou à Medipreço. Um exemplo real, da Aurora: 14 colaboradores foram desligados entre 21 e 23 de outubro, mas o RH só enviou o arquivo com essas saídas no dia 27. O contrato manda contar a base no dia 26. Nesse dia, pela data do desligamento, os 14 já tinham saído; pelo que a Medipreço sabia, ainda estavam cadastrados. A cobrança precisa escolher qual das duas datas vale, e os contratos não dizem.

**A minha escolha.** Vale a data em que a mudança chegou ao sistema. A nota conta quem estava cadastrado no momento que o contrato define. Informação que chega depois muda os meses seguintes e nunca os anteriores. No exemplo, os 14 são cobrados em outubro e saem da conta em novembro.

Três motivos:

- **A nota fica final.** Calculada hoje ou daqui a um ano, dá o mesmo número. Se valesse a data declarada pelo RH, cada arquivo novo poderia alterar meses já cobrados, e toda nota viraria uma conta aberta, com recálculo e crédito sem fim.
- **Manter a base em dia é obrigação do cliente, e os contratos dizem isso.** Aurora, cláusula 4.1 (a): "manter a base de beneficiários atualizada". Delta, 7.3: a parceira "é a única responsável pela exatidão das bases". As cláusulas 2.2 do Cedro e 5.3 da Estrela vão no mesmo sentido.
- **É simples de explicar ao cliente.** "Cobramos quem estava na sua base neste momento, e esta é a lista."

**O custo dessa escolha.** Ela não é neutra, e a proposta não esconde isso:

- **O cliente paga por quem já saiu e ainda não foi informado.** Os 14 da Aurora custaram R$ 145,50 em outubro, e o RH nem estava atrasado: informou em poucos dias úteis.
- **Na Delta o efeito se inverte.** Das 5.105 vidas contadas em outubro, 192 tinham data de desligamento em setembro e só saíram do sistema num arquivo de 5 de outubro. Como a Delta paga menos por vida quando passa de 5.000, essas 192 baixam o preço de todas. Ali, informar com atraso reduz a nota.

O que faço com esse custo é deixá-lo à vista. A nota da Aurora lista as 19 saídas que chegaram depois da contagem, com a data de cada uma, e o RH vê quanto custa informar depois do dia 26. Se a Medipreço quiser dar crédito por desligamento informado com atraso, isso passa a ser uma regra do contrato, que aparece como item da nota seguinte. A nota anterior continua fechada.

### O caso que mais depende de interpretação: a Delta

A Delta mostra por que a interpretação adotada precisa estar escrita em cada nota. Ela paga por faixa: R$ 10 por vida até 5.000 vidas, R$ 9 de 5.001 a 10.000. A base dela fica em torno de 5.000, então pequenas diferenças na forma de contar mudam a faixa e, com ela, o preço de todas as vidas.

Em outubro a Medipreço faturou R$ 48.920,00 (4.892 vidas a R$ 10). Pelo contrato, a nota seria uma destas, conforme a interpretação:

| Interpretação | Vidas | Nota | O faturado ficou |
|---|---|---|---|
| Base cadastrada, preço da faixa para todas as vidas (a que adotei) | 5.105 | R$ 45.945 | R$ 2.975 a mais |
| Data declarada pelo RH, preço da faixa para todas as vidas | 5.055 | R$ 45.495 | R$ 3.425 a mais |
| Base cadastrada, sem os 192 desligados de setembro | 4.913 | R$ 49.130 | R$ 210 a menos |
| Base cadastrada, preço menor só para as vidas acima de 5.000 | 5.105 | R$ 50.945 | R$ 2.025 a menos |

Por isso não afirmo que a Medipreço cobrou R$ 3 mil a mais da Delta. O que os dados sustentam é mais modesto e mais útil: a foto de um único dia não aplica a cláusula 7.2 em nenhuma das interpretações, e cem ou duzentas vidas fazem a nota variar cerca de R$ 5 mil.

## 3. Como isso vira sistema

A escolha da seção 2 diz o que contar. Esta seção diz como a Medipreço deixa de depender da planilha para fazer essa conta. São quatro peças.

1. **Cada contrato vira uma ficha de regras.** Lendo os seis contratos, toda cobrança se descreve com as mesmas cinco escolhas: o que se conta (vidas ou só titulares), como se apura a quantidade (foto num dia, máximo do mês, ao menos um dia, proporcional aos dias), qual é o preço (fixo, por plano, por faixa, com ou sem mínimo), quantas notas saem (uma, ou uma por CNPJ) e quando se cobra (antes ou depois do mês). Quem preenche e aprova a ficha é uma pessoa, que responde por ela.
2. **O sistema faz a conta.** A partir da ficha e do histórico de entradas e saídas, ele apura a quantidade e o valor. A mesma ficha e a mesma base dão sempre o mesmo número.
3. **Cada nota guarda a própria explicação.** A lista das pessoas cobradas, a regra em português, o instante da contagem, o que mudou desde o mês anterior e o que chegou depois da contagem.
4. **Há uma conferência antes de emitir.** O sistema avisa o que hoje passa despercebido, como uma carga de 600 pessoas que o suporte desfez dois dias depois, ou pessoas que aparecem em duas empresas do mesmo grupo.

Como isso responde às três palavras da pergunta, e até onde vai:

- **Simples.** O financeiro deixa de contar e de interpretar contrato. Ele confere uma lista já calculada.
- **Escalável.** Um contrato novo que combina escolhas já conhecidas é só uma ficha nova. Quando a ficha pede algo que o sistema não sabe calcular, ele recusa e diz o motivo, em vez de calcular errado. Medi esse limite: as cinco escolhas formam 96 combinações possíveis, e o protótipo cobra 44 delas. São todas as 36 que não usam mínimo nem pró-rata, e 8 das 60 que usam.
- **Auditável.** Toda nota mostra a regra, as pessoas e as interpretações adotadas, e o cálculo refeito dá o mesmo resultado. Falta uma parte, que o protótipo não tem: guardar o fechamento aprovado junto com a versão da ficha que o calculou. Sem isso, editar a ficha muda o recálculo dos meses passados.

## 4. O que muda para cada área

O enunciado traz quatro falas. A tabela mostra o que cada uma ganha.

| Quem | Hoje | Com a proposta |
|---|---|---|
| Financeiro | conta à mão, interpreta contrato na planilha, erra sem perceber | confere e aprova um fechamento já calculado, com avisos, e baixa o arquivo das notas para emitir |
| RH do cliente | recebe um número e não sabe de onde veio | recebe a nota com a lista de pessoas, as datas e o que chegou depois da contagem |
| CS | abre planilha, banco e contrato e não fecha a conta | abre a nota e vê a regra, as pessoas e a diferença para o mês anterior |
| Comercial | promete sem saber se a operação consegue cobrar | consulta, antes de prometer, quais modelos o sistema cobra, quais recusa e por quê |

O RH e o CS fazem a mesma pergunta de lados opostos ("de onde veio este número?"), e por isso a mesma página, a nota explicada, responde aos dois. O comercial faz outra pergunta, antes de existir nota, e ganhou uma página própria.

## 5. O caminho, do contrato assinado à nota paga

O enunciado pede o caminho inteiro. A tabela mostra as oito etapas que enxergo nele e, em cada uma, o que este trabalho cobre.

| Etapa | O que acontece | Neste trabalho |
|---|---|---|
| 1. Contrato assinado | uma pessoa preenche a ficha e responde por ela; o sistema recusa a ficha que não sabe cobrar | fichas dos 6 contratos e a validação |
| 2. Base viva | o RH envia arquivo ou usa o portal; o sistema guarda quando cada mudança chegou | uso o histórico como está |
| 3. Pré-fechamento | o sistema apura e mostra os avisos | protótipo |
| 4. Fechamento | o financeiro aprova; a contagem e a ficha ficam gravadas | o protótipo calcula; não grava nem tem aprovação |
| 5. Nota com extrato | emissão com a lista de pessoas e a regra | protótipo (arquivo das notas para emitir) |
| 6. Contestação | o cliente e o CS consultam o extrato | protótipo (o caso da Aurora) |
| 7. Acerto | o que o contrato manda compensar entra como item de uma nota seguinte | protótipo (o pré-pago da Bravo) |
| 8. Pagamento | vencimento, baixa e conciliação | fora: o kit não tem dado de pagamento |

**Sobre a última etapa.** Não construí nada de pagamento, porque o kit não traz nenhum dado sobre isso e o que eu fizesse seria inventado. Mas a proposta toca nela por um caminho indireto. O RH da Aurora diz: "quero entender essa diferença antes de pagar". Uma nota que o cliente não entende é uma nota que espera, e a nota explicada ataca essa causa. Para fechar o caminho, o sistema precisaria guardar o estado de cada nota (emitida, contestada, paga) e o vencimento. Com esse dado, eu mediria quantas notas são contestadas e quantos dias levam para ser pagas, antes e depois do extrato.

## 6. As minhas escolhas de escopo

O enunciado deixa comigo por onde começar, o que aprofundar e o que deixar de fora, e pede o porquê.

- **Comecei pela contagem.** É onde os dados mostram o problema, e é o único trecho do caminho em que o kit permite conferir a resposta, porque traz as notas emitidas.
- **Aprofundei a conta e a explicação da nota.** As quatro falas do enunciado pedem isso, cada uma de um lado.
- **Deixei de fora:**
  - **Emissão fiscal, boleto e integração com ERP.** Vêm depois do número certo.
  - **Pagamento e conciliação.** O kit não tem esse dado (seção 5).
  - **Aprovação e gravação do fechamento.** O protótipo calcula e mostra; não grava.
  - **Renegociar contratos.** Sigo os contratos como estão; onde o texto deixa dúvida, a dúvida vira pergunta (seção 8).
  - **IA dentro do fechamento.** Foi uma escolha, explicada na seção 10.

## 7. Por onde a Medipreço começaria

Se a proposta fosse adotada, eu não mudaria a cobrança de ninguém no primeiro dia. A ordem seria:

1. **Explicar as notas de hoje.** Entregar o extrato sobre o método atual. Atende o RH e o CS de imediato, aponta erros como o dos 499 e não muda o valor de ninguém.
2. **Calcular pelo contrato em paralelo.** Mostrar, cliente a cliente, a diferença entre o faturado e o contratado, e responder as dúvidas da seção 8.
3. **Virar a cobrança.** Contrato por contrato, com o cliente avisado.

O primeiro passo não mexe em dinheiro. Os outros dois mexem em dinheiro e em relacionamento, e por isso vêm depois.

## 8. O que os contratos não fecham

Ao transformar os contratos em fichas, encontrei pontos em que o texto não basta para calcular. Não deu tempo de perguntar à Medipreço antes da entrega. Em cada ponto adotei uma interpretação, que fica escrita na ficha e aparece na própria nota. Se a resposta da Medipreço for outra, muda a ficha do contrato, e não o programa.

| Onde | O que eu perguntaria | O que o protótipo faz hoje |
|---|---|---|
| Delta, 7.1 | Ao passar de 5.000 vidas, o preço menor vale para todas as vidas ou só para as excedentes? | Para todas, como na nota de agosto (R$ 9,00 sobre as 5.051 vidas). |
| Delta, 7.1 e 7.2 | A faixa se escolhe pela quantidade cobrada no mês ou pelo tamanho da base? Em outubro a base nunca passou de 4.941 vidas, mas 5.105 pessoas estiveram ao menos um dia. | Pela quantidade cobrada: 5.105 a R$ 9,00. Pelo tamanho da base seriam 5.105 a R$ 10,00, R$ 51.050. |
| Delta, 7.2 | Vida com saída informada só no mês seguinte conta para a faixa? | Conta, enquanto está cadastrada. |
| Delta, 7.2 e 7.3 | Qual é a regra para uma carga errada que o suporte desfaz? | Não cobra as 600 entradas de 07/10, desfeitas com a mesma data. |
| Cedro, 6.3 | Quando alguém muda de empresa dentro do grupo no meio do mês, em que dia se mede a proporção de cada empresa? | No dia do máximo, com aviso na nota. Só importa nesse caso. |
| Bravo, 4.4 | "Efetivamente ativo" é quem esteve ativo em algum dia do mês, ou quem está ativo no dia da contagem? | Quem esteve ativo em algum dia. A outra interpretação fica calculada e à vista. |
| Estrela, 5.3 | Qual é a consequência de informar fora dos 5 dias úteis? | Nenhuma: vale a base cadastrada no dia 26. |
| Todos | A Medipreço registra quando o arquivo do RH chega? | Usa a data em que a mudança entrou no sistema. |

### O acerto da Bravo, que hoje não é feito

Este é o ponto em que mais precisei interpretar, e por isso explico em separado.

A Bravo paga antecipado. A nota de setembro, por exemplo, é emitida em 27 de agosto, com os titulares que estavam na base no dia 26. Como ninguém sabe em agosto quantos titulares estarão ativos em setembro, a cláusula 4.4 manda compensar na nota seguinte a diferença entre os titulares cobrados e os "efetivamente ativos no mês". Nenhuma das quatro notas emitidas da Bravo traz esse acerto.

A cláusula é ambígua em dois pontos. Não define o que é "efetivamente ativo". E manda acertar o mês numa nota que sai no dia 27, antes de o mês acabar. O protótipo calcula o acerto de duas formas e mostra as duas na nota:

- **A que adotei: quem esteve ativo em qualquer dia do mês paga o mês inteiro.** Quem entra depois da cobrança é cobrado na nota seguinte. Quem entra nos últimos dias do mês, depois do dia 26, é cobrado num ajuste, uma nota adiante; esse ajuste é premissa minha, porque o contrato não trata desses dias. Quem sai no meio do mês não recebe crédito, porque o contrato cobra valor mensal, sem proporcional. Os acertos ficam em R$ 345,00 na nota de setembro, R$ 180,00 na de outubro e R$ 165,00 na de novembro.
- **A outra: a foto do dia 26.** O acerto é a diferença entre a contagem desta nota e a da anterior. Os acertos ficam em R$ 165,00, R$ 75,00 e R$ 150,00.

As duas dão o mesmo resultado para quem fica o mês inteiro e só divergem para quem entra ou sai no meio do ciclo. Adotei a primeira porque é a mais fiel ao texto, que fala em mês e não em dia. Ela também é a mais favorável à Medipreço, e portanto a mais sujeita a contestação. Por isso a nota mostra a adotada em destaque e a outra ao clicar, e a ficha do contrato escolhe qual vale. Antes de usar de verdade, eu confirmaria com o financeiro o que já foi combinado com o cliente, que pesa mais do que a minha interpretação.

### As outras interpretações adotadas

- **O proporcional da Faro é por dias corridos do mês** (cláusula 4.2).
- **Carga desfeita não é cobrada.** O suporte registrou as 600 saídas da Delta com a data da própria carga.
- **Quem muda de empresa dentro do grupo conta uma vez só.** Em outubro, 126 pessoas passaram da Cedro Lojas Sul para a Cedro Distribuição. O aviso sobre a divisão entre as empresas aparece só nesse mês, com os dois valores possíveis.
- **Quando o dia 26 cai em fim de semana, a contagem recua para a sexta, às 9h.** É o que as contagens de 24/07 e 25/09 fizeram.

## 9. O que construí

O enunciado pede algo funcionando. Construí um protótipo que roda no computador, só com Python, sobre os dados do kit.

- **As fichas de regras** (`prototipo/contratos.json`): os seis contratos descritos pelas mesmas cinco escolhas, com o número das cláusulas e as interpretações adotadas.
- **O cálculo** (`prototipo/motor.py`): fecha agosto, setembro e outubro para os seis clientes em menos de um segundo. Não tem regra escrita para nenhum cliente; tudo o que é específico está na ficha. Recusa a ficha que não sabe calcular.
- **A lista do mês:** a tela do financeiro. Mostra as notas de todos os clientes, os avisos para conferir e o arquivo das notas para emitir.
- **A nota explicada:** a tela do RH e do CS. Mostra a regra, a conta passo a passo, as pessoas cobradas, o que mudou desde o mês anterior e o que chegou depois da contagem. Onde a cobrança de hoje difere do contrato, aponta o número da cláusula.
- **"O que dá para vender":** a página do comercial. Lista as combinações de contrato que o sistema cobra, as que recusa e o motivo.
- **Os testes** (`prototipo/testes.py`): 50 conferências automáticas. As principais: contando como o financeiro contou, o programa chega à quantidade cobrada em 27 dos 28 itens de nota emitidos (o outro é o erro dos 499 da Bravo); e o cálculo pela regra do contrato bate com uma segunda conta, feita em separado em SQL.

**Limites do protótipo.** Ele foi feito para os dados do kit, e testei o que acontece com meses novos, simulados:

- **As regras aguentam.** Em novembro e dezembro simulados, os valores de Aurora, Estrela, Delta, Faro e Cedro bateram com uma conta separada, e as notas de agosto a outubro não mudaram.
- **Os meses estão fixos no código.** Um mês novo não aparece sem ajuste em `motor.py`, e as telas e os testes pressupõem que o mês tem nota emitida para comparar.
- **O calendário de feriados só cobre 2026.**
- **Dado inconsistente para o cálculo de todos os clientes** (pessoa ou CNPJ desconhecido, saída de quem não está ativo), com erro técnico em vez de aviso.
- **Cliente que está na base e não tem ficha fica de fora sem aviso.**
- **Toda saída registrada pelo suporte é tratada como carga desfeita.** A regra veio de um único caso, o da Delta. Uma saída comum registrada pelo suporte tiraria a pessoa também das notas passadas, o que contraria a escolha central. Num sistema real, a anulação precisa de uma marca própria.

Nas telas, a comparação entre o que foi faturado e o que o contrato manda fica numa caixa à parte. Ela é a evidência do diagnóstico, e não faz parte do produto que proponho.

## 10. Como usei a IA

O relato completo, com os erros da IA e o que eu corrigi, está em `docs/uso-de-ia.md`. Em resumo:

- **No processo.** Conduzi o trabalho com o Claude Code do começo ao fim. Eu decidi em cada etapa. A IA leu o kit, escreveu as consultas, o código e os textos, e sugeriu quando pedi.
- **Na solução.** A IA não entra, e isso foi uma escolha. O cálculo é código comum, porque o número de uma nota tem que sair igual toda vez. A interpretação do contrato é decisão de uma pessoa: numa carteira com muitos contratos, um erro de leitura de um modelo vira cobrança errada todo mês. No máximo, a IA ajuda essa pessoa como assistente; nunca decide.
