"""Motor do fechamento do mês.

Lê o histórico de eventos (dados/base.sqlite) e a ficha de regras de cada contrato
(contratos.json) e calcula, para cada cliente e competência, as notas, as pessoas
por trás de cada número e os alertas.

O caminho é sempre o mesmo:
    eventos -> períodos de cadastro -> apuração (quem conta) -> preço -> notas

Linha do tempo: a base cadastrada. Vale o que estava cadastrado no sistema
(data_processamento), não a data que o RH declarou (data_informada).

Uso:  python3 motor.py        (grava saidas/fechamento.json)
"""
import calendar
import json
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).parent
BANCO = RAIZ.parent / "dados" / "base.sqlite"
FICHAS = RAIZ / "contratos.json"
SAIDA = RAIZ / "saidas" / "fechamento.json"

COMPETENCIAS = ["2026-08", "2026-09", "2026-10"]


# ---------------------------------------------------------------- 1. dados

def carregar(banco=BANCO):
    """Lê as tabelas do kit, sem transformar nada."""
    if not Path(banco).exists():
        raise FileNotFoundError(
            f"Falta a base do kit. Copie o arquivo base.sqlite do zip do case para {banco} "
            "(os dados do case não vão no repositório; veja o README)."
        )
    con = sqlite3.connect(banco)
    con.row_factory = sqlite3.Row
    ler = lambda sql: [dict(r) for r in con.execute(sql)]
    return {
        "empresas": {r["cnpj"]: r for r in ler("select * from empresas")},
        "pessoas": {r["pessoa_id"]: r for r in ler("select * from pessoas")},
        "eventos": ler("select * from eventos order by data_processamento, evento_id"),
        "notas": ler("select * from notas_emitidas order by nota_id, item"),
    }


def montar_periodos(dados):
    """Transforma os eventos em períodos de cadastro: um por pessoa e CNPJ, da entrada até a saída.

    Cada período guarda quando entrou e saiu DO SISTEMA (data de processamento),
    as datas que o RH declarou e os planos que a pessoa teve.
    Período desfeito pelo suporte da Medipreço fica marcado como anulado.
    """
    abertos, periodos = {}, []
    for ev in dados["eventos"]:
        chave = (ev["pessoa_id"], ev["cnpj"])
        if ev["tipo_evento"] == "entrada":
            empresa = dados["empresas"][ev["cnpj"]]
            abertos[chave] = {
                "pessoa": ev["pessoa_id"],
                "tipo": dados["pessoas"][ev["pessoa_id"]]["tipo"],
                "titular": dados["pessoas"][ev["pessoa_id"]]["titular_id"],
                "cnpj": ev["cnpj"],
                "empresa": empresa["razao_social"],
                "cliente": empresa["cliente"],
                "entrou": ev["data_processamento"],
                "saiu": None,
                "informada_entrada": ev["data_informada"],
                "informada_saida": None,
                "planos": [(ev["data_processamento"], ev["plano"])],
                "anulado": False,
            }
            periodos.append(abertos[chave])
        elif ev["tipo_evento"] == "troca_plano":
            abertos[chave]["planos"].append((ev["data_processamento"], ev["plano"]))
        else:  # saida
            p = abertos.pop(chave)
            p["saiu"] = ev["data_processamento"]
            p["informada_saida"] = ev["data_informada"]
            p["anulado"] = ev["origem"] == "suporte_medipreco"
    return periodos


# ---------------------------------------------------------------- 1b. a ficha é cobrável?

class FichaInvalida(ValueError):
    """A ficha pede uma conta que o motor não sabe fazer."""


