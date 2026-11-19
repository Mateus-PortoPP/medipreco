"""O protótipo rodando no navegador.

Uso:  python3 prototipo/servidor.py        (depois abra http://localhost:8000; o navegador abre sozinho)

O servidor não guarda páginas prontas. Ele roda o motor e monta as telas na hora:
  - quando você abre a primeira página;
  - sempre que contratos.json ou dados/base.sqlite mudam (edite a ficha e recarregue a página);
  - quando você clica em "Recalcular".
Em /conferencias ele roda o testes.py e mostra o resultado.

Só usa a biblioteca padrão do Python. Para parar: Ctrl+C.
"""
import functools
import json
import subprocess
import sys
import time
import webbrowser
from datetime import datetime
import re
from html import escape, unescape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import parse_qs, quote, urlsplit

import gerar_site
import motor

print = functools.partial(print, flush=True)  # o terminal mostra cada linha na hora

PORTAS = range(8000, 8011)
ASSETS = motor.RAIZ / "site" / "assets"
TIPOS = {".webp": "image/webp", ".png": "image/png", ".svg": "image/svg+xml", ".css": "text/css"}

ESTILO = """<style>
.barra{background:var(--deep);color:#c9d6e3;font-size:13px}
.barra>div{max-width:1120px;margin:0 auto;padding:10px 24px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.barra .ponto{display:inline-block;width:8px;height:8px;border-radius:50%;background:#3ddc84;margin-right:8px}
.barra .ponto.erro{background:#ff6b5e}
.barra form{margin:0}.barra .estado{flex:1 1 420px;min-width:0}
.barra .acoes{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}
.barra button,.barra a.botao{font:inherit;font-weight:600;cursor:pointer;border-radius:999px;padding:5px 14px;
  border:1px solid #ffffff44;background:transparent;color:#fff;text-decoration:none}
.barra button:hover,.barra a.botao:hover{border-color:var(--ciano);color:var(--ciano);background:transparent}
.conf{list-style:none;margin:0;padding:0}
.conf li{display:flex;gap:12px;padding:10px 0;border-top:1px solid var(--borda);align-items:baseline}
.conf li:first-child{border-top:0}
.conf .marca{flex:none;font-weight:700;font-size:13px;border-radius:999px;padding:1px 10px}
.conf .ok{background:#e3f6ec;color:#16653a}.conf .falhou{background:#fde8e6;color:var(--erro)}
.conf .detalhe{color:var(--escuro);font-size:13px}
.botao-volta{display:inline-block;font-weight:600;color:var(--ciano-texto);text-decoration:none;border:1px solid var(--borda);
  border-radius:999px;padding:8px 18px;background:var(--branco)}.botao-volta:hover{border-color:var(--ciano-cta)}
pre.erro{white-space:pre-wrap;background:#fde8e6;color:var(--erro);padding:16px;border-radius:12px;font-size:13px}
</style>"""


# ---------------------------------------------------------------- cálculo

def segundos(x):
    return f"{x:.2f}".replace(".", ",") + " s"


class Calculo:
    """Guarda as páginas do último cálculo e refaz quando as entradas mudam."""

    def __init__(self):
        self.trava = Lock()
        self.marca = None
        self.paginas, self.erro, self.quando, self.duracao, self.resumo = {}, None, None, 0.0, ""

    @staticmethod
    def entradas():
        return tuple(p.stat().st_mtime_ns for p in (motor.FICHAS, motor.BANCO))

    def garantir(self, forcar=False):
        with self.trava:
            marca = self.entradas()
            if not forcar and marca == self.marca:
                return
            inicio = time.perf_counter()
            try:
                r = motor.rodar()
                gerar_site.BARRA = ""  # as páginas guardadas ficam sem barra
                self.paginas = gerar_site.paginas(r)
                self.erro = None
                f = r["fechamentos"]
                notas = sum(len(x["notas"]) for x in f)
                self.resumo = f"{len(r['fichas'])} contratos, {len(f)} fechamentos, {notas} notas"
            except Exception as e:  # ficha editada com erro: mostra o erro em vez de derrubar o servidor
                self.erro = f"{type(e).__name__}: {e}"
                self.paginas = {}
            self.duracao = time.perf_counter() - inicio
            self.quando = datetime.now()
            self.marca = marca
            print(f"  [{self.quando:%H:%M:%S}] fechamento calculado em {segundos(self.duracao)}"
                  + (f" — ERRO: {self.erro}" if self.erro else f" — {self.resumo}"))


