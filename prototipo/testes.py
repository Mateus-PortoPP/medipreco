"""Como sabemos que o motor está certo.

Uso:  python3 prototipo/testes.py

Quatro grupos de conferência:
  A. O motor entende a base: reconstrói a situação de hoje e as notas já emitidas.
  B. O cálculo pela regra do contrato bate com uma segunda conta, feita em SQL, de forma independente.
  C. As contas fecham por dentro (pessoas somam a quantidade, itens somam a nota, rateio soma o total).
  D. O resultado serve a quem vai usar (financeiro, RH do cliente, CS, comercial).
"""
import json
import sqlite3
import sys

import motor

dados = motor.carregar()
config = json.loads(motor.FICHAS.read_text(encoding="utf-8"))
conv, fichas = config["convencoes"], {f["cliente"]: f for f in config["contratos"]}
periodos = motor.montar_periodos(dados)
resultado = motor.rodar()
fech = {(f["cliente"], f["competencia"]): f for f in resultado["fechamentos"]}
con = sqlite3.connect(motor.BANCO)

falhas = []


def conferir(nome, condicao, detalhe=""):
    print(("  ok     " if condicao else "  FALHOU ") + nome + (f"  [{detalhe}]" if detalhe else ""))
    if not condicao:
        falhas.append(nome)


# ------------------------------------------------------------------ A
print("\nA. O motor entende a base")

hoje = {(p["pessoa"], p["cnpj"]) for p in periodos if p["saiu"] is None}
vinculos = {(r[0], r[1]) for r in con.execute("select pessoa_id, cnpj from vinculos where ativo = 1")}
conferir("os períodos reconstruídos dão a mesma lista de ativos da tabela vinculos", hoje == vinculos,
         f"{motor.br_num(len(hoje))} ativos")

# método de hoje: contar a base no instante em que o financeiro contou
batem, nao_batem = 0, []
for n in dados["notas"]:
    meus = [p for p in periodos if p["cliente"] == n["cliente"]]
    base = motor.apurar_foto(meus, n["contagem_em"])
    if n["cliente"] == "Grupo Cedro":
        base = [l for l in base if l["cnpj"] == n["cnpj_tomador"]]
    if "Plano" in n["item"]:
        base = [l for l in base if n["item"].endswith(l["plano"])]
    if n["base_calculo"] == "titulares":
        base = [l for l in base if l["tipo"] == "titular"]
    if len(base) == n["quantidade"]:
        batem += 1
    else:
        nao_batem.append((n["cliente"], n["competencia"], n["quantidade"], len(base)))
conferir("contando a base em contagem_em, o motor reproduz 27 dos 28 itens de nota emitidos", batem == 27, f"{batem} de 28")
conferir("o único item que não bate é a Bravo de setembro (cobrou 499, a regra dá 332)",
         nao_batem == [("Bravo Tecnologia", "2026-09", 499, 332)], "; ".join(f"{c} {m}: cobrou {q}, a base dá {b}" for c, m, q, b in nao_batem))

datas_ok = all(fech[(n["cliente"], n["competencia"])]["emissao"] == n["data_emissao"] for n in dados["notas"])
conferir("a data de emissão calculada pela ficha é igual à data real das 28 notas", datas_ok)
fotos = [f for f in resultado["fechamentos"] if f["metodo"] == "foto"]
conferir("o instante da contagem calculado pela ficha é igual ao que o financeiro usou (contratos de foto)",
         all(f["instante"] == f["faturado"]["contagem_em"] for f in fotos), f"{len(fotos)} fechamentos")

# ------------------------------------------------------------------ B
print("\nB. O cálculo bate com uma segunda conta, feita em SQL")

con.executescript("""
create temp table iv as
with es as (select v.*, e.cliente,
                   lead(tipo_evento) over w pt, lead(data_processamento) over w pp, lead(origem) over w po
            from eventos v join empresas e using (cnpj) where tipo_evento in ('entrada', 'saida')
            window w as (partition by pessoa_id, cnpj order by data_processamento, evento_id))
select pessoa_id, cnpj, cliente, data_processamento pi, pp pf, coalesce(po = 'suporte_medipreco', 0) anulado
from es where tipo_evento = 'entrada';
create temp table dias as
with recursive d(dia) as (select '2026-08-01' union all select date(dia, '+1 day') from d where dia < '2026-10-31')
select dia, substr(dia, 1, 7) mes from d;
""")
no_fim = "i.pi <= d.dia || ' 23:59:59' and (i.pf is null or i.pf > d.dia || ' 23:59:59')"