def validar(ficha):
    """Diz o que o motor não sabe calcular nesta ficha. Lista vazia: o contrato é cobrável.

    O motor só calcula as combinações que foram conferidas nos seis contratos do kit.
    Qualquer outra é recusada aqui, com o motivo, em vez de sair um número errado.
    """
    p = []
    for campo in ("cliente", "conta", "apuracao", "preco", "notas", "emissao"):
        if campo not in ficha:
            p.append(f'falta o campo "{campo}"')
    if p:
        return p
    conta, ap, preco, notas, em = (ficha[c] for c in ("conta", "apuracao", "preco", "notas", "emissao"))
    metodo, tipo, minimo = ap.get("metodo"), preco.get("tipo"), ficha.get("minimo_vidas")

    if conta not in ("vidas", "titulares"):
        p.append(f'"conta" deve ser "vidas" ou "titulares" (veio "{conta}")')

    if metodo not in ("foto", "ao_menos_um_dia", "pro_rata", "maximo_do_mes"):
        p.append(f'método de apuração desconhecido: "{metodo}". O motor sabe: foto, ao_menos_um_dia, pro_rata, maximo_do_mes')
    elif metodo == "foto":
        if not (isinstance(ap.get("dia"), int) and 1 <= ap["dia"] <= 28):
            p.append("a foto precisa do dia da contagem, de 1 a 28")
        if ap.get("mes") not in ("referencia", "anterior"):
            p.append('a foto precisa dizer o mês da contagem: "referencia" ou "anterior"')

    if tipo == "fixo":
        if not isinstance(preco.get("valor"), (int, float)):
            p.append("preço fixo precisa do valor")
    elif tipo == "por_plano":
        if not preco.get("valores"):
            p.append("preço por plano precisa da tabela de planos e valores")
    elif tipo == "faixa":
        tetos = [f.get("ate") for f in preco.get("faixas") or []]
        if not tetos or tetos[-1] is not None or None in tetos[:-1] or tetos[:-1] != sorted(tetos[:-1]):
            p.append('as faixas precisam estar em ordem crescente, e a última sem teto ("ate": null)')
    else:
        p.append(f'tipo de preço desconhecido: "{tipo}". O motor sabe: fixo, por_plano, faixa')

    if metodo == "pro_rata" and tipo != "fixo":
        p.append("pró-rata só está calculado com preço fixo; com plano ou faixa, falta programar o preço de cada dia")
    if minimo and (tipo != "fixo" or metodo == "pro_rata"):
        p.append("mínimo só está calculado com preço fixo e sem pró-rata; com plano ou faixa, o contrato precisa dizer a que preço se cobra o complemento")

    if notas.get("tipo") == "unica":
        if not notas.get("tomador"):
            p.append("nota única precisa do CNPJ do tomador")
    elif notas.get("tipo") == "por_cnpj":
        if metodo == "pro_rata":
            p.append("nota por CNPJ não está calculada com pró-rata; falta programar os dias de cada pessoa em cada empresa")
        if minimo:
            p.append("nota por CNPJ não está calculada com mínimo; o contrato precisa dizer qual empresa paga o complemento")
        if metodo == "maximo_do_mes" and notas.get("rateio") != "dia_do_maximo":
            p.append('nota por CNPJ com máximo do mês precisa dizer o momento do rateio; o motor sabe "dia_do_maximo"')
    else:
        p.append(f'"notas" deve ser "unica" ou "por_cnpj" (veio "{notas.get("tipo")}")')

    if em.get("tipo") == "primeiro_dia_util":
        if em.get("mes") != "seguinte":
            p.append('emissão no primeiro dia útil só está calculada para o mês "seguinte" (pós-pago)')
    elif em.get("tipo") == "dia_fixo":
        if em.get("mes") != "anterior" or not isinstance(em.get("dia"), int):
            p.append('emissão em dia fixo só está calculada para o mês "anterior" (pré-pago), com o dia')
    else:
        p.append(f'tipo de emissão desconhecido: "{em.get("tipo")}"')

    if ficha.get("acerto"):
        pre_pago = metodo == "foto" and ap.get("mes") == "anterior" and em.get("tipo") == "dia_fixo"
        if not pre_pago or tipo != "fixo" or notas.get("tipo") != "unica" or ficha["acerto"].get("efetivos") not in ("ao_menos_um_dia", "foto"):
            p.append('acerto só está calculado no pré-pago (foto e emissão no mês anterior), com preço fixo, nota única '
                     'e "efetivos": "ao_menos_um_dia" ou "foto"')
    return p


def exigir_cobravel(ficha):
    problemas = validar(ficha)
    if problemas:
        raise FichaInvalida(f'{ficha.get("cliente", "contrato sem nome")}: o motor não sabe cobrar este contrato.\n  - '
                            + "\n  - ".join(problemas))


# ---------------------------------------------------------------- 2. calendário

def dia_util(d, feriados):
    return d.weekday() < 5 and d.isoformat() not in feriados


def recuar_para_dia_util(d, feriados):
    while not dia_util(d, feriados):
        d -= timedelta(days=1)
    return d


def avancar_para_dia_util(d, feriados):
    while not dia_util(d, feriados):
        d += timedelta(days=1)
    return d


def mes_vizinho(ano, mes, passo):
    total = ano * 12 + (mes - 1) + passo
    return total // 12, total % 12 + 1


def dias_do_mes(ano, mes):
    return [date(ano, mes, d) for d in range(1, calendar.monthrange(ano, mes)[1] + 1)]


def instante_da_foto(ficha, ano, mes, conv):
    """Dia e hora em que a base é contada, para contratos de foto."""
    ap = ficha["apuracao"]
    a, m = mes_vizinho(ano, mes, -1) if ap["mes"] == "anterior" else (ano, mes)
    dia = recuar_para_dia_util(date(a, m, ap["dia"]), conv["feriados"])
    return f"{dia.isoformat()} {conv['hora_da_contagem']}:00"


def data_de_emissao(ficha, ano, mes, conv):
    em = ficha["emissao"]
    if em["tipo"] == "primeiro_dia_util":
        a, m = mes_vizinho(ano, mes, +1)
        return avancar_para_dia_util(date(a, m, 1), conv["feriados"]).isoformat()
    a, m = mes_vizinho(ano, mes, -1)  # dia fixo do mês anterior (pré-pago)
    return avancar_para_dia_util(date(a, m, em["dia"]), conv["feriados"]).isoformat()