calculo = Calculo()


def barra(caminho):
    if calculo.erro:
        estado = '<span class="estado"><span class="ponto erro"></span>O cálculo falhou. Veja o erro abaixo.</span>'
    else:
        estado = (f'<span class="estado"><span class="ponto"></span>Calculado às {calculo.quando:%H:%M:%S}, em '
                  f'{segundos(calculo.duracao)}, de <code>contratos.json</code> e da base: {calculo.resumo}.</span>')
    return (ESTILO + f'<div class="barra"><div>{estado}<span class="acoes">'
            f'<form method="post" action="/recalcular"><input type="hidden" name="volta" value="{escape(caminho)}">'
            f'<button type="submit">Recalcular</button></form>'
            f'<a class="botao" href="/conferencias?volta={quote(caminho)}">Rodar as conferências</a></span></div></div>')


def pagina_simples(titulo, capa, corpo, caminho, volta=None):
    """Páginas do servidor (conferências, erro, não encontrado). Sempre com uma saída na faixa do topo."""
    gerar_site.BARRA = barra(caminho)
    meses = sorted(n[4:-5] for n in calculo.paginas if n.startswith("mes-"))
    destino = (volta, titulo_da_pagina(volta)) if volta else ("/", "Fechamento do mês")
    return gerar_site.pagina(titulo, capa, corpo, meses, None, gerar_site.trilho(destino, titulo, []))


# ---------------------------------------------------------------- conferências

def destino_seguro(volta):
    """Só aceita voltar para uma página deste servidor."""
    return volta if volta.startswith("/") and not volta.startswith("//") else "/"


def titulo_da_pagina(caminho):
    html = calculo.paginas.get(caminho.lstrip("/") or "index.html", "")
    achado = re.search(r"<title>(.*?)</title>", html)
    return unescape(achado.group(1)) if achado else "o fechamento"


def conferencias(caminho, volta="/"):
    inicio = time.perf_counter()
    proc = subprocess.run([sys.executable, str(motor.RAIZ / "testes.py")], cwd=motor.RAIZ,
                          capture_output=True, text=True)
    duracao = time.perf_counter() - inicio
    grupos, atual = [], None
    for linha in proc.stdout.splitlines():
        if len(linha) > 2 and linha[1:3] == ". " and linha[0].isalpha():
            atual = {"titulo": linha, "itens": []}
            grupos.append(atual)
        elif atual is not None and linha.startswith(("  ok", "  FALHOU")):
            ok = linha.startswith("  ok")
            texto = linha[8:].strip()
            nome, _, detalhe = texto.partition("  [")
            atual["itens"].append((ok, nome, detalhe.rstrip("]")))
    total = sum(len(g["itens"]) for g in grupos)
    falhas = sum(1 for g in grupos for ok, *_ in g["itens"] if not ok)
    print(f"  [{datetime.now():%H:%M:%S}] conferências: {total - falhas} de {total} ok em {segundos(duracao)}")

    blocos = []
    for g in grupos:
        itens = "".join(
            f'<li><span class="marca {"ok" if ok else "falhou"}">{"ok" if ok else "falhou"}</span>'
            f'<span>{escape(nome)}' + (f'<br><span class="detalhe">{escape(det)}</span>' if det else "") + "</span></li>"
            for ok, nome, det in g["itens"])
        blocos.append(f'<h2>{escape(g["titulo"])}</h2><section class="cartao"><ul class="conf">{itens}</ul></section>')
    if proc.returncode != 0 and not grupos:
        blocos.append(f'<pre class="erro">{escape(proc.stderr or proc.stdout)}</pre>')

    resultado = "Tudo certo" if proc.returncode == 0 else f"{falhas} falha(s)"
    capa = (f'<h1>{resultado}: {total - falhas} de {total} conferências</h1>'
            f'<p>Rodou em {segundos(duracao)}. O motor é recalculado do zero e comparado com o que já foi emitido, '
            f'com uma segunda conta em SQL e com o que cada público precisa ver.</p>')
    blocos.append(f'<p style="margin-top:32px"><a class="botao-volta" href="{escape(volta)}">← Voltar para {escape(titulo_da_pagina(volta))}</a></p>')
    return pagina_simples("Conferências", capa, "".join(blocos), volta, volta)  # rodar de novo mantém o destino da volta


