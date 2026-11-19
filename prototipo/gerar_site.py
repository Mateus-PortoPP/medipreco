"""Gera as telas do protótipo a partir do cálculo do motor.

Uso:  python3 prototipo/gerar_site.py     (grava as telas em prototipo/site/; abra index.html)

Dois tipos de página, sem JavaScript:
  - a lista do mês: todos os clientes, o valor de cada nota e o que precisa de atenção;
  - a nota explicada: a regra, a conta, as pessoas e o que mudou.
E um arquivo por mês com as notas prontas para emitir (notas-AAAA-MM.csv).
"""
import csv
import io
import unicodedata
from html import escape
from pathlib import Path

import motor
from motor import br_data, br_data_hora, br_mes, br_num, br_reais

SITE = motor.RAIZ / "site"

METODO = {"foto": "Base no dia de contagem", "maximo_do_mes": "Maior número do mês",
          "ao_menos_um_dia": "Ao menos 1 dia no mês", "pro_rata": "Pró-rata por dia"}
APOIO = {"contrato": ("Texto do contrato", "apoio-contrato"), "dados": ("Apoiado nos dados", "apoio-dados"),
         "pergunta": ("O contrato não define", "apoio-pergunta")}
NIVEL = {"erro": "Erro", "atencao": "Atenção", "info": "Aviso"}

CSS = """
:root{--navy:#0e2841;--deep:#081420;--ciano:#00c2ff;--ciano-cta:#0080a8;--ciano-texto:#00688c;--surface:#f4f8fd;
--borda:#d7e0ea;--escuro:#4a5a68;--claro:#8c9aa6;--erro:#b3261e;--branco:#fff;--ambar:#8a5a00;--ambar-bg:#fff6e0;
--erro-bg:#fdecea;--ciano-bg:#e3f6fd}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--navy);font:16px/1.55 "Manrope",ui-sans-serif,system-ui,sans-serif;
font-variant-numeric:tabular-nums}
a{color:var(--ciano-texto);font-weight:600;text-decoration:none}a:hover{text-decoration:underline}
header{background:var(--navy);color:var(--branco)}
.topo{max-width:1120px;margin:0 auto;padding:18px 24px;display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.topo img{height:30px;width:auto;display:block}
.topo .produto{font-size:14px;color:#c9d6e3;border-left:1px solid #ffffff33;padding-left:20px}
.topo nav{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}
.pilula{display:inline-block;padding:6px 16px;border-radius:999px;font-size:14px;font-weight:600;color:var(--branco);
border:1px solid #ffffff40}
.pilula.ativa{background:var(--ciano);color:var(--navy);border-color:var(--ciano)}
.pilula.outra{border-style:dashed;margin-left:12px}
.capa{background:var(--navy);color:var(--branco)}
.capa div{max-width:1120px;margin:0 auto;padding:8px 24px 36px}
.capa h1{font-size:36px;line-height:1.15;margin:0 0 6px;font-weight:700}
.capa p{margin:0;color:#c9d6e3;max-width:70ch}
.capa a{color:var(--ciano)}
main{max-width:1120px;margin:0 auto;padding:28px 24px 64px}
h2{font-size:22px;line-height:1.25;margin:40px 0 6px}
h2+p.sub{margin:0 0 16px;color:var(--escuro);max-width:75ch}
h3{font-size:16px;margin:20px 0 8px}
.cartao{background:var(--branco);border:1px solid var(--borda);border-radius:16px;padding:20px 24px;
box-shadow:0 1px 2px #0e28410f,0 10px 24px -14px #0e28412e}
.blocos{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin-top:-28px}
.bloco .rotulo{font-size:14px;color:var(--escuro);font-weight:600}
.bloco .valor{font-size:28px;font-weight:700;line-height:1.2;margin-top:2px}
.bloco .nota{font-size:14px;color:var(--escuro)}
.tabela{width:100%;border-collapse:collapse;font-size:15px}
.tabela th{text-align:left;font-size:13px;color:var(--escuro);font-weight:600;padding:8px 12px;border-bottom:2px solid var(--borda);
white-space:nowrap}
.tabela td{padding:10px 12px;border-bottom:1px solid var(--borda);vertical-align:top}
.tabela tr:last-child td{border-bottom:0}
.tabela .num{text-align:right;white-space:nowrap}
.tabela tfoot td{font-weight:700;border-top:2px solid var(--borda)}
.rolagem{overflow-x:auto}
.selo{display:inline-block;padding:2px 10px;border-radius:999px;font-size:13px;font-weight:600;white-space:nowrap}
.selo.erro{background:var(--erro-bg);color:var(--erro)}.selo.atencao{background:var(--ambar-bg);color:var(--ambar)}
.selo.info{background:var(--ciano-bg);color:var(--ciano-texto)}.selo.ok{background:#eef2f6;color:var(--escuro)}
.selo.apoio-contrato{background:#eef2f6;color:var(--navy)}.selo.apoio-dados{background:var(--ciano-bg);color:var(--ciano-texto)}
.selo.apoio-pergunta{background:var(--ambar-bg);color:var(--ambar)}
.aviso{border-left:4px solid var(--borda);padding:10px 16px;margin:10px 0;background:var(--branco);border-radius:0 12px 12px 0}
.aviso.erro{border-color:var(--erro);background:var(--erro-bg)}.aviso.atencao{border-color:#d99a00;background:var(--ambar-bg)}
.aviso.info{border-color:var(--ciano-cta);background:var(--ciano-bg)}
.aviso>strong:first-child{display:block}
.passos{margin:8px 0 0;padding-left:22px}.passos li{margin:4px 0}
.regra{font-size:18px;line-height:1.5;margin:0;max-width:70ch}
dl.clausulas{margin:8px 0 0}dl.clausulas dt{font-weight:700;margin-top:10px}dl.clausulas dd{margin:0;color:var(--escuro)}
details{margin-top:12px}summary{cursor:pointer;font-weight:600;color:var(--ciano-texto)}
.dois{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
.diagnostico{border:2px dashed var(--borda);background:transparent;box-shadow:none}
.diagnostico h2{margin-top:0}
.baixar{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin:20px 0 0;padding-top:16px;border-top:1px solid var(--borda)}
.baixar span{color:var(--escuro);font-size:13px}
.botao{display:inline-block;background:var(--ciano-cta);color:var(--branco);font-weight:600;font-size:14px;
  padding:9px 20px;border-radius:999px;text-decoration:none}
.botao:hover{background:var(--ciano-texto)}
.etiqueta{font-size:13px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--escuro)}
.migalha{font-size:14px;margin:0 0 8px}.migalha a{color:var(--ciano)}
.vizinhos{display:flex;justify-content:space-between;margin-top:32px;font-size:15px}
.mais{color:var(--erro)}.menos{color:var(--ciano-texto)}
footer{max-width:1120px;margin:0 auto;padding:0 24px 40px;color:var(--escuro);font-size:14px}
html{scroll-behavior:smooth}
[id]{scroll-margin-top:64px}
.trilho{position:sticky;top:0;z-index:5;background:var(--deep);color:#c9d6e3;font-size:14px;border-bottom:1px solid #ffffff1f}
.trilho>div{max-width:1120px;margin:0 auto;padding:0 24px;display:flex;align-items:center;gap:6px 20px;overflow-x:auto;white-space:nowrap}
.trilho a{color:#c9d6e3;font-weight:600;padding:12px 0;display:inline-block}
.trilho a:hover{color:var(--ciano);text-decoration:none}
.trilho .voltar{color:var(--ciano)}
.trilho .onde{color:var(--branco);font-weight:700;border-left:1px solid #ffffff33;padding-left:20px}
.trilho .secoes{display:flex;gap:18px;margin-left:auto}
.trilho .vizinho{border-left:1px solid #ffffff33;padding-left:20px;display:flex;gap:16px}
.clausula{display:inline-block;margin-left:8px;padding:1px 10px;border-radius:999px;font-size:13px;font-weight:700;
background:var(--navy);color:var(--branco);white-space:nowrap}
a.clausula:hover{background:var(--ciano-cta);text-decoration:none}
.aviso .clausulas{display:block;margin-top:6px;font-size:13px;color:var(--escuro)}
.aviso .clausulas .clausula{margin:0 6px 0 0}
dl.clausulas dt:target,dl.clausulas dt:target+dd{background:var(--ambar-bg);box-shadow:-8px 0 0 var(--ambar-bg),8px 0 0 var(--ambar-bg)}
details>.rolagem{max-height:440px;overflow:auto;border:1px solid var(--borda);border-radius:12px;margin-top:10px}
details>.rolagem .tabela thead th{position:sticky;top:0;background:var(--branco);box-shadow:0 2px 0 var(--borda)}
details[open]>summary{margin-bottom:2px}
.outras{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 0}
.outras a{border:1px solid var(--borda);border-radius:999px;padding:6px 16px;background:var(--branco);font-size:14px}
.outras a:hover{border-color:var(--ciano-cta);text-decoration:none}
.outras a.principal{background:var(--ciano-cta);color:var(--branco);border-color:var(--ciano-cta)}
"""