# ---------------------------------------------------------------- 3. quem estava cadastrado

def cadastrado(p, instante):
    """A pessoa estava no sistema naquele instante?"""
    return p["entrou"] <= instante and (p["saiu"] is None or p["saiu"] > instante)


def plano_em(p, instante):
    plano = p["planos"][0][1]
    for quando, nome in p["planos"]:
        if quando <= instante:
            plano = nome
    return plano


def fim_do_dia(d):
    return f"{d.isoformat()} 23:59:59"


def base_em(periodos, instante):
    """A base cadastrada num instante, uma linha por pessoa.

    Quem está em dois CNPJs do mesmo contrato ao mesmo tempo (transferência ainda
    não concluída no sistema) conta uma vez só, na empresa em que entrou por último.
    """
    por_pessoa = {}
    for p in periodos:
        if not p["anulado"] and cadastrado(p, instante):
            atual = por_pessoa.get(p["pessoa"])
            if atual is None or p["entrou"] > atual["entrou"]:
                por_pessoa[p["pessoa"]] = p
    return list(por_pessoa.values())


def dias_cadastrados(p, dias):
    """Os dias do mês em que a pessoa estava cadastrada no fim do dia."""
    return {d for d in dias if cadastrado(p, fim_do_dia(d))}


def linha(p, instante, **extra):
    return {"pessoa": p["pessoa"], "tipo": p["tipo"], "plano": plano_em(p, instante),
            "empresa": p["empresa"], "cnpj": p["cnpj"], "cadastrada_em": p["entrou"][:10], **extra}


# ---------------------------------------------------------------- 4. os quatro métodos de apuração

def apurar_foto(periodos, instante):
    """Conta quem estava cadastrado num instante."""
    return [linha(p, instante) for p in base_em(periodos, instante)]


def apurar_ao_menos_um_dia(periodos, dias):
    """Conta toda pessoa cadastrada em ao menos 1 dia do mês."""
    dias_de, ultimo = defaultdict(set), {}
    for p in periodos:  # em ordem de entrada; quem voltou ou foi transferido soma os dias sem repetir
        meus_dias = set() if p["anulado"] else dias_cadastrados(p, dias)
        if meus_dias:
            dias_de[p["pessoa"]] |= meus_dias
            ultimo[p["pessoa"]] = p
    return [linha(p, fim_do_dia(dias[-1]), dias=len(dias_de[pessoa])) for pessoa, p in ultimo.items()]


def apurar_pro_rata(periodos, dias):
    """Mesmas pessoas do método anterior; o preço é que será proporcional aos dias."""
    return apurar_ao_menos_um_dia(periodos, dias)


def apurar_maximo_do_mes(periodos, dias):
    """Acha o dia do mês com mais pessoas cadastradas e devolve a base daquele dia."""
    melhor_dia, melhor_base, serie = None, [], []
    for d in dias:
        base = base_em(periodos, fim_do_dia(d))
        serie.append({"dia": d.isoformat(), "vidas": len(base)})
        if len(base) > len(melhor_base):  # em caso de empate, vale o primeiro dia
            melhor_dia, melhor_base = d, base
    return melhor_dia, [linha(p, fim_do_dia(melhor_dia)) for p in melhor_base], serie


def transferencias_no_mes(meus, dias):
    """Pessoas que entraram numa empresa do contrato durante o mês vindo de outra empresa do mesmo contrato."""
    inicio, fim = f"{dias[0].isoformat()} 00:00:00", fim_do_dia(dias[-1])
    por_pessoa = defaultdict(list)
    for p in meus:
        if not p["anulado"]:
            por_pessoa[p["pessoa"]].append(p)
    achadas = []
    for periodos in por_pessoa.values():
        for p in periodos:
            origem = [q for q in periodos if q["cnpj"] != p["cnpj"] and q["entrou"] < p["entrou"] and (q["saiu"] is None or q["saiu"] >= inicio)]
            if inicio <= p["entrou"] <= fim and origem:
                achadas.append({"pessoa": p["pessoa"], "de": origem[-1]["empresa"], "para": p["empresa"], "em": p["entrou"][:10]})
    return achadas


CRITERIOS_DE_ACERTO = {"ao_menos_um_dia": "Mês cheio por qualquer dia ativo", "foto": "Foto do dia da contagem"}