sql_delta = dict(con.execute(f"""
    select d.mes, count(distinct i.pessoa_id) from dias d join iv i
      on i.cliente = 'Delta Benefícios' and i.anulado = 0 and {no_fim} group by d.mes"""))
for mes, vidas in sql_delta.items():
    esperado = vidas * (10 if vidas <= 5000 else 9 if vidas <= 10000 else 8)
    conferir(f"Delta {mes}: ao menos 1 dia, com faixa", fech[("Delta Benefícios", mes)]["total"] == esperado,
             f"{motor.br_num(vidas)} vidas, {motor.br_reais(esperado)}")

sql_faro = dict(con.execute(f"""
    select d.mes, round(11.0 * count(*) / (select count(*) from dias x where x.mes = d.mes), 2)
    from dias d join iv i on i.cliente = 'Faro Serviços' and i.anulado = 0 and {no_fim} group by d.mes"""))
for mes, valor in sql_faro.items():
    conferir(f"Faro {mes}: pró-rata por dias corridos", fech[("Faro Serviços", mes)]["total"] == valor, motor.br_reais(valor))

sql_cedro = dict(con.execute(f"""
    select mes, max(vidas) from (select d.mes, d.dia, count(distinct i.pessoa_id) vidas from dias d join iv i
      on i.cliente = 'Grupo Cedro' and i.anulado = 0 and {no_fim} group by d.mes, d.dia) group by mes"""))
for mes, vidas in sql_cedro.items():
    conferir(f"Cedro {mes}: máximo do mês", fech[("Grupo Cedro", mes)]["total"] == vidas * 8, f"{motor.br_num(vidas)} vidas, {motor.br_reais(vidas * 8)}")

# acerto do pré-pago (Bravo, 4.4): entra na nota seguinte. Quem esteve ativo em ao menos 1 dia do mês, do dia 1
# até a contagem da nota (dia 26), menos os cobrados antes, na contagem do mês anterior
con.execute("create temp table tit as select i.* from iv i join pessoas p using (pessoa_id) where p.tipo = 'titular' and i.cliente = 'Bravo Tecnologia' and i.anulado = 0")
for mes_do_acerto, cobrado_em, agora, na_nota in (("2026-08", "2026-07-24 09:00:00", "2026-08-26 09:00:00", "2026-09"),
                                                  ("2026-09", "2026-08-26 09:00:00", "2026-09-25 09:00:00", "2026-10"),
                                                  ("2026-10", "2026-09-25 09:00:00", "2026-10-26 09:00:00", "2026-11")):
    efetivos = con.execute(f"""select count(*) from (
        select i.pessoa_id from dias d join tit i on {no_fim} where d.mes = ? and d.dia || ' 23:59:59' < ?
        union select pessoa_id from tit where pi <= ? and (pf is null or pf > ?))""", (mes_do_acerto, agora, agora, agora)).fetchone()[0]
    cobrados = con.execute("select count(distinct pessoa_id) from tit where pi <= ? and (pf is null or pf > ?)", (cobrado_em, cobrado_em)).fetchone()[0]
    # o ajuste: quem entrou no mês anterior depois da contagem daquele mês (ativo em algum dia dele, e fora das duas contas)
    anterior = {"2026-08": "2026-07", "2026-09": "2026-08", "2026-10": "2026-09"}[mes_do_acerto]
    ajuste = con.execute(f"""select count(*) from (
        select i.pessoa_id from (select date('{anterior}-01', '+' || n || ' day') dia from (select 0 n union select 1 union select 2 union select 3
               union select 4 union select 5 union select 6 union select 7 union select 8 union select 9 union select 10 union select 11 union select 12
               union select 13 union select 14 union select 15 union select 16 union select 17 union select 18 union select 19 union select 20
               union select 21 union select 22 union select 23 union select 24 union select 25 union select 26 union select 27 union select 28
               union select 29 union select 30) where substr(date('{anterior}-01', '+' || n || ' day'), 1, 7) = '{anterior}') d
          join tit i on {no_fim}
        except select pessoa_id from tit where pi <= ?)""", (cobrado_em,)).fetchone()[0]
    nota = fech[("Bravo Tecnologia", na_nota)]
    esperado = efetivos - cobrados + ajuste
    conferir(f"Bravo: o acerto de {mes_do_acerto} entra na nota seguinte ({na_nota}) e bate com a segunda conta",
             nota["acerto"]["quantidade"] == esperado and nota["total"] == (nota["quantidade"] + esperado) * 15,
             f"{efetivos} efetivos − {cobrados} cobrados = {efetivos - cobrados:+d}; mais {ajuste} que entraram no fim de {anterior}: {motor.br_reais(esperado * 15)}")
    na_contagem = con.execute("select count(distinct pessoa_id) from tit where pi <= ? and (pf is null or pf > ?)", (agora, agora)).fetchone()[0]
    conferir(f"Bravo: a outra leitura (foto do dia da contagem) também é calculada para a nota de {na_nota}",
             nota["acerto_alternativo"]["quantidade"] == na_contagem - cobrados,
             f"{na_contagem} − {cobrados} = {na_contagem - cobrados:+d} titulares, {motor.br_reais((na_contagem - cobrados) * 15)}")
