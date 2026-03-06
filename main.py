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
    """Gera links diretos de pesquisa nas plataformas chinesas"""
    q = requests.utils.quote(query)
    return [
        {"titulo": f"{query} - Weidian", "link": f"https://weidian.com/?search={q}"},
        {"titulo": f"{query} - Taobao",  "link": f"https://s.taobao.com/search?q={q}"},
        {"titulo": f"{query} - 1688",    "link": f"https://s.1688.com/selloffer/offer_search.htm?keywords={q}"},
        {"titulo": f"{query} - Pandabuy","link": f"https://www.pandabuy.com/search?keyword={q}"},
    ]

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
    imposto_str = f"EUR {calc['imposto']} (IVA)" if calc['imposto'] > 0 else "Isento (valor menor que 45 EUR)"

    linhas = [
        f"🔥 {produto.upper()}",
        "",
        f"💰 Estimativa: ~EUR {calc['preco_eur']} (cambio: 1 CNY = EUR {round(taxa,4)})",
        f"📦 Peso estimado: {estimar_peso(produto)}kg",
        f"🚚 Frete estimado: ~EUR {calc['frete']}",
        f"🏛 Importacao PT: {imposto_str}",
        f"✅ Total estimado PT: ~EUR {calc['total_pt']}",
        f"🏷 Revenda sugerida: EUR {calc['revenda']}",
        "",
        "🔗 Pesquisar produto:",
    ]

    for r in resultados:
        linhas.append(f"• {r['titulo']}: {r['link']}")

    if resultados:
        qc = f"https://www.ufinds.net/?url={requests.utils.quote(resultados[0]['link'])}"
        linhas.append(f"\n📸 Ver QC: {qc}")

    linhas.append("\n⚠️ Precos sao estimativas. Confirma sempre stock antes de encomendar.")

    return "\n".join(linhas)

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
        await msg.reply_text(resposta)
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