def acerto_do_pre_pago(ficha, ano, mes, meus, conv, criterio):
    """Pré-pago: quem foi cobrado antes do mês contra quem esteve "efetivamente ativo" nele.

    A nota da competência C é contada e emitida no fim de C-1 e traz o acerto de C-1 (a "nota seguinte").
    O contrato não define "efetivamente ativo"; o motor sabe duas leituras:

    "ao_menos_um_dia": conta quem esteve cadastrado em ao menos 1 dia do mês. Na data da nota só se conhece
        o mês até a contagem, então quem entra depois dela fica para um ajuste na nota seguinte (o residual).
    "foto": conta quem está cadastrado no dia da contagem. O acerto é a diferença entre duas contagens.

    Devolve None quando a cobrança antecipada do mês é anterior ao histórico completo da base.
    """
    conta = lambda linhas: {l["pessoa"]: l for l in linhas if ficha["conta"] == "vidas" or l["tipo"] == "titular"}
    a, m = mes_vizinho(ano, mes, -1)
    cobrado_em = instante_da_foto(ficha, a, m, conv)      # a contagem que cobrou C-1 adiantado
    agora = instante_da_foto(ficha, ano, mes, conv)       # a contagem desta nota
    if cobrado_em[:10] < conv["historico_completo_desde"]:
        return None
    cobrados, na_contagem = conta(apurar_foto(meus, cobrado_em)), conta(apurar_foto(meus, agora))

    def ativos_ate(ano_, mes_, instante):
        """Quem esteve cadastrado em ao menos 1 dia do mês, pelo que se sabia no instante."""
        dias = [d for d in dias_do_mes(ano_, mes_) if fim_do_dia(d) < instante]
        return {**conta(apurar_ao_menos_um_dia(meus, dias)), **conta(apurar_foto(meus, instante))}

    residual = None
    if criterio == "foto":
        efetivos = na_contagem
    else:
        efetivos = ativos_ate(a, m, agora)
        # o residual: quem entrou em C-2 depois da contagem daquele mês e por isso ficou fora do acerto de C-2
        a2, m2 = mes_vizinho(ano, mes, -2)
        cobrado_em_2 = instante_da_foto(ficha, a2, m2, conv)
        if cobrado_em_2[:10] >= conv["historico_completo_desde"]:
            ja_contados = {**conta(apurar_foto(meus, cobrado_em_2)), **ativos_ate(a2, m2, cobrado_em)}
            mes_cheio = conta(apurar_ao_menos_um_dia(meus, dias_do_mes(a2, m2)))
            residual = {"competencia": f"{a2}-{m2:02d}", "pessoas": [mes_cheio[x] for x in mes_cheio if x not in ja_contados]}
    debito = [efetivos[x] for x in efetivos if x not in cobrados]
    credito = [cobrados[x] for x in cobrados if x not in efetivos]
    return {"criterio": criterio, "competencia": f"{a}-{m:02d}", "cobrado_em": cobrado_em, "ate": agora,
            "cobrados": len(cobrados), "efetivos": len(efetivos), "debito": debito, "credito": credito, "residual": residual,
            "quantidade": len(debito) - len(credito) + (len(residual["pessoas"]) if residual else 0), "valor": 0.0}


# ---------------------------------------------------------------- 5. preço

def preco_da_faixa(faixas, quantidade):
    for f in faixas:
        if f["ate"] is None or quantidade <= f["ate"]:
            return f["valor"]


def item(descricao, quantidade, unitario):
    return {"descricao": descricao, "quantidade": quantidade, "unitario": unitario,
            "valor": round(quantidade * unitario + 1e-9, 2)}


def precificar(ficha, linhas, dias, quantidade_do_grupo=None):
    """Transforma as pessoas apuradas em itens de nota.

    quantidade_do_grupo: nas notas por CNPJ, a faixa de preço é a do grupo inteiro, não a de cada empresa.
    """
    preco, unidade = ficha["preco"], ficha["conta"]
    if ficha["apuracao"]["metodo"] == "pro_rata":
        vida_dias = sum(l["dias"] for l in linhas)
        valor = round(preco["valor"] * vida_dias / len(dias) + 1e-9, 2)
        return [{"descricao": f"Mensalidade pró-rata: {vida_dias} vida-dias ÷ {len(dias)} dias do mês",
                 "quantidade": round(vida_dias / len(dias), 2), "unitario": preco["valor"], "valor": valor}]
    if preco["tipo"] == "por_plano":
        sem_preco = sorted({l["plano"] for l in linhas} - set(preco["valores"]))
        if sem_preco:  # sem isto, a pessoa ficaria na lista e fora da conta
            raise FichaInvalida(f'{ficha["cliente"]}: há pessoas em plano sem preço na ficha: {", ".join(sem_preco)}')
        return [item(f"Mensalidade Plano {plano}", sum(1 for l in linhas if l["plano"] == plano), valor)
                for plano, valor in preco["valores"].items()]
    quantidade = len(linhas)
    unitario = preco_da_faixa(preco["faixas"], quantidade_do_grupo or quantidade) if preco["tipo"] == "faixa" else preco["valor"]
    itens = [item(f"Mensalidade ({unidade})", quantidade, unitario)]
    minimo = ficha.get("minimo_vidas")
    if minimo and quantidade < minimo:
        itens.append(item(f"Complemento do mínimo de {minimo} vidas", minimo - quantidade, unitario))
    return itens