mes_cheio_sql = {m: con.execute(f"select count(distinct i.pessoa_id) from dias d join tit i on {no_fim} where d.mes = ?", (m,)).fetchone()[0]
                 for m in ("2026-08", "2026-09")}

for cliente in ("Aurora Logística", "Estrela Indústria"):
    conferir(f"{cliente}: pela regra do contrato, a nota emitida está certa nos três meses",
             all(fech[(cliente, m)]["diferenca"] == 0 for m in motor.COMPETENCIAS))

# ------------------------------------------------------------------ C
print("\nC. As contas fecham por dentro")

todos = resultado["fechamentos"]
conferir("em todo fechamento, a lista de pessoas tem o tamanho da quantidade cobrada",
         all(len(f["pessoas"]) == f["quantidade"] for f in todos))
conferir("ninguém aparece duas vezes na mesma nota",
         all(len({l["pessoa"] for l in f["pessoas"]}) == len(f["pessoas"]) for f in todos))
conferir("os itens somam o total de cada nota, e as notas somam o total do cliente",
         all(abs(sum(i["valor"] for n in f["notas"] for i in n["itens"]) - f["total"]) < 0.005 for f in todos))
cedro = fech[("Grupo Cedro", "2026-10")]
conferir("Cedro outubro: as três notas somam o valor do grupo, sem sobra de centavos",
         sum(n["total"] for n in cedro["notas"]) == cedro["quantidade"] * 8 and len(cedro["notas"]) == 3,
         " + ".join(motor.br_reais(n["total"]) for n in cedro["notas"]) + " = " + motor.br_reais(cedro["total"]))
transf = {m: len(fech[("Grupo Cedro", m)]["transferencias"]) for m in motor.COMPETENCIAS}
aviso_de_rateio = {m: any("divisão depende do dia" in a["titulo"] for a in fech[("Grupo Cedro", m)]["alertas"]) for m in motor.COMPETENCIAS}
conferir("Cedro: o aviso sobre o dia do rateio só aparece no mês em que alguém mudou de empresa (outubro, 126 pessoas)",
         transf == {"2026-08": 0, "2026-09": 0, "2026-10": 126} and aviso_de_rateio == {"2026-08": False, "2026-09": False, "2026-10": True},
         ", ".join(f"{m}: {n}" for m, n in transf.items()))
anulados = {p["pessoa"] for p in periodos if p["anulado"]}
conferir("nenhuma das 600 pessoas da carga desfeita aparece em nota",
         len(anulados) == 600 and not any(l["pessoa"] in anulados for f in todos for l in f["pessoas"]))
