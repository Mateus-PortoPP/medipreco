# Como usei a IA

Conduzi o trabalho com o Claude Code do começo ao fim. Eu decidi em cada etapa: o que investigar, como ler cada contrato, o que construir e o que deixar de fora. A IA executou (leitura do kit, consultas, código e redação) e trouxe sugestões quando pedi. Nenhuma sugestão virou decisão sem eu aceitar, e várias eu recusei.

## O que a IA executou, sob a minha direção

- **Leitura do kit.** Leu os seis contratos e a base e montou a comparação entre como cada cliente paga e como a Medipreço cobra hoje.
- **Investigação dos dados.** Escreveu as consultas em SQL do `analise/analise.ipynb`. Foi assim que apareceu que 27 dos 28 itens de nota são a mesma contagem da base às 9h do dia de corte, e que o item que não bate é a Bravo de setembro.
- **Código.** Escreveu o `motor.py`, o `testes.py` e o `gerar_site.py`, e a ficha de regras em `contratos.json`.
- **Texto.** Redigiu a proposta, o roteiro e este arquivo a partir das decisões que eu tomei.

## O que eu decidi

- **Aurora e Estrela: a cobrança está certa.** A IA tratava "posição da base no dia 26" como ambígua e sugeria crédito ao cliente. Li as cláusulas 4.1 e 5.3 e concluí que vale a base cadastrada no dia 26. O problema dessas duas é explicação, não valor.
- **Base cadastrada para todos os contratos**, e não a data que o RH declarou.
- **Faro:** pró-rata por dias corridos do mês.
- **Cedro:** rateio pelas vidas de cada empresa no dia do máximo, com aviso na tela, porque o contrato não define o momento.
- **Bravo 4.4:** primeiro decidi não calcular o acerto, porque o contrato não diz como contar o "efetivo". Depois li a cláusula junto com a 4.3 e a 3.2: o pagamento é antecipado e a empresa deve divulgar o programa, então entram titulares depois da cobrança, e o acerto existe para cobrá-los. Efetivamente ativo é quem esteve cadastrado em ao menos 1 dia do mês. Considerei a cláusula ambígua e escrevi a regra com as duas leituras (mês cheio por qualquer dia ativo, que adotei, e foto do dia 26), os casos em que elas divergem e as limitações da que escolhi. O protótipo calcula as duas e mostra a alternativa na própria nota.
- **Duas telas, não quatro.** A IA propôs uma tela por público. O RH e o CS fazem a mesma pergunta. O comercial ganhou depois uma página própria, porque a pergunta dele vem antes de existir nota.

## Como conferi o que a IA produziu

- **Duas contas independentes.** O motor em Python e o notebook em SQL calculam Delta, Faro e Cedro separadamente, e os valores são idênticos.
- **Reprodução do passado.** Contando a base como o financeiro contou, o motor reproduz 27 dos 28 itens de nota já emitidos.
- **Testes.** `python3 prototipo/testes.py` roda 50 conferências.
- **Uma revisão geral.** Pedi que tudo o que tinha sido decidido fosse reconferido contra o contrato e os dados e separado em três grupos: visto, interpretação e suposição.
- **Uma regra de trabalho.** Só vira regra de cálculo o que tem apoio no texto do contrato ou nos dados. O que é inventado sai ou vira pergunta à Medipreço.

## Onde a IA errou

- **Números.** A primeira análise tinha cinco números errados ou imprecisos, entre eles o divisor do pró-rata da Faro e a contagem de saídas da Aurora. Foram achados na reconferência.
- **Premissa escondida.** Todos os valores "pelo contrato" de Faro, Cedro e Delta estavam calculados pela data informada pelo RH, sem ninguém ter decidido isso. Era o oposto do que eu tinha adotado para a Aurora. Apareceu na revisão geral, e os números foram recalculados.
- **Certeza demais.** Disse que a cláusula 5.2 da Aurora "fechava a questão". Ela fala em "colaborador ativo" e admite outra leitura. A decisão ficou como premissa declarada.
- **Regra sem apoio.** Registrou como decidido um rateio do Cedro por dias de cada pessoa, que não está no contrato. Saiu.
- **Palavra errada.** Chamou de "atraso" o arquivo mensal da Delta. O contrato da Delta não dá prazo; só o da Estrela dá.
- **Correção exagerada.** Depois da regra de não inventar, passou a aceitar só o texto literal do contrato. Os dados também são apoio.
- **Conclusão forte demais.** Escreveu que "a Delta é onde está o dinheiro", como se a Medipreço tivesse cobrado R$ 3 mil a mais. Desconfiei dos números de outubro e pedi a análise: a conta estava certa, mas o resultado depende da leitura, e 192 das vidas contadas tinham saído em setembro. A afirmação foi trocada pela tabela das quatro leituras.
- **Acerto no mês errado.** Ao calcular o acerto do pré-pago da Bravo, a IA pôs o acerto de agosto na nota de outubro, argumentando que em 27/08 o mês ainda não tinha acabado. Reli as cláusulas 4.3 e 4.4: a nota é contada no dia 26 e o acerto vai "na nota fiscal seguinte". O de agosto entra na nota de setembro, com o que se sabe no dia 26.
- **Cautela demais.** A primeira versão da página do comercial dizia que o sistema cobrava 18 de 96 modelos. Estranhei o número: boa parte das recusas era restrição que a IA tinha posto sem necessidade. Depois de revistas, são 44.
- **Escopo.** Propôs quatro telas, uma simulação de métodos e um alerta de variação acima de 10%, com limite inventado. Ficaram duas telas, e o resto saiu.

O padrão: a IA erra menos na conta e mais ao tratar uma suposição como fato. O que funcionou foi exigir, para cada afirmação, a cláusula ou a consulta que a sustenta.

## A IA dentro do fechamento da Medipreço

Usei IA para construir tudo isto, mas o que proponho não tem IA rodando. Foi uma escolha minha.

- **No cálculo, não entra.** O número de uma nota tem que sair igual toda vez que se roda. O motor é código comum, sem modelo e sem chamada a nenhuma API de IA.
- **Na leitura dos contratos, quem decide é uma pessoa.** Numa carteira real há muito mais contratos do que os seis do kit. Deixar um modelo interpretar cada um é sujeito a erro, e em contrato não dá para arriscar: um erro de leitura vira cobrança errada todo mês. A ficha de regras é preenchida e aprovada por uma pessoa, que responde por ela.
- **O máximo que eu aceitaria** é a IA como assistente e executora dessa pessoa, do jeito que usei neste trabalho: ela ajuda a ler, a conferir e a escrever, e nunca decide.

Este próprio trabalho mostra o motivo. Com seis contratos, a IA tratou suposição como fato mais de uma vez (lista acima), e só não virou número errado porque havia alguém conferindo cada leitura contra a cláusula.