# ---------------------------------------------------------------- 6. fechamento de um cliente

def fechar(ficha, competencia, periodos, dados, conv):
    """Calcula o fechamento de um cliente numa competência."""
    exigir_cobravel(ficha)
    ano, mes = int(competencia[:4]), int(competencia[5:])
    dias = dias_do_mes(ano, mes)
    meus = [p for p in periodos if p["cliente"] == ficha["cliente"]]
    metodo = ficha["apuracao"]["metodo"]
    r = {"cliente": ficha["cliente"], "contrato": ficha["contrato"], "competencia": competencia,
         "metodo": metodo, "emissao": data_de_emissao(ficha, ano, mes, conv), "passos": []}

    # 6.1 quem conta
    if metodo == "foto":
        r["instante"] = instante_da_foto(ficha, ano, mes, conv)
        base = apurar_foto(meus, r["instante"])
        r["base_na_contagem"] = len(base)
        linhas = [l for l in base if ficha["conta"] == "vidas" or l["tipo"] == "titular"]
        r["passos"].append(f"Base cadastrada em {br_data_hora(r['instante'])}: {len(base)} vidas "
                           f"({sum(l['tipo'] == 'titular' for l in base)} titulares e "
                           f"{sum(l['tipo'] == 'dependente' for l in base)} dependentes).")
        if ficha["conta"] == "titulares":
            r["passos"].append(f"O contrato cobra por titular: {len(linhas)} titulares. Dependentes não pagam.")
    else:
        # por titular: os dependentes ficam fora antes de contar
        contaveis = meus if ficha["conta"] == "vidas" else [p for p in meus if p["tipo"] == "titular"]
        unidade = ficha["conta"].capitalize()
        if metodo == "maximo_do_mes":
            dia_pico, linhas, r["serie"] = apurar_maximo_do_mes(contaveis, dias)
            r["dia_do_maximo"] = dia_pico.isoformat()
            r["passos"].append(f"Maior número de {ficha['conta']} do grupo no mês: {len(linhas)}, em {br_data(dia_pico.isoformat())}.")
        else:
            linhas = apurar_ao_menos_um_dia(contaveis, dias)
            r["passos"].append(f"{unidade} com cadastro em ao menos 1 dia de {br_mes(competencia)}: {br_num(len(linhas))}.")

    # 6.2 preço e notas
    if ficha["notas"]["tipo"] == "por_cnpj":
        do_grupo = precificar(ficha, linhas, dias)
        if len(do_grupo) == 1:
            r["passos"].append(f"Valor do grupo: {do_grupo[0]['quantidade']} × {br_reais(do_grupo[0]['unitario'])} = {br_reais(do_grupo[0]['valor'])}.")
        else:
            r["passos"].append(f"Valor do grupo: {br_reais(round(sum(i['valor'] for i in do_grupo), 2))}.")
        r["passos"].append({"maximo_do_mes": "Divisão pelas vidas de cada empresa no dia em que o máximo foi alcançado.",
                            "foto": "Divisão pelas vidas de cada empresa no instante da contagem."}.get(
                                metodo, "Divisão pela empresa de cada pessoa; quem mudou de empresa no mês conta na de destino."))
        r["notas"] = []
        for cnpj, emp in dados["empresas"].items():
            if emp["cliente"] == ficha["cliente"]:
                da_empresa = [l for l in linhas if l["cnpj"] == cnpj]
                r["notas"].append({"tomador": emp["razao_social"], "cnpj": cnpj,
                                   "itens": precificar(ficha, da_empresa, dias, quantidade_do_grupo=len(linhas))})
        if metodo == "maximo_do_mes":
            # o dia em que se mede a proporção só importa quando alguém muda de empresa dentro do grupo no mês
            r["transferencias"] = transferencias_no_mes(meus, dias)
            no_fim = base_em(meus, fim_do_dia(dias[-1]))
            valor_do_grupo = round(sum(i["valor"] for i in do_grupo), 2)
            r["rateio_no_fim_do_mes"] = {n["tomador"]: round(valor_do_grupo * sum(p["cnpj"] == n["cnpj"] for p in no_fim) / max(len(no_fim), 1), 2)
                                         for n in r["notas"]}
    else:
        itens = precificar(ficha, linhas, dias)
        for it in itens:
            r["passos"].append(f"{it['descricao']}: {br_num(it['quantidade'])} × {br_reais(it['unitario'])} = {br_reais(it['valor'])}.")
        tomador = ficha["notas"]["tomador"]
        r["notas"] = [{"tomador": dados["empresas"][tomador]["razao_social"], "cnpj": tomador, "itens": itens}]
        if ficha.get("acerto"):
            criterio, unitario = ficha["acerto"]["efetivos"], ficha["preco"]["valor"]
            r["acerto"] = ac = acerto_do_pre_pago(ficha, ano, mes, meus, conv, criterio)
            # a outra leitura da mesma cláusula, só para mostrar quanto daria
            outro = next(c for c in CRITERIOS_DE_ACERTO if c != criterio)
            r["acerto_alternativo"] = alt = acerto_do_pre_pago(ficha, ano, mes, meus, conv, outro)
            for x in (ac, alt):
                if x:
                    x["valor"] = round(x["quantidade"] * unitario, 2)
            if ac:
                mes_ac, liquido = br_mes(ac["competencia"]), len(ac["debito"]) - len(ac["credito"])
                if criterio == "foto":
                    r["passos"].append(f"Acerto de {mes_ac}: {br_num(ac['efetivos'])} {ficha['conta']} na contagem desta nota e "
                                       f"{br_num(ac['cobrados'])} cobrados antes, em {br_data(ac['cobrado_em'][:10])}: {liquido:+d}.")
                else:
                    r["passos"].append(
                        f"Acerto de {mes_ac}: {br_num(ac['efetivos'])} {ficha['conta']} estiveram ativos em ao menos 1 dia do mês, até esta "
                        f"contagem, e {br_num(ac['cobrados'])} tinham sido cobrados antes, em {br_data(ac['cobrado_em'][:10])}. "
                        f"{len(ac['debito'])} entraram depois da cobrança e {len(ac['credito'])} foram cobrados sem chegar a estar ativos no mês: {liquido:+d}.")
                if liquido:
                    itens.append(item(f"Acerto de {mes_ac} ({ficha['conta']} a {'débito' if liquido > 0 else 'crédito'})", liquido, unitario))
                    r["passos"].append(f"{itens[-1]['descricao']}: {liquido:+d} × {br_reais(unitario)} = {br_reais(itens[-1]['valor'])}.")
                if ac["residual"] and ac["residual"]["pessoas"]:
                    n, mes_res = len(ac["residual"]["pessoas"]), br_mes(ac["residual"]["competencia"])
                    itens.append(item(f"Ajuste de {mes_res} ({ficha['conta']} que entraram depois da contagem daquele mês)", n, unitario))
                    r["passos"].append(f"Ajuste de {mes_res}: {n} {ficha['conta']} entraram depois da contagem daquele mês e ficaram fora "
                                       f"do acerto dele: {n} × {br_reais(unitario)} = {br_reais(itens[-1]['valor'])}.")
    for n in r["notas"]:
        n["total"] = round(sum(i["valor"] for i in n["itens"]), 2)
    r["total"] = round(sum(n["total"] for n in r["notas"]), 2)
    r["quantidade"] = len(linhas)
    r["pessoas"] = sorted(linhas, key=lambda l: (l["empresa"], l["tipo"] != "titular", l["pessoa"]))

    # 6.3 o que foi faturado de verdade
    emitidas = [n for n in dados["notas"] if n["cliente"] == ficha["cliente"] and n["competencia"] == competencia]
    r["faturado"] = {
        "itens": [{"nota": n["nota_id"], "tomador": n["tomador"], "descricao": n["item"], "quantidade": n["quantidade"],
                   "unitario": n["valor_unitario"], "valor": n["valor_item"]} for n in emitidas],
        "total": round(sum(n["valor_item"] for n in emitidas), 2),
        "quantidade": sum(n["quantidade"] for n in emitidas),
        "contagem_em": emitidas[0]["contagem_em"] if emitidas else None,
        "emissao": emitidas[0]["data_emissao"] if emitidas else None,
    }
    r["diferenca"] = round(r["total"] - r["faturado"]["total"], 2)
    # a mesma diferença sem o acerto do pré-pago, que tem aviso próprio
    r["diferenca_da_mensalidade"] = round(r["diferenca"] - ((r.get("acerto") or {}).get("valor") or 0), 2)

    # 6.4 o que mudou na base depois da contagem, até o fim do mês (só para foto no próprio mês)
    if metodo == "foto" and ficha["apuracao"]["mes"] == "referencia":
        fim = fim_do_dia(dias[-1])
        r["depois_da_contagem"] = [
            {"pessoa": e["pessoa_id"], "evento": e["tipo_evento"], "plano": e["plano"],
             "data_informada": e["data_informada"], "cadastrado_em": e["data_processamento"], "origem": e["origem"]}
            for e in dados["eventos"]
            if dados["empresas"][e["cnpj"]]["cliente"] == ficha["cliente"] and r["instante"] < e["data_processamento"] <= fim]
        r["base_no_fim_do_mes"] = len(base_em(meus, fim))

    r["alertas"] = alertas(ficha, r, meus, dias, dados, conv)
    # onde a nota emitida e o contrato não batem: os números das cláusulas, sem repetir
    r["clausulas_em_jogo"] = list(dict.fromkeys(n for a in r["alertas"] if a["diagnostico"] for n in a["clausulas"]))
    return r