def slug(texto):
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower().replace(" ", "-")


def arquivo_nota(f):
    return f"nota-{slug(f['cliente'])}-{f['competencia']}.html"


def tabela(cabecalho, linhas, rodape=None):
    """cabecalho: lista de (título, é_número). linhas: lista de listas já em HTML."""
    th = "".join(f'<th class="{"num" if num else ""}">{escape(t)}</th>' for t, num in cabecalho)
    def tr(celulas):
        return "<tr>" + "".join(f'<td class="{"num" if cabecalho[i][1] else ""}">{c}</td>' for i, c in enumerate(celulas)) + "</tr>"
    corpo = "".join(tr(l) for l in linhas)
    pe = f"<tfoot>{tr(rodape)}</tfoot>" if rodape else ""
    return f'<div class="rolagem"><table class="tabela"><thead><tr>{th}</tr></thead><tbody>{corpo}</tbody>{pe}</table></div>'


def bloco(rotulo, valor, nota=""):
    return (f'<div class="cartao bloco"><div class="rotulo">{escape(rotulo)}</div><div class="valor">{valor}</div>'
            f'<div class="nota">{nota}</div></div>')


def clausulas(numeros, nota=""):
    """Os números das cláusulas, cada um levando ao texto dela na nota (sem repetir o texto aqui)."""
    return "".join(f'<a class="clausula" href="{nota}#clausula-{n.replace(".", "-")}">Cláusula {n}</a>' for n in numeros)


def aviso(a, link="", nota=""):
    no_contrato = (f'<span class="clausulas">No contrato: {clausulas(a["clausulas"], nota)}</span>'
                   if a.get("clausulas") else "")
    return (f'<div class="aviso {a["nivel"]}"><strong>{NIVEL[a["nivel"]]}: {escape(a["titulo"])}{link}</strong>'
            f'{escape(a["texto"])}{no_contrato}</div>')


