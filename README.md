# O fechamento do mês — case AI Builder, Medipreço

A ficha de regras de cada contrato calcula a nota, e a nota mostra de onde veio cada número.

## Como rodar

**Precisa de:** Python 3.9 ou mais novo. Não instala nenhum pacote.

Para conferir se você tem: `python3 --version`. No Mac, se o comando pedir para instalar as ferramentas de linha de comando, aceite; é o próprio Python da Apple. No Windows, use `python` ou `py` no lugar de `python3`.

**1. Entre na pasta do projeto**

```
cd medipreco
```

**2. Ponha a base do kit no lugar**

Os dados do case não estão no repositório. Copie o `base.sqlite` do zip do case para a pasta `dados/`:

```
mkdir -p dados
cp /caminho/do/kit/base.sqlite dados/
```

**3. Suba o protótipo**

```
python3 prototipo/servidor.py
```

O navegador abre sozinho em `http://localhost:8000`. Se a porta 8000 estiver ocupada, ele usa a próxima livre e mostra no terminal qual é. Se o navegador não abrir, copie o endereço que aparece no terminal.

**4. O que experimentar** (uns 5 minutos)

- **Lista do mês:** as notas de outubro de todos os clientes, calculadas agora. A barra escura no topo mostra quando o cálculo rodou e quanto levou.
- **Baixar as notas para emitir:** o arquivo que o financeiro leva para a emissão, uma linha por item. Abre direto na planilha.
- **Uma nota:** clique em Aurora Logística. A nota mostra a regra, a conta, as 737 pessoas cobradas e as 19 saídas que chegaram depois da contagem.
- **O que dá para vender:** o botão no canto do topo. É a página do comercial: os modelos de cobrança que o sistema sabe calcular, os que recusa e por quê.
- **Um contrato que o sistema não sabe cobrar:** abra `prototipo/contratos.json` e, na Faro Serviços, troque `"minimo_vidas": null` por `"minimo_vidas": 500` (mínimo num contrato pró-rata). Salve e recarregue a página: o protótipo para e diz o motivo, em vez de calcular errado. Desfaça a troca depois.
- **Rodar as conferências:** o botão no topo roda os 50 testes e mostra o resultado na tela.

**5. Para parar:** Ctrl+C no terminal.

### Sem o servidor

Os mesmos passos pelo terminal:

```
python3 prototipo/motor.py        # o fechamento de agosto a outubro, cliente por cliente
python3 prototipo/testes.py       # as 50 conferências; termina com TUDO CERTO
python3 prototipo/gerar_site.py   # grava as telas em prototipo/site/, para abrir sem servidor
```

## O que tem aqui

```
docs/
  PROPOSTA.md        a proposta
  uso-de-ia.md       como a IA foi usada, o que eu decidi e onde ela errou
prototipo/
  servidor.py        o protótipo no navegador
  motor.py           o cálculo
  contratos.json     a ficha de regras dos seis contratos
  gerar_site.py      as telas: a lista do mês, a nota explicada e a página do comercial
  testes.py          as conferências do cálculo
  site/assets/       os logos usados nas telas
analise/
  analise.ipynb      a investigação dos dados, em SQL
requirements.txt     os pacotes do notebook
```

A base do kit fica em `dados/`, que não vem no repositório (passo 2).

O protótipo não precisa de nenhum pacote. O `requirements.txt` é só para o notebook, que é opcional:

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
