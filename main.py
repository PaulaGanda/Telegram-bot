"""
STREETWEAR FINDER BOT 🔥
========================
INSTALAÇÃO (1 vez):
  pip install python-telegram-bot requests

CORRER:
  python streetwear_bot.py

CONFIGURAÇÃO: muda o TOKEN abaixo pelo teu token do @BotFather
"""

import logging
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ─────────────────────────────────────────
# CONFIGURAÇÃO — MUDA AQUI
# ─────────────────────────────────────────
import os
TOKEN = os.environ.get("TOKEN", "8676778196:AAHDuib3WLEyBFab-yiwqxdrvGnjEXv0zNM")
MARGEM_REVENDA = 2.5   # multiplica o custo total por este valor
# ─────────────────────────────────────────

logging.basicConfig(level=logging.INFO)

PESOS = {
    "tenis": 0.9, "sneaker": 0.9, "shoe": 0.9, "boot": 0.9,
    "casaco": 0.6, "jacket": 0.6, "hoodie": 0.5, "sweater": 0.5,
    "calca": 0.45, "pants": 0.45, "jeans": 0.5, "shorts": 0.3,
    "tshirt": 0.25, "tee": 0.25, "shirt": 0.3,
    "cap": 0.15, "hat": 0.15, "bone": 0.15,
    "bag": 0.4, "mochila": 0.5, "backpack": 0.5,
}

def estimar_peso(produto: str) -> float:
    p = produto.lower()
    for k, v in PESOS.items():
        if k in p:
            return v
    return 0.3  # default

def get_taxa_cambio() -> float:
    try:
        r = requests.get("https://open.er-api.com/v6/latest/CNY", timeout=5)
        return r.json()["rates"]["EUR"]
    except:
        return 0.128  # fallback fixo

def buscar_produtos(query: str) -> list:
    """Busca gratuita via DuckDuckGo scraping leve"""
    resultados = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        # Busca no Weidian via DDG
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query + ' site:weidian.com OR site:taobao.com preco')}"
        r = requests.get(url, headers=headers, timeout=8)
        from html.parser import HTMLParser

        class LinkParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links = []
                self.titles = []
                self._cur_title = ""
                self._in_title = False

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and "href" in attrs:
                    href = attrs["href"]
                    if "weidian.com" in href or "taobao.com" in href or "1688.com" in href:
                        self.links.append(href)
                        self._in_title = True

            def handle_data(self, data):
                if self._in_title:
                    self._cur_title += data

            def handle_endtag(self, tag):
                if tag == "a" and self._in_title:
                    self.titles.append(self._cur_title.strip())
                    self._cur_title = ""
                    self._in_title = False

        parser = LinkParser()
        parser.feed(r.text)

        for i, link in enumerate(parser.links[:3]):
            title = parser.titles[i] if i < len(parser.titles) else query
            resultados.append({"titulo": title or query, "link": link})

    except Exception as e:
        logging.warning(f"Busca falhou: {e}")

    # Se não encontrou nada, gera links de pesquisa diretos
    if not resultados:
        q = requests.utils.quote(query)
        resultados = [
            {"titulo": f"{query} - Weidian", "link": f"https://weidian.com/?search={q}"},
            {"titulo": f"{query} - Taobao", "link": f"https://s.taobao.com/search?q={q}"},
            {"titulo": f"{query} - 1688",   "link": f"https://s.1688.com/selloffer/offer_search.htm?keywords={q}"},
        ]
    return resultados

def calcular(preco_cny: float, peso: float, taxa: float) -> dict:
    preco_eur   = round(preco_cny * taxa, 2)
    frete       = round(peso * 18, 2)           # ~€18/kg EMS China→PT
    subtotal    = preco_eur + frete
    imposto     = round(subtotal * 0.23, 2) if subtotal > 45 else 0.0
    total_pt    = round(subtotal + imposto, 2)
    revenda     = round((total_pt * MARGEM_REVENDA) / 5) * 5  # arredonda p/ múltiplo de 5
    return {
        "preco_eur": preco_eur,
        "frete": frete,
        "imposto": imposto,
        "total_pt": total_pt,
        "revenda": revenda,
    }

def gerar_resposta(produto: str, resultados: list, calc: dict, taxa: float) -> str:
    melhor = resultados[0] if resultados else None
    outras = "\n".join(f"  • <a href='{r['link']}'>{r['titulo'][:40]}...</a>" for r in resultados[1:]) or "  Sem mais resultados"

    qc_link = ""
    if melhor:
        qc_link = f"https://www.ufinds.net/?url={requests.utils.quote(melhor['link'])}"

    imposto_str = f"€{calc['imposto']} (IVA)" if calc['imposto'] > 0 else "Isento (valor < €45)"

    return f"""🔥 <b>{produto.upper()}</b>

💰 Estimativa preço: ~€{calc['preco_eur']} <i>(câmbio: 1 CNY = €{round(taxa,4)})</i>
📦 Peso estimado: {estimar_peso(produto)}kg
🚚 Frete estimado: ~€{calc['frete']}
🏛 Importação PT: {imposto_str}
✅ <b>Total estimado PT: ~€{calc['total_pt']}</b>
🏷 Revenda sugerida: <b>€{calc['revenda']}</b>

🔗 <b>Resultado principal:</b>
{"<a href='" + melhor['link'] + "'>" + melhor['titulo'][:50] + "</a>" if melhor else "Sem resultado direto"}

📉 <b>Outras opções:</b>
{outras}

{"📸 <b>Ver QC:</b> <a href='" + qc_link + "'>UFinds QC</a>" if melhor else ""}

⚠️ <i>Preços são estimativas. Confirma sempre stock e peso real antes de encomendar.</i>"""

# ──────────────────────────────────────────
# HANDLERS
# ──────────────────────────────────────────

GREETINGS = {"oi", "olá", "ola", "hey", "hi", "start", "hello", "boas", "/start"}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    # Saudação
    if msg.text and msg.text.strip().lower() in GREETINGS:
        await msg.reply_text("O que você procura para seu outfit hoje? 😏🔥")
        return

    # Imagem — extrair caption ou pedir descrição
    if msg.photo:
        produto = msg.caption if msg.caption else None
        if not produto:
            await msg.reply_text("📸 Foto recebida! Descreve o produto na legenda (ex: 'Nike TN preto') para eu procurar. 👇")
            return
    elif msg.text:
        produto = msg.text.strip()
    else:
        await msg.reply_text("Envia o nome do produto ou uma foto com legenda 👟")
        return

    await msg.reply_text(f"🔍 A procurar <b>{produto}</b>... aguarda um segundo!", parse_mode="HTML")

    try:
        taxa      = get_taxa_cambio()
        resultados = buscar_produtos(produto)
        peso      = estimar_peso(produto)
        # Preço base estimado: sem preço real, usamos média por categoria
        preco_cny_estimado = {0.9: 350, 0.6: 180, 0.5: 140, 0.45: 120, 0.3: 80, 0.25: 60, 0.15: 45, 0.4: 150}.get(peso, 100)
        calc      = calcular(preco_cny_estimado, peso, taxa)
        resposta  = gerar_resposta(produto, resultados, calc, taxa)
        await msg.reply_text(resposta, parse_mode="HTML", disable_web_page_preview=False)
    except Exception as e:
        logging.error(e)
        await msg.reply_text("❌ Erro na pesquisa. Tenta novamente com outro nome.")

# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────

def main():
    print("🤖 Bot a iniciar...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("✅ Bot online! Abre o Telegram e envia 'oi'")
    app.run_polling()

if __name__ == "__main__":
    main()