def trilho(voltar, onde, secoes, vizinhos=()):
    """A faixa que acompanha a rolagem: de qualquer ponto da página dá para voltar, pular de seção ou trocar de mês."""
    return ('<nav class="trilho"><div>' + (f'<a class="voltar" href="{voltar[0]}">← {escape(voltar[1])}</a>' if voltar else "")
            + f'<span class="onde"{"" if voltar else " style=border:0;padding:0"}>{escape(onde)}</span><span class="secoes">'
            + "".join(f'<a href="#{i}">{escape(n)}</a>' for i, n in secoes) + '<a href="#topo">↑ Topo</a></span>'
            + ('<span class="vizinho">' + "".join(f'<a href="{h}">{escape(n)}</a>' for h, n in vizinhos) + "</span>" if vizinhos else "")
            + "</div></nav>")


def diferenca(v):
    """v = regra - faturado. Diz em palavras se o faturado ficou acima ou abaixo da regra."""
    if not v:
        return "igual"
    return f'<span class="{"mais" if v < 0 else "menos"}">{br_reais(abs(v))} {"a mais" if v < 0 else "a menos"}</span>'


BARRA = ""  # o servidor local preenche com o estado do cálculo; no site estático fica vazia


def pagina(titulo, capa, corpo, meses, mes_ativo, faixa=""):
    abas = "".join(f'<a class="pilula{" ativa" if m == mes_ativo else ""}" href="mes-{m}.html" '
                   f'title="Fechamento de {br_mes(m)}">{br_mes(m).split(" de ")[0].capitalize()}</a>' for m in meses)
    abas += f'<a class="pilula outra{" ativa" if mes_ativo == "vender" else ""}" href="vender.html">O que dá para vender</a>'
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(titulo)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body id="topo">
<header><div class="topo"><a href="index.html"><img src="assets/logo-branco.webp" alt="Medipreço"></a>
<span class="produto">Fechamento do mês</span><nav>{abas}</nav></div></header>
{BARRA}
{faixa}
<div class="capa"><div>{capa}</div></div>
<main>{corpo}</main>
<footer>Protótipo do case AI Builder. Todos os dados são fictícios. Linha do tempo: a base cadastrada no sistema.</footer>
</body></html>"""


# ---------------------------------------------------------------- a lista do mês

def lista_do_mes(mes, fechamentos, meses):
    do_mes = [f for f in fechamentos if f["competencia"] == mes]
    conferencia = [(f, a) for f in do_mes for a in f["alertas"] if not a["diagnostico"]]
    diagnostico = [(f, a) for f in do_mes for a in f["alertas"] if a["diagnostico"]]
    total = sum(f["total"] for f in do_mes)
    faturado = sum(f["faturado"]["total"] for f in do_mes)
    notas = sum(len(f["notas"]) for f in do_mes)

    capa = (f"<h1>Fechamento de {br_mes(mes)}</h1><p>As notas do mês, calculadas pela regra de cada contrato. "
            f"Abra uma nota para ver a conta e as pessoas por trás do número.</p>")
    blocos = '<div class="blocos">' + bloco("Valor do mês", br_reais(total), f"{len(do_mes)} clientes") + \
        bloco("Notas a emitir", str(notas), "uma por cliente; no grupo, uma por empresa") + \
        bloco("Para conferir antes de emitir", str(len(conferencia)), "avisos do sistema") + "</div>"

    linhas = []
    for f in do_mes:
        selos = "".join(f'<span class="selo {a["nivel"]}">{escape(a["titulo"])}</span> ' for a in f["alertas"] if not a["diagnostico"])
        linhas.append([f'<a href="{arquivo_nota(f)}">{escape(f["cliente"])}</a><br><span class="nota" style="color:var(--escuro);font-size:13px">{f["contrato"]}</span>',
                       METODO[f["metodo"]], br_num(f["quantidade"]), str(len(f["notas"])), br_reais(f["total"]),
                       selos or '<span class="selo ok">Sem avisos</span>'])
    corpo = blocos + '<h2 id="notas">Notas do mês</h2>' + '<div class="cartao">' + tabela(
        [("Cliente", 0), ("Como conta", 0), ("Quantidade", 1), ("Notas", 1), ("Valor", 1), ("Conferência", 0)], linhas,
        ["Total", "", "", str(notas), br_reais(total), ""]) + (
        f'<p class="baixar"><a class="botao" href="notas-{mes}.csv" download>Baixar as notas para emitir</a>'
        f'<span>Arquivo com as {notas} notas, uma linha por item: tomador, CNPJ, item, quantidade, valor e data de emissão.</span></p>'
        ) + "</div>"

    if conferencia:
        corpo += '<h2 id="conferir">Para conferir antes de emitir</h2>' + "".join(
            aviso(a, f' · <a href="{arquivo_nota(f)}">{escape(f["cliente"])}</a>', arquivo_nota(f)) for f, a in conferencia)

    linhas = [[f'<a href="{arquivo_nota(f)}#diagnostico">{escape(f["cliente"])}</a>', br_reais(f["faturado"]["total"]),
               br_reais(f["total"]), diferenca(f["diferenca"]),
               clausulas(f["clausulas_em_jogo"], arquivo_nota(f)) or "—"] for f in do_mes]
    corpo += ('<h2>&nbsp;</h2><div class="cartao diagnostico" id="diagnostico"><span class="etiqueta">Diagnóstico do case · não faz parte do produto</span>'
              "<h2>O que foi faturado × a regra do contrato</h2>"
              '<p class="sub" style="color:var(--escuro);max-width:75ch">As notas emitidas contaram a base num único instante, igual para todos os clientes. '
              "Esta tabela compara esse valor com o que a regra de cada contrato manda cobrar. "
              "A coluna do meio diz quanto o faturado ficou acima ou abaixo da regra, e a última aponta a cláusula que a nota emitida não seguiu. "
              "O valor pela regra depende das leituras adotadas, que estão em cada nota.</p>"
              + tabela([("Cliente", 0), ("Faturado", 1), ("Pela regra do contrato", 1), ("Faturado, contra a regra", 1), ("No contrato", 0)], linhas,
                       ["Total", br_reais(faturado), br_reais(total), diferenca(round(total - faturado, 2)), ""])
              + "".join(aviso(a, f' · <a href="{arquivo_nota(f)}#diagnostico">{escape(f["cliente"])}</a>', arquivo_nota(f)) for f, a in diagnostico)
              + "</div>")
    secoes = [("notas", "Notas")] + ([("conferir", "Para conferir")] if conferencia else []) + [("diagnostico", "Diagnóstico")]
    return pagina(f"Fechamento de {br_mes(mes)}", capa, corpo, meses, mes,
                  trilho(None, f"Fechamento de {br_mes(mes)}", secoes))


# ---------------------------------------------------------------- o arquivo para emitir

COLUNAS = ["cliente", "contrato", "tomador", "cnpj_tomador", "competencia", "data_emissao", "vencimento_dias",
           "item", "base_calculo", "quantidade", "valor_unitario", "valor_item", "total_da_nota"]


def arquivo_das_notas(mes, fechamentos, fichas):
    """As notas do mês, uma linha por item, nas colunas que a tabela de notas emitidas já usa.

    Separado por ponto e vírgula e com vírgula decimal, para abrir direto na planilha.
    """
    decimal = lambda v: f"{v:.2f}".replace(".", ",")
    inteiro_ou_decimal = lambda q: str(q) if float(q).is_integer() else decimal(q)
    saida = io.StringIO()
    w = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    w.writerow(COLUNAS)
    for f in fechamentos:
        if f["competencia"] != mes:
            continue
        ficha = fichas[f["cliente"]]
        for nota in f["notas"]:
            for i in nota["itens"]:
                w.writerow([f["cliente"], f["contrato"], nota["tomador"], nota["cnpj"], mes, f["emissao"],
                            ficha["vencimento_dias"] or "", i["descricao"], ficha["conta"], inteiro_ou_decimal(i["quantidade"]),
                            decimal(i["unitario"]), decimal(i["valor"]), decimal(nota["total"])])
    return "\ufeff" + saida.getvalue()  # a marca inicial faz a planilha ler os acentos


# ---------------------------------------------------------------- a nota explicada

def tabela_pessoas(linhas, ficha, multi):
    com_plano, com_dias = ficha["preco"]["tipo"] == "por_plano", any("dias" in l for l in linhas)
    cab = [("Pessoa", 0), ("Tipo", 0)] + ([("Plano", 0)] if com_plano else []) + ([("Empresa", 0)] if multi else []) \
        + [("No sistema desde", 0)] + ([("Dias no mês", 1)] if com_dias else [])
    corpo = [[l["pessoa"], l["tipo"]] + ([l["plano"]] if com_plano else []) + ([escape(l["empresa"])] if multi else [])
             + [br_data(l["cadastrada_em"])] + ([str(l["dias"])] if com_dias else []) for l in linhas]
    return tabela(cab, corpo)


def nota_explicada(f, ficha, vizinhas, meses, do_mes):
    multi = len({l["cnpj"] for l in f["pessoas"]}) > 1 or len(f["notas"]) > 1
    unidade = ficha["conta"]
    if f["metodo"] == "foto":
        contagem = f"{f['instante'][8:10]}/{f['instante'][5:7]}, {int(f['instante'][11:13])}h"
        nota_contagem = "base cadastrada neste instante"
    else:
        ano, mes = f["competencia"].split("-")
        contagem = f"{br_mes(f['competencia']).split(' de ')[0].capitalize()} inteiro"
        nota_contagem = f"maior número em {br_data(f['dia_do_maximo'])}" if f["metodo"] == "maximo_do_mes" else "posição no fim de cada dia"

    capa = (f"<h1>{escape(f['cliente'])}</h1><p>Contrato {f['contrato']} · competência {br_mes(f['competencia'])}</p>")
    corpo = '<div class="blocos">' + bloco("Valor da nota", br_reais(f["total"]), f"{len(f['notas'])} nota(s)") + \
        bloco(f"{unidade.capitalize()} cobrad{'o' if unidade == 'titulares' else 'a'}s", br_num(f["quantidade"]), METODO[f["metodo"]]) + \
        bloco("Contagem", contagem, nota_contagem) + bloco("Emissão", br_data(f["emissao"]),
              f"vencimento em {ficha['vencimento_dias']} dias" if ficha["vencimento_dias"] else "&nbsp;") + "</div>"

    # 1. como o valor foi calculado
    corpo += '<h2 id="calculo">Como este valor foi calculado</h2>' + '<div class="cartao">' + f'<p class="regra">{escape(ficha["regra"])}</p>'
    corpo += '<ol class="passos">' + "".join(f"<li>{escape(p)}</li>" for p in f["passos"]) + "</ol>"
    for n in f["notas"]:
        corpo += f"<h3>Nota para {escape(n['tomador'])} · CNPJ {n['cnpj']}</h3>" + tabela(
            [("Item", 0), ("Quantidade", 1), ("Valor unitário", 1), ("Valor", 1)],
            [[escape(i["descricao"]), br_num(i["quantidade"]), br_reais(i["unitario"]), br_reais(i["valor"])] for i in n["itens"]],
            ["Total da nota", "", "", br_reais(n["total"])])
    ac, alt = f.get("acerto"), f.get("acerto_alternativo")
    if ac and alt:
        nome = motor.CRITERIOS_DE_ACERTO
        corpo += (f'<div class="aviso atencao"><strong>Cláusula ambígua, na leitura do autor deste protótipo (Mateus): o acerto do pré-pago'
                  f'{clausulas(motor.clausulas_de(ficha, "acerto"))}</strong>'
                  f'O contrato manda compensar a diferença para os titulares "efetivamente ativos no mês de referência" e não define o termo. '
                  f'Também não diz o que fazer com quem entra ou sai entre a emissão da nota, no dia 27, e o fim do mês. '
                  f'<br>Leitura adotada nesta nota: <strong>{nome[ac["criterio"]].lower()}</strong>. Acerto de <strong>{br_reais(ac["valor"])}</strong>.'
                  f'<details><summary>Ver a outra leitura: {nome[alt["criterio"]].lower()} ({br_reais(alt["valor"])})</summary>'
                  + tabela([("Leitura", 0), ("Como conta", 0), (f"{unidade.capitalize()} no acerto", 1), ("Valor do acerto", 1), ("Total da nota", 1)],
                           [[f"<strong>{nome[x['criterio']]}</strong>" + (" (adotada)" if x is ac else ""),
                             "Quem esteve ativo em ao menos 1 dia do mês paga o mês; quem entra depois do dia 26 é cobrado na nota seguinte"
                             if x["criterio"] == "ao_menos_um_dia" else "A diferença entre a contagem desta nota e a contagem anterior",
                             f"{x['quantidade']:+d}", br_reais(x["valor"]), br_reais(round(f["total"] - ac["valor"] + x["valor"], 2))] for x in (ac, alt)])
                  + '<p>As duas dão o mesmo valor para quem fica o mês inteiro. Só divergem para quem entra ou sai no meio do ciclo: '
                    'pela foto, quem sai no meio do mês recebe crédito, e quem entra e sai entre duas contagens nunca é cobrado. '
                    'A leitura adotada é a mais literal e a mais favorável à Medipreço; a prática já combinada com o cliente pesa mais do que as duas.</p>'
                    "</details></div>")
    if ac:
        if ac["residual"] and ac["residual"]["pessoas"]:
            corpo += (f"<details><summary>Ajuste de {br_mes(ac['residual']['competencia'])}: quem entrou depois da contagem daquele mês "
                      f"({len(ac['residual']['pessoas'])})</summary>{tabela_pessoas(ac['residual']['pessoas'], ficha, multi)}</details>")
        if ac["debito"]:
            corpo += (f"<details><summary>Acerto de {br_mes(ac['competencia'])}: quem entrou depois da cobrança ({len(ac['debito'])})</summary>"
                      f"{tabela_pessoas(ac['debito'], ficha, multi)}</details>")
        if ac["credito"]:
            corpo += (f"<details><summary>Acerto de {br_mes(ac['competencia'])}: quem foi cobrado e não chegou a estar ativo no mês ({len(ac['credito'])})</summary>"
                      f"{tabela_pessoas(ac['credito'], ficha, multi)}</details>")
    for l in ficha["leituras"]:
        # o aviso de mudança de empresa só aparece no mês em que ela aconteceu (e vem pela conferência, com os valores)
        if l["apoio"] == "pergunta" and not l.get("quando"):
            corpo += (f'<div class="aviso atencao"><strong>Ponto que o contrato não define: {escape(l["ponto"])}</strong>'
                      f'{escape(l["adotado"])} {escape(l["evidencia"])}</div>')
    corpo += "</div>"

    # 2. a regra no contrato
    corpo += '<h2 id="contrato">A regra no contrato</h2>' + '<div class="cartao"><dl class="clausulas">' + "".join(
        f'<dt id="clausula-{k.replace(".", "-")}">Cláusula {k}</dt><dd>{escape(v)}</dd>' for k, v in ficha["clausulas"].items()) + "</dl>"
    corpo += "<h3>Leituras adotadas neste cálculo</h3>" + tabela(
        [("Ponto", 0), ("O que foi adotado", 0), ("Apoio", 0), ("Evidência", 0)],
        [[escape(l["ponto"]), escape(l["adotado"]), f'<span class="selo {APOIO[l["apoio"]][1]}">{APOIO[l["apoio"]][0]}</span>',
          escape(l["evidencia"])] for l in ficha["leituras"]]) + "</div>"

    # 3. o que mudou desde o mês anterior
    c = f["comparacao"]
    if c:
        sinal = lambda n: f"{n:+,}".replace(",", ".")
        corpo += f'<h2 id="mudou">O que mudou desde {br_mes(c["competencia_anterior"])}</h2>'
        corpo += '<div class="cartao">' + tabela(
            [("", 0), (br_mes(c["competencia_anterior"]).capitalize(), 1), (br_mes(f["competencia"]).capitalize(), 1), ("Variação", 1)],
            [[f"{unidade.capitalize()} cobrad{'o' if unidade == 'titulares' else 'a'}s", br_num(c["quantidade_anterior"]), br_num(f["quantidade"]), sinal(c["variacao_quantidade"])],
             ["Valor", br_reais(c["total_anterior"]), br_reais(f["total"]), ("+" if c["variacao_valor"] >= 0 else "−") + br_reais(abs(c["variacao_valor"]))[3:]]])
        corpo += (f"<p>Entraram <strong>{len(c['entraram'])}</strong> e saíram <strong>{len(c['sairam'])}</strong>"
                  + (f"; <strong>{len(c['trocaram_de_plano'])}</strong> trocaram de plano" if c["trocaram_de_plano"] else "")
                  + f". {br_num(c['quantidade_anterior'])} + {len(c['entraram'])} − {len(c['sairam'])} = {br_num(f['quantidade'])}.</p>")
        if c["entraram"]:
            corpo += f"<details><summary>Quem entrou ({len(c['entraram'])})</summary>{tabela_pessoas(c['entraram'], ficha, multi)}</details>"
        if c["sairam"]:
            corpo += f"<details><summary>Quem saiu ({len(c['sairam'])})</summary>{tabela_pessoas(c['sairam'], ficha, multi)}</details>"
        if c["trocaram_de_plano"]:
            corpo += f"<details><summary>Quem trocou de plano ({len(c['trocaram_de_plano'])})</summary>" + tabela(
                [("Pessoa", 0), ("De", 0), ("Para", 0)], [[t["pessoa"], t["de"], t["para"]] for t in c["trocaram_de_plano"]]) + "</details>"
        corpo += "</div>"

    # 4. o que mudou na base depois da contagem
    if "depois_da_contagem" in f:
        ev = sorted(f["depois_da_contagem"], key=lambda e: (e["data_informada"], e["pessoa"]))
        fim = br_mes(f["competencia"])
        corpo += '<h2 id="depois">O que mudou na base depois da contagem</h2><div class="cartao">'
        if ev:
            saidas, entradas = sum(e["evento"] == "saida" for e in ev), sum(e["evento"] == "entrada" for e in ev)
            corpo += (f"<p>A base foi contada em {br_data_hora(f['instante'])}: <strong>{br_num(f['base_na_contagem'])} vidas</strong>. "
                      f"Depois disso, até o fim de {fim}, o sistema recebeu {saidas} saída(s) e {entradas} entrada(s). "
                      f"Elas não entram nesta nota. No último dia do mês a base tinha <strong>{br_num(f['base_no_fim_do_mes'])} vidas</strong>.</p>")
            corpo += tabela([("Pessoa", 0), ("O que mudou", 0), ("Data informada pelo RH", 0), ("Recebido pelo sistema em", 0), ("Como chegou", 0)],
                            [[e["pessoa"], {"saida": "Saída", "entrada": "Entrada", "troca_plano": "Troca de plano"}[e["evento"]],
                              br_data(e["data_informada"]), br_data_hora(e["cadastrado_em"]),
                              {"carga_rh": "Arquivo do RH", "portal_rh": "Portal", "suporte_medipreco": "Suporte Medipreço"}[e["origem"]]] for e in ev])
        else:
            corpo += f"<p>Nenhuma alteração chegou entre a contagem ({br_data_hora(f['instante'])}) e o fim de {fim}.</p>"
        corpo += "</div>"

    # 5. conferência
    conf = [a for a in f["alertas"] if not a["diagnostico"]]
    if conf:
        corpo += '<h2 id="conferencia">Conferência antes de emitir</h2>' + "".join(aviso(a) for a in conf)

    # 6. pessoas cobradas
    corpo += (f"<h2 id=\"pessoas\">{unidade.capitalize()} cobrad{'o' if unidade == 'titulares' else 'a'}s ({br_num(f['quantidade'])})</h2>"
              f'<div class="cartao"><details><summary>Ver a lista completa</summary>{tabela_pessoas(f["pessoas"], ficha, multi)}</details></div>')

    # 7. diagnóstico: o que foi faturado de verdade
    fat = f["faturado"]
    corpo += ('<h2>&nbsp;</h2><div class="cartao diagnostico" id="diagnostico"><span class="etiqueta">Diagnóstico do case · não faz parte do produto</span>'
              "<h2>O que foi faturado nesta competência</h2>"
              f'<p class="sub" style="color:var(--escuro)">Contagem feita em {br_data_hora(fat["contagem_em"])}; nota emitida em {br_data(fat["emissao"])}.</p>'
              + tabela([("Nota", 0), ("Tomador", 0), ("Item", 0), ("Quantidade", 1), ("Valor unitário", 1), ("Valor", 1)],
                       [[i["nota"], escape(i["tomador"]), escape(i["descricao"]), br_num(i["quantidade"]), br_reais(i["unitario"]), br_reais(i["valor"])] for i in fat["itens"]],
                       ["Faturado", "", "", "", "", br_reais(fat["total"])])
              + f"<p>Pela regra do contrato: <strong>{br_reais(f['total'])}</strong>. Faturado, contra a regra: <strong>{diferenca(f['diferenca'])}</strong>."
              + (f" No contrato: {clausulas(f['clausulas_em_jogo'])}" if f["clausulas_em_jogo"] else "") + "</p>"
              + "".join(aviso(a) for a in f["alertas"] if a["diagnostico"]) + "</div>")

    # 8. para onde ir daqui
    antes, depois = vizinhas
    nome_mes = lambda x: br_mes(x["competencia"]).split(" de ")[0].capitalize()
    lista = f'mes-{f["competencia"]}.html'
    corpo += (f'<h2>Para onde ir daqui</h2><div class="cartao"><div class="outras">'
              f'<a class="principal" href="{lista}">← Voltar para o fechamento de {br_mes(f["competencia"])}</a>'
              + (f'<a href="{arquivo_nota(antes)}">← {escape(f["cliente"])} em {nome_mes(antes).lower()}</a>' if antes else "")
              + (f'<a href="{arquivo_nota(depois)}">{escape(f["cliente"])} em {nome_mes(depois).lower()} →</a>' if depois else "")
              + "</div>" + f'<h3>Outras notas de {br_mes(f["competencia"])}</h3><div class="outras">'
              + "".join(f'<a href="{arquivo_nota(x)}">{escape(x["cliente"])}</a>' for x in do_mes if x is not f) + "</div></div>")

    secoes = [("calculo", "Cálculo"), ("contrato", "Contrato")] + ([("mudou", "Mês anterior")] if c else []) \
        + ([("depois", "Depois da contagem")] if "depois_da_contagem" in f else []) + [("pessoas", "Pessoas"), ("diagnostico", "Diagnóstico")]
    vizinhos = ([(arquivo_nota(antes), f"← {nome_mes(antes)}")] if antes else []) + ([(arquivo_nota(depois), f"{nome_mes(depois)} →")] if depois else [])
    return pagina(f"{f['cliente']} · {br_mes(f['competencia'])}", capa, corpo, meses, f["competencia"],
                  trilho((lista, f"Fechamento de {br_mes(f['competencia'])}"), f["cliente"], secoes, vizinhos))


# ---------------------------------------------------------------- o que dá para vender (comercial)

PECAS = [
    ("conta", "O que conta", [("vidas", "Todas as vidas (titular e dependentes)"), ("titulares", "Só os titulares")]),
    ("apuracao", "Como conta as vidas do mês", [("foto", "Contagem num dia do mês"), ("maximo_do_mes", "Maior número do mês"),
                                                ("ao_menos_um_dia", "Quem esteve ao menos 1 dia"), ("pro_rata", "Pró-rata por dia")]),
    ("preco", "Preço", [("fixo", "Valor fixo por vida"), ("por_plano", "Um valor por plano"), ("faixa", "Faixa pelo tamanho da base")]),
    ("minimo", "Mínimo garantido", [(False, "Sem mínimo"), (True, "Com mínimo")]),
    ("notas", "Notas", [("unica", "Uma nota"), ("por_cnpj", "Uma por CNPJ, com rateio")]),
]
NOME_DA_PECA = {(chave, valor): nome for chave, _, opcoes in PECAS for valor, nome in opcoes}


def modelo_de(ficha):
    """As cinco escolhas de uma ficha, para comparar contratos entre si."""
    return (ficha["conta"], ficha["apuracao"]["metodo"], ficha["preco"]["tipo"], bool(ficha.get("minimo_vidas")), ficha["notas"]["tipo"])


def ficha_do_modelo(conta, metodo, preco, minimo, notas):
    """Uma ficha só com o esqueleto do modelo, para perguntar ao motor se ele sabe cobrar."""
    return {"cliente": "modelo", "conta": conta,
            "apuracao": {"metodo": metodo, **({"dia": 26, "mes": "referencia"} if metodo == "foto" else {})},
            "preco": {"fixo": {"tipo": "fixo", "valor": 1.0}, "por_plano": {"tipo": "por_plano", "valores": {"A": 1.0}},
                      "faixa": {"tipo": "faixa", "faixas": [{"ate": 10, "valor": 1.0}, {"ate": None, "valor": 1.0}]}}[preco],
            "minimo_vidas": 500 if minimo else None,
            "notas": {"tipo": "unica", "tomador": "-"} if notas == "unica" else {"tipo": "por_cnpj", "rateio": "dia_do_maximo"},
            "emissao": {"tipo": "primeiro_dia_util", "mes": "seguinte"}}


def catalogo(fichas):
    """Todas as combinações das cinco escolhas, com a resposta do motor para cada uma."""
    em_uso = {}
    for f in fichas.values():
        em_uso.setdefault(modelo_de(f), []).append(f["cliente"])
    modelos = [()]
    for _, _, opcoes in PECAS:
        modelos = [m + (valor,) for m in modelos for valor, _ in opcoes]
    return [{"modelo": m, "clientes": em_uso.get(m, []), "motivos": motor.validar(ficha_do_modelo(*m))} for m in modelos]


def o_que_da_para_vender(fichas, fechamentos, meses):
    cat = catalogo(fichas)
    usados = [c for c in cat if c["clientes"]]
    aceitos = [c for c in cat if not c["motivos"] and not c["clientes"]]
    recusados = [c for c in cat if c["motivos"]]
    nomes = lambda m: [NOME_DA_PECA[(PECAS[i][0], v)] for i, v in enumerate(m)]
    ultima = {f["cliente"]: f for f in fechamentos if f["competencia"] == "2026-10"}
    pre_pagos = [f["cliente"] for f in fichas.values() if f.get("acerto")]

    capa = ("<h1>O que dá para vender</h1><p>Para o comercial, antes de prometer: os modelos de cobrança que o sistema "
            "sabe calcular hoje, os que ele recusa e por quê. Esta página é montada pelo próprio motor de cálculo, "
            "que responde a cada combinação.</p>")
    # mínimo (posição 3) e pró-rata (posição 1) são as duas peças com restrição
    especial = lambda c: c["modelo"][3] or c["modelo"][1] == "pro_rata"
    simples, especiais = [c for c in cat if not especial(c)], [c for c in cat if especial(c)]
    ok = lambda lista: sum(1 for c in lista if not c["motivos"])
    corpo = '<div class="blocos">' + bloco("Peças de cobrança", str(sum(len(o) for _, _, o in PECAS)),
                                           "todas calculadas: o que conta, como conta, preço, mínimo e notas") \
        + bloco("Modelos sem mínimo e sem pró-rata", f"{ok(simples)} de {len(simples)}", "toda combinação é cobrável") \
        + bloco("Modelos com mínimo ou pró-rata", f"{ok(especiais)} de {len(especiais)}",
                "cobráveis com preço fixo e uma nota; nos outros, o sistema recusa e diz por quê") + "</div>"

    corpo += ('<h2 id="pecas">As cinco escolhas de um contrato</h2><p class="sub">Todo contrato do kit se descreve com estas escolhas. '
              "Um modelo novo é uma combinação delas.</p>" + '<div class="cartao">' + tabela(
                  [("Escolha", 0), ("Opções", 0), ("Quem usa hoje", 0)],
                  [[escape(titulo) if i == 0 else "", escape(nome),
                    escape(", ".join(sorted(f["cliente"] for f in fichas.values() if modelo_de(f)[n] == valor))) or "—"]
                   for n, (_, titulo, opcoes) in enumerate(PECAS) for i, (valor, nome) in enumerate(opcoes)]) + "</div>")

    corpo += ('<h2 id="em-uso">Modelos em uso</h2><p class="sub">Conferidos contra as notas já emitidas e contra uma segunda conta.</p>'
              + '<div class="cartao">' + tabela(
                  [("Cliente", 0)] + [(titulo, 0) for _, titulo, _ in PECAS],
                  [[", ".join(f'<a href="{arquivo_nota(ultima[c])}">{escape(c)}</a>' for c in u["clientes"])] + [escape(x) for x in nomes(u["modelo"])]
                   for u in usados]) + "</div>")

    corpo += ('<h2 id="aceitos">Outras combinações que o sistema já sabe cobrar</h2><p class="sub">São feitas das mesmas peças. '
              "As peças foram conferidas fora do contrato em que nasceram: cobrança por titular com outro jeito de contar, "
              "nota por CNPJ com contagem num dia (reproduz as nove notas que o Cedro recebeu) e faixa de preço num grupo. "
              "Nenhum contrato do kit usa estas combinações; o primeiro cliente de cada uma merece uma conferência à mão.</p>" + '<div class="cartao"><details><summary>'
              f"Ver as {len(aceitos)} combinações</summary>" + tabela([(titulo, 0) for _, titulo, _ in PECAS],
                                                                     [[escape(x) for x in nomes(a["modelo"])] for a in aceitos]) + "</details></div>")

    por_motivo = {}
    for r in recusados:
        por_motivo.setdefault(r["motivos"][0].split(";")[0], []).append(r)
    corpo += ('<h2 id="recusados">O que o sistema recusa hoje</h2><p class="sub">Todos envolvem mínimo ou pró-rata fora do caso simples. '
              "Em parte falta o contrato dizer (a que preço se cobra o complemento do mínimo, qual empresa do grupo paga), em parte falta programar. "
              "Até lá, o sistema recusa o contrato em vez de calcular errado.</p>" + '<div class="cartao">' + tabela(
                  [("Motivo", 0), ("Combinações", 1), ("Um exemplo", 0)],
                  [[escape(motivo[0].upper() + motivo[1:]), str(len(lista)), escape(" · ".join(nomes(lista[0]["modelo"])))]
                   for motivo, lista in sorted(por_motivo.items(), key=lambda kv: -len(kv[1]))]) + "</div>")

    corpo += ('<h2 id="quando">Quando se paga</h2><div class="cartao"><p><strong>Pós-pago:</strong> nota no primeiro dia útil do mês seguinte. '
              "Funciona com qualquer combinação acima.</p><p><strong>Pré-pago:</strong> nota no mês anterior, pela contagem de um dia, "
              "e a diferença para quem esteve mesmo ativo entra numa nota seguinte, a crédito ou a débito. "
              "Hoje só está calculado com contagem num dia, preço fixo e nota única"
              + (f" (é o contrato da {escape(', '.join(pre_pagos))})" if pre_pagos else "") + ".</p></div>")

    corpo += ('<h2 id="perguntas">O que perguntar antes de assinar</h2><p class="sub">Pontos que os seis contratos deixaram em aberto. '
              "Um contrato novo deveria responder por escrito.</p>" + '<div class="cartao">' + tabela(
                  [("Cliente", 0), ("Ponto que o contrato não define", 0), ("O que o sistema faz enquanto isso", 0)],
                  [[escape(f["cliente"]), escape(l["ponto"]), escape(l["adotado"])]
                   for f in fichas.values() for l in f["leituras"] if l["apoio"] == "pergunta"]) + "</div>")

    secoes = [("pecas", "Escolhas"), ("em-uso", "Em uso"), ("aceitos", "Aceitos"), ("recusados", "Recusados"), ("quando", "Quando se paga"), ("perguntas", "Perguntas")]
    return pagina("O que dá para vender", capa, corpo, meses, "vender", trilho(("index.html", "Fechamento do mês"), "O que dá para vender", secoes))


# ---------------------------------------------------------------- gerar tudo

def paginas(r):
    """Monta as páginas e os arquivos de notas a partir do resultado do motor. Devolve {nome do arquivo: conteúdo}."""
    fichas = {x["cliente"]: x for x in r["fichas"]}
    fechamentos = r["fechamentos"]
    meses = sorted({f["competencia"] for f in fechamentos})
    saida = {f"mes-{mes}.html": lista_do_mes(mes, fechamentos, meses) for mes in meses}
    saida["index.html"] = saida["mes-2026-10.html"]
    saida["vender.html"] = o_que_da_para_vender(fichas, fechamentos, meses)
    saida.update({f"notas-{mes}.csv": arquivo_das_notas(mes, fechamentos, fichas) for mes in meses})
    for cliente in fichas:
        do_cliente = [f for f in fechamentos if f["cliente"] == cliente]
        for i, f in enumerate(do_cliente):
            vizinhas = (do_cliente[i - 1] if i else None, do_cliente[i + 1] if i + 1 < len(do_cliente) else None)
            do_mes = [x for x in fechamentos if x["competencia"] == f["competencia"]]
            saida[arquivo_nota(f)] = nota_explicada(f, fichas[cliente], vizinhas, meses, do_mes)
    return saida


def gerar():
    r = motor.rodar()
    SITE.mkdir(exist_ok=True)
    for nome, html in paginas(r).items():
        (SITE / nome).write_text(html, encoding="utf-8")
    return len({f["competencia"] for f in r["fechamentos"]}), len(r["fechamentos"])


if __name__ == "__main__":
    n_meses, n_notas = gerar()
    print(f"{n_meses} listas de mês e {n_notas} notas explicadas gravadas em site/. Abra site/index.html")