# ---------------------------------------------------------------- 7. alertas (conferência antes de emitir)

def clausulas_de(ficha, *partes):
    """Os números das cláusulas que definem estas partes da regra ("conta", "apuracao", "preco"...), sem repetir."""
    mapa, numeros = ficha.get("clausula_de", {}), []
    for parte in partes:
        if mapa.get(parte) and mapa[parte] not in numeros:
            numeros.append(mapa[parte])
    return numeros


def alertas(ficha, r, meus, dias, dados, conv):
    avisos = []
    # diagnostico=True: compara com a nota que já foi emitida. Só existe neste estudo, não no produto.
    # clausulas: os números das cláusulas do contrato que a nota emitida deixou de seguir.
    ok = lambda nivel, titulo, texto, diagnostico=False, clausulas=(): avisos.append(
        {"nivel": nivel, "titulo": titulo, "texto": texto, "diagnostico": diagnostico, "clausulas": list(clausulas)})
    fat = r["faturado"]

    # base de cálculo trocada: faturou vidas num contrato por titular (ou o contrário)
    if r["metodo"] == "foto" and ficha["conta"] == "titulares" and fat["contagem_em"]:
        vidas = len(base_em(meus, fat["contagem_em"]))
        if fat["quantidade"] == vidas != r["quantidade"]:
            ok("erro", "Base de cálculo trocada",
               f"A nota emitida cobrou {vidas}, que é o total de vidas (titulares e dependentes). "
               f"O contrato cobra por titular: {r['quantidade']}. Cobrança a maior de {br_reais(-r['diferenca_da_mensalidade'])}.", diagnostico=True,
               clausulas=clausulas_de(ficha, "conta"))

    if r["diferenca_da_mensalidade"] and not any(a["nivel"] == "erro" for a in avisos):
        sentido = "a mais" if r["diferenca_da_mensalidade"] < 0 else "a menos"
        ok("atencao", "Faturado diferente da regra do contrato",
           f"Foi faturado {br_reais(fat['total'])}; pela regra do contrato são {br_reais(fat['total'] + r['diferenca_da_mensalidade'])}. "
           f"Faturado {sentido}: {br_reais(abs(r['diferenca_da_mensalidade']))}.", diagnostico=True,
           clausulas=clausulas_de(ficha, "apuracao"))

    # faixa de preço: a foto e a regra caem em faixas diferentes
    if ficha["preco"]["tipo"] == "faixa" and fat["itens"]:
        meu = r["notas"][0]["itens"][0]["unitario"]
        if fat["itens"][0]["unitario"] != meu:
            ok("atencao", "Faixa de preço diferente",
               f"A nota emitida contou {br_num(fat['quantidade'])} vidas e usou {br_reais(fat['itens'][0]['unitario'])} por vida. "
               f"Pela regra do contrato são {br_num(r['quantidade'])} vidas, na faixa de {br_reais(meu)}.", diagnostico=True,
               clausulas=clausulas_de(ficha, "preco", "apuracao"))

    # pré-pago: o contrato manda acertar a diferença na nota seguinte, e a nota emitida não traz o acerto
    ac = r.get("acerto")
    if ac and ac["quantidade"] and len(fat["itens"]) == 1:
        ok("atencao", "Acerto do pré-pago não aplicado",
           f"A nota emitida tem um item só, sem crédito nem débito. Pelo contrato, ela traria o acerto de {br_mes(ac['competencia'])}: "
           f"{ac['quantidade']:+d} {ficha['conta']}, {br_reais(ac['valor'])}. Pela outra leitura da cláusula seriam "
           f"{br_reais(r['acerto_alternativo']['valor'])}.", diagnostico=True, clausulas=clausulas_de(ficha, "acerto"))

    # carga desfeita pelo suporte dentro do mês
    desfeitos = [p for p in meus if p["anulado"] and dias_cadastrados(p, dias)]
    if desfeitos:
        ok("info", "Carga desfeita pelo suporte",
           f"{len(desfeitos)} entradas cadastradas em {br_data(desfeitos[0]['entrou'][:10])} foram desfeitas pelo suporte "
           f"da Medipreço em {br_data(desfeitos[0]['saiu'][:10])}. Não foram cobradas.")

    # pessoa cadastrada em duas empresas do contrato ao mesmo tempo
    dobrados = set()
    for d in dias:
        vistos = defaultdict(set)
        for p in meus:
            if not p["anulado"] and cadastrado(p, fim_do_dia(d)):
                vistos[p["pessoa"]].add(p["cnpj"])
        for pessoa, cnpjs in vistos.items():
            if len(cnpjs) > 1:
                dobrados.add((pessoa, d))
    if dobrados:
        pessoas = {p for p, _ in dobrados}
        d1, d2 = min(d for _, d in dobrados), max(d for _, d in dobrados)
        ok("info", "Pessoas em duas empresas ao mesmo tempo",
           f"{len(pessoas)} pessoas ficaram cadastradas em duas empresas do contrato de {br_data(d1.isoformat())} "
           f"a {br_data(d2.isoformat())} (transferência). Cada uma foi contada uma vez só, na empresa de destino.")

    # mudança de empresa dentro do grupo: é o único caso em que o dia do rateio muda a divisão
    if r.get("transferencias"):
        t = r["transferencias"]
        rotas = defaultdict(int)
        for x in t:
            rotas[(x["de"], x["para"])] += 1
        (de, para), n = max(rotas.items(), key=lambda kv: kv[1])
        ok("atencao", "Mudança de empresa dentro do grupo: a divisão depende do dia",
           f"{len(t)} pessoas mudaram de empresa neste mês ({n} de {de} para {para}, em {br_data(min(x['em'] for x in t))}). "
           f"O contrato manda dividir o valor na proporção das vidas de cada empresa e não diz em que dia medir. "
           f"Esta nota mede no dia do máximo ({br_data(r['dia_do_maximo'])}). Medindo no último dia do mês, a divisão seria: "
           + "; ".join(f"{nome}, {br_reais(v)} em vez de {br_reais(next(nt['total'] for nt in r['notas'] if nt['tomador'] == nome))}"
                       for nome, v in r["rateio_no_fim_do_mes"].items()) + ". O total do grupo é o mesmo.",
           clausulas=clausulas_de(ficha, "notas"))

    # dependente sem titular na base
    referencia = r.get("instante") or fim_do_dia(dias[-1])
    base = base_em(meus, referencia)
    presentes = {p["pessoa"] for p in base}
    orfaos = [p for p in base if p["tipo"] == "dependente" and p["titular"] not in presentes]
    if orfaos:
        ok("atencao", "Dependente sem titular na base",
           f"{len(orfaos)} dependente(s) cadastrado(s) sem o titular em {br_data(referencia[:10])}: "
           + ", ".join(p["pessoa"] for p in orfaos) + ".")

    # mínimo aplicado
    if any("Complemento" in i["descricao"] for n in r["notas"] for i in n["itens"]):
        ok("info", "Mínimo contratual aplicado", f"A base ficou abaixo de {ficha['minimo_vidas']} vidas; a nota inclui o complemento.")
    return avisos