conferir("Bravo: só titulares na lista de cobrados",
         all(l["tipo"] == "titular" for f in todos if f["cliente"] == "Bravo Tecnologia" for l in f["pessoas"]))
conferir("Estrela: quantidade acima de 500 nos três meses, então sem complemento de mínimo",
         all(fech[("Estrela Indústria", m)]["quantidade"] >= 500 for m in motor.COMPETENCIAS))

# o mínimo funciona quando a base cai: simulação com a base de hoje (475)
base_hoje = motor.apurar_foto([p for p in periodos if p["cliente"] == "Estrela Indústria"], "2026-11-12 23:59:59")
itens = motor.precificar(fichas["Estrela Indústria"], base_hoje, [])
conferir("Estrela com a base de hoje (475): o mínimo gera um item de complemento de 25 vidas e a nota dá R$ 4.750,00",
         len(base_hoje) == 475 and itens[1]["quantidade"] == 25 and round(sum(i["valor"] for i in itens), 2) == 4750.00)

# ------------------------------------------------------------------ D
print("\nD. O resultado serve a quem vai usar")

bravo = fech[("Bravo Tecnologia", "2026-09")]
conferir("Financeiro: comparado com a nota emitida, o motor aponta o erro dos 499 da Bravo (contando pela ficha, ele não acontece)",
         any(a["nivel"] == "erro" for a in bravo["alertas"]), bravo["alertas"][0]["titulo"])
conferir("Financeiro: toda diferença entre a nota emitida e o contrato aponta o número da cláusula, e a cláusula existe no contrato",
         all(f["clausulas_em_jogo"] for f in todos if f["diferenca"])
         and all(n in fichas[f["cliente"]]["clausulas"] for f in todos for n in f["clausulas_em_jogo"]),
         "; ".join(sorted({f"{f['cliente'].split()[-1]} {', '.join(f['clausulas_em_jogo'])}" for f in todos if f["clausulas_em_jogo"]})))
conferir("Financeiro: os únicos fechamentos sem nenhuma diferença são os de contratos de foto",
         {f["metodo"] for f in todos if f["diferenca"] == 0} == {"foto"})

# o arquivo que o financeiro leva para emitir
import csv
import io
import gerar_site
linhas = list(csv.DictReader(io.StringIO(gerar_site.arquivo_das_notas("2026-10", todos, fichas).lstrip("\ufeff")), delimiter=";"))
em_reais = lambda texto: float(texto.replace(",", "."))
outubro = [f for f in todos if f["competencia"] == "2026-10"]
conferir("Financeiro: o arquivo de outubro tem as 8 notas, e os itens somam o valor do mês",
         len({l["cnpj_tomador"] for l in linhas}) == 8 == sum(len(f["notas"]) for f in outubro)
         and abs(sum(em_reais(l["valor_item"]) for l in linhas) - sum(f["total"] for f in outubro)) < 0.005,
         f"{len(linhas)} linhas, {motor.br_reais(sum(em_reais(l['valor_item']) for l in linhas))}")

aurora = fech[("Aurora Logística", "2026-10")]
saidas = [e for e in aurora["depois_da_contagem"] if e["evento"] == "saida"]
conferir("RH da Aurora: 737 cobradas, 19 saídas cadastradas depois da contagem, 718 no fim do mês",
         aurora["quantidade"] == 737 and len(saidas) == 19 and aurora["base_no_fim_do_mes"] == 718
         and aurora["quantidade"] - len(saidas) == aurora["base_no_fim_do_mes"])
conferir("RH da Aurora: 14 das 19 saídas tinham data de desligamento anterior ao dia 26",
         sum(e["data_informada"] < "2026-10-26" for e in saidas) == 14)

conferir("CS: em toda nota, quantidade anterior + entraram − saíram = quantidade atual",
         all(f["comparacao"]["quantidade_anterior"] + len(f["comparacao"]["entraram"]) - len(f["comparacao"]["sairam"])
             == f["quantidade"] for f in todos))

# "Vou conseguir cobrar antes de prometer?" O motor recusa, com o motivo, o que ele não sabe calcular.
conferir("Comercial: as seis fichas do kit são cobráveis", all(motor.validar(f) == [] for f in fichas.values()))