def pagina_de_erro(caminho):
    capa = '<h1>O cálculo não rodou</h1><p>Provavelmente a última edição de <code>contratos.json</code> deixou o arquivo inválido.</p>'
    corpo = (f'<section class="cartao"><pre class="erro">{escape(calculo.erro)}</pre>'
             '<p>Corrija o arquivo e recarregue a página. O servidor recalcula sozinho.</p></section>')
    return pagina_simples("Erro no cálculo", capa, corpo, caminho)


# ---------------------------------------------------------------- HTTP

class Pedido(BaseHTTPRequestHandler):
    def responder(self, codigo, conteudo, tipo="text/html; charset=utf-8"):
        dados = conteudo.encode("utf-8") if isinstance(conteudo, str) else conteudo
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        caminho = self.path.split("?")[0]
        nome = caminho.lstrip("/") or "index.html"

        if nome.startswith("assets/"):
            arquivo = (ASSETS / nome[len("assets/"):]).resolve()
            if arquivo.parent == ASSETS.resolve() and arquivo.is_file():
                return self.responder(200, arquivo.read_bytes(), TIPOS.get(arquivo.suffix, "application/octet-stream"))
            return self.responder(404, "não encontrado", "text/plain; charset=utf-8")

        calculo.garantir()
        if nome == "conferencias":
            volta = destino_seguro(parse_qs(urlsplit(self.path).query).get("volta", ["/"])[0])
            return self.responder(200, conferencias(caminho, volta))
        if calculo.erro:
            return self.responder(500, pagina_de_erro(caminho))
        if nome in calculo.paginas and nome.endswith(".csv"):  # o arquivo das notas para emitir
            return self.responder(200, calculo.paginas[nome], "text/csv; charset=utf-8")
        if nome in calculo.paginas:
            gerar_site.BARRA = barra(caminho)
            # as páginas são montadas sem a barra; ela é posta aqui, com o estado do cálculo
            html = calculo.paginas[nome].replace("</header>\n\n", "</header>\n" + gerar_site.BARRA + "\n", 1)
            return self.responder(200, html)
        return self.responder(404, pagina_simples("Não encontrado", "<h1>Página não encontrada</h1>",
                                                  '<p><a href="/">Voltar para o fechamento</a></p>', caminho))

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        corpo = self.rfile.read(tamanho).decode("utf-8")
        if self.path == "/recalcular":
            calculo.garantir(forcar=True)
            volta = parse_qs(corpo).get("volta", ["/"])[0]
            volta = destino_seguro(volta)
            self.send_response(303)
            self.send_header("Location", volta)
            self.end_headers()
            return
        self.responder(404, "não encontrado", "text/plain; charset=utf-8")

    def log_message(self, formato, *args):  # silencia o log padrão; o cálculo já imprime o que importa
        pass


def main():
    if not motor.BANCO.exists():
        raise SystemExit(
            f"Falta a base do kit. Copie o arquivo base.sqlite do zip do case para {motor.BANCO} "
            "e rode de novo (veja o README)."
        )
    for porta in PORTAS:
        try:
            servidor = ThreadingHTTPServer(("127.0.0.1", porta), Pedido)
            break
        except OSError:
            continue
    else:
        sys.exit(f"As portas {PORTAS.start} a {PORTAS.stop - 1} estão ocupadas.")

    endereco = f"http://localhost:{porta}"
    print(f"\nFechamento do mês — protótipo\n\n  Abra {endereco}\n")
    calculo.garantir()
    print("\n  Edite contratos.json e recarregue a página para ver a nota mudar. Ctrl+C para parar.\n")
    if "--sem-navegador" not in sys.argv:
        webbrowser.open(endereco)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor parado.")


if __name__ == "__main__":
    main()