def comparar_com_anterior(atual, anterior):
    """Para o CS: o que mudou em relação ao mês anterior, pessoa a pessoa."""
    if anterior is None:
        return None
    antes = {l["pessoa"]: l for l in anterior["pessoas"]}
    agora = {l["pessoa"]: l for l in atual["pessoas"]}
    entraram = [agora[p] for p in agora if p not in antes]
    sairam = [antes[p] for p in antes if p not in agora]
    trocaram = [{"pessoa": p, "de": antes[p]["plano"], "para": agora[p]["plano"]}
                for p in agora if p in antes and antes[p]["plano"] != agora[p]["plano"]]
    variacao = atual["quantidade"] - anterior["quantidade"]
    c = {"competencia_anterior": anterior["competencia"], "quantidade_anterior": anterior["quantidade"],
         "total_anterior": anterior["total"], "entraram": entraram, "sairam": sairam, "trocaram_de_plano": trocaram,
         "variacao_quantidade": variacao, "variacao_valor": round(atual["total"] - anterior["total"], 2)}
    return c


# ---------------------------------------------------------------- 8. formatação em português

def br_num(n):
    if isinstance(n, float) and n != int(n):
        return f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{int(n):,}".replace(",", ".")


def br_reais(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def br_data(iso):
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


def br_data_hora(iso):
    return f"{br_data(iso)} às {iso[11:13]}h"


MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro"]


def br_mes(competencia):
    return f"{MESES[int(competencia[5:]) - 1]} de {competencia[:4]}"


# ---------------------------------------------------------------- 9. tudo junto

def rodar():
    dados = carregar()
    config = json.loads(FICHAS.read_text(encoding="utf-8"))
    conv, fichas = config["convencoes"], config["contratos"]
    periodos = montar_periodos(dados)
    for ficha in fichas:  # antes de calcular qualquer nota
        exigir_cobravel(ficha)

    fechamentos = []
    for ficha in fichas:
        anterior = fechar(ficha, "2026-07", periodos, dados, conv)  # só para comparar com agosto
        meses = COMPETENCIAS + (["2026-11"] if ficha["apuracao"].get("mes") == "anterior" else [])
        for competencia in meses:
            atual = fechar(ficha, competencia, periodos, dados, conv)
            atual["comparacao"] = comparar_com_anterior(atual, anterior)
            fechamentos.append(atual)
            anterior = atual
    return {"convencoes": conv, "fichas": fichas, "fechamentos": fechamentos}


if __name__ == "__main__":
    resultado = rodar()
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'cliente':<20}{'competência':<13}{'faturado':>12}{'regra':>12}{'diferença':>12}  alertas")
    for f in resultado["fechamentos"]:
        print(f"{f['cliente']:<20}{f['competencia']:<13}{f['faturado']['total']:>12.2f}{f['total']:>12.2f}"
              f"{f['diferenca']:>12.2f}  {len(f['alertas'])}")
    print(f"\ngravado em {SAIDA.relative_to(RAIZ)}")