def modelo(base, competencia="2026-10", **mudancas):
    """Um contrato do kit com uma peça trocada: um modelo que ninguém comprou ainda."""
    return motor.fechar({**fichas[base], **mudancas}, competencia, periodos, dados, conv)


# peças fora do contrato em que nasceram, conferidas contra uma conta que não depende do motor
sem_acerto = {"acerto": None, "emissao": {"tipo": "primeiro_dia_util", "mes": "seguinte"}}
conferir("Comercial: por titular com 'ao menos 1 dia' conta só titulares, e bate com a segunda conta em SQL",
         all(modelo("Bravo Tecnologia", m, apuracao={"metodo": "ao_menos_um_dia"}, **sem_acerto)["quantidade"] == q for m, q in mes_cheio_sql.items()),
         ", ".join(f"{m}: {q}" for m, q in mes_cheio_sql.items()))
por_dia = {}
for m in motor.COMPETENCIAS:
    f = modelo("Grupo Cedro", m, apuracao={"metodo": "foto", "dia": 26, "mes": "referencia"}, notas={"tipo": "por_cnpj"})
    por_dia.update({(m, n["cnpj"]): n["itens"][0]["quantidade"] for n in f["notas"]})
emitidas = {(n["competencia"], n["cnpj_tomador"]): n["quantidade"] for n in dados["notas"] if n["cliente"] == "Grupo Cedro"}
conferir("Comercial: nota por CNPJ com contagem num dia reproduz as 9 notas que o Cedro recebeu de verdade", por_dia == emitidas, f"{len(emitidas)} notas")
f = modelo("Grupo Cedro", preco={"tipo": "faixa", "faixas": [{"ate": 500, "valor": 10.0}, {"ate": None, "valor": 8.0}]})
conferir("Comercial: nota por CNPJ com faixa usa a faixa do grupo inteiro em todas as empresas, e as notas somam o grupo",
         {i["unitario"] for n in f["notas"] for i in n["itens"]} == {8.0} and f["total"] == f["quantidade"] * 8.0,
         f"{f['quantidade']} vidas no grupo, {motor.br_reais(f['total'])}")


def recusa(nome, base, **mudancas):
    ficha = {**fichas[base], **mudancas}
    motivos = motor.validar(ficha)
    try:
        motor.fechar(ficha, "2026-10", periodos, dados, conv)
        calculou = True
    except motor.FichaInvalida:
        calculou = False
    conferir(f"Comercial: recusa {nome}, em vez de calcular errado", bool(motivos) and not calculou,
             motivos[0].split(";")[0] if motivos else "passou na validação")


uma_faixa = {"tipo": "faixa", "faixas": [{"ate": 500, "valor": 10.0}, {"ate": None, "valor": 8.0}]}
recusa("nota por CNPJ com mínimo (quem paga o complemento?)", "Grupo Cedro", minimo_vidas=1000)
recusa("pró-rata com faixa de preço", "Faro Serviços", preco=uma_faixa)
recusa("mínimo com preço por plano", "Aurora Logística", minimo_vidas=1000)
recusa("mínimo com pró-rata", "Faro Serviços", minimo_vidas=500)
recusa("método de apuração que não existe", "Faro Serviços", apuracao={"metodo": "media_do_mes"})
recusa("faixas fora de ordem", "Delta Benefícios",
       preco={"tipo": "faixa", "faixas": [{"ate": 10000, "valor": 9.0}, {"ate": 5000, "valor": 10.0}, {"ate": None, "valor": 8.0}]})
try:
    motor.precificar(fichas["Aurora Logística"], [{"plano": "Ouro"}], [])
    sem_preco = False
except motor.FichaInvalida:
    sem_preco = True
conferir("Comercial: recusa pessoa em plano que não tem preço na ficha", sem_preco)

fonte = (motor.RAIZ / "motor.py").read_text(encoding="utf-8")
conferir("Comercial: o motor não tem regra escrita para nenhum cliente; tudo vem da ficha",
         not any(nome.split()[0] in fonte for nome in fichas))

print(f"\n{'TUDO CERTO' if not falhas else 'FALHAS: ' + str(len(falhas))}")
sys.exit(1 if falhas else 0)
