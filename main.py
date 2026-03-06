"""
STREETWEAR FINDER BOT 🔥 — Formato AGTFIND
==========================================
pip install python-telegram-bot requests
"""

import logging
import requests
import os
import urllib.parse
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ─────────────────────────────────────────
TOKEN       = os.environ.get("TOKEN",      "8676778196:AAHDuib3WLEyBFab-yiwqxdrvGnjEXv0zNM")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY","01e2736ca798960313dcb269139ca1423eca613452be008e50e80eb52daebee4")
MARGEM      = 2.5
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

def estimar_peso(produto):
    p = produto.lower()
    for k, v in PESOS.items():
        if k in p:
            return v
    return 0.3

def get_taxa_cambio():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/CNY", timeout=5)
        rates = r.json()["rates"]
        return rates.get("EUR", 0.128), rates.get("USD", 0.138)
    except:
        return 0.128, 0.138

def buscar_weidian(query):
    try:
        params = {
            "engine": "google",
            "q": f"{query} site:weidian.com",
            "api_key": SERPAPI_KEY,
            "num": 5,
        }
        r = requests.get("https://serpapi.com/search", params=params, timeout=10)
        data = r.json()
        for result in data.get("organic_results", []):
            link = result.get("link", "")
            if "weidian.com" in link and "item" in link:
                return {"link": link, "titulo": result.get("title", query)}
    except Exception as e:
        logging.warning(f"Weidian search falhou: {e}")
    return {"link": None, "titulo": query}

def buscar_preco(query):
    try:
        params = {
            "engine": "google_shopping",
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": 3,
        }
        r = requests.get("https://serpapi.com/search", params=params, timeout=10)
        data = r.json()
        results = data.get("shopping_results", [])
        if results:
            return results[0].get("price", "")
    except Exception as e:
        logging.warning(f"Preco search falhou: {e}")
    return ""

def gerar_links(weidian_link, query):
    if weidian_link:
        encoded = urllib.parse.quote(weidian_link, safe="")
        item_id = weidian_link.split("itemID=")[-1].split("&")[0] if "itemID=" in weidian_link else ""
        return {
            "weidian":  weidian_link,
            "litbuy":   f"https://www.litbuy.com/product?url={encoded}",
            "mulebuy":  f"https://mulebuy.com/product/?url={encoded}",
            "oopbuy":   f"https://www.oopbuy.com/product/weidian/{item_id}",
            "kakobuy":  f"https://kakobuy.com/item/details/?url={encoded}",
            "sugargoo": f"https://www.sugargoo.com/#/home/productDetail?productLink={encoded}",
        }
    else:
        q = urllib.parse.quote(query)
        return {
            "weidian":  f"https://weidian.com/?search={q}",
            "litbuy":   f"https://www.litbuy.com/search?keyword={q}",
            "mulebuy":  f"https://mulebuy.com/search/?keyword={q}",
            "oopbuy":   f"https://www.oopbuy.com/search?keyword={q}",
            "kakobuy":  f"https://kakobuy.com/search?keyword={q}",
            "sugargoo": f"https://www.sugargoo.com/#/home/productSearch?searchInfo={q}",
        }

def calcular(peso, taxa_eur, taxa_usd, preco_raw):
    try:
        preco_cny = float(''.join(c for c in preco_raw if c.isdigit() or c == '.'))
    except:
        preco_cny = {0.9: 320, 0.6: 159, 0.5: 130, 0.45: 110, 0.3: 75, 0.25: 55, 0.15: 40, 0.4: 140}.get(peso, 100)

    preco_eur = round(preco_cny * taxa_eur, 2)
    preco_usd = round(preco_cny * taxa_usd, 2)
    frete     = round(peso * 18, 2)
    subtotal  = preco_eur + frete
    imposto   = round(subtotal * 0.23, 2) if subtotal > 45 else 0.0
    total_pt  = round(subtotal + imposto, 2)
    revenda   = round((total_pt * MARGEM) / 5) * 5
    return {
        "preco_cny": preco_cny,
        "preco_eur": preco_eur,
        "preco_usd": preco_usd,
        "frete": frete,
        "imposto": imposto,
        "total_pt": total_pt,
        "revenda": revenda,
    }

def formatar(produto, calc, links):
    imposto_str = f"EUR {calc['imposto']} (IVA)" if calc['imposto'] > 0 else "Isento"
    return (
        f"🏬 Article: {produto}\n"
        f"💴 Price: CNY{calc['preco_cny']} ~ EUR{calc['preco_eur']} ~ USD{calc['preco_usd']}\n"
        f"📦 Peso: {estimar_peso(produto)}kg | Frete: ~EUR{calc['frete']}\n"
        f"🏛 Importacao PT: {imposto_str}\n"
        f"✅ Total PT: ~EUR{calc['total_pt']}\n"
        f"🏷 Revenda sugerida: EUR{calc['revenda']}\n"
        f"\n"
        f"🏪 Weidian Link\n{links['weidian']}\n"
        f"\n"
        f"🟡 Go LITbuy Buy\n{links['litbuy']}\n"
        f"\n"
        f"🔴 Go Mulebuy Buy\n{links['mulebuy']}\n"
        f"\n"
        f"🟠 Go OOPBUY Buy\n{links['oopbuy']}\n"
        f"\n"
        f"🟢 Go Kakobuy Buy\n{links['kakobuy']}\n"
        f"\n"
        f"🔵 Go Sugargoo Buy\n{links['sugargoo']}\n"
        f"\n"
        f"⚠️ Precos sao estimativas. Confirma stock antes de encomendar."
    )

# ──────────────────────────────────────────
GREETINGS = {"oi", "ola", "olá", "hey", "hi", "start", "hello", "boas", "/start"}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    if msg.text and msg.text.strip().lower() in GREETINGS:
        await msg.reply_text("O que voce procura para seu outfit hoje? 😏🔥\n\nEnvia o nome do produto ou foto com o nome na legenda.")
        return

    if msg.photo:
        produto = msg.caption.strip() if msg.caption else None
        if not produto:
            await msg.reply_text("Foto recebida! Escreve o nome do produto na legenda e envia de novo.")
            return
    elif msg.text:
        produto = msg.text.strip()
    else:
        await msg.reply_text("Envia o nome do produto ou foto com legenda.")
        return

    await msg.reply_text(f"A procurar {produto}... aguarda!")

    try:
        taxa_eur, taxa_usd = get_taxa_cambio()
        peso               = estimar_peso(produto)
        weidian_result     = buscar_weidian(produto)
        weidian_link       = weidian_result["link"]
        preco_raw          = buscar_preco(produto)
        calc               = calcular(peso, taxa_eur, taxa_usd, preco_raw)
        links              = gerar_links(weidian_link, produto)
        resposta           = formatar(produto, calc, links)

        if msg.photo:
            await msg.reply_photo(photo=msg.photo[-1].file_id, caption=resposta)
        else:
            await msg.reply_text(resposta)

    except Exception as e:
        logging.error(e)
        await msg.reply_text("Erro na pesquisa. Tenta novamente.")

# ──────────────────────────────────────────
def main():
    print("Bot a iniciar...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    print("Bot online!")
    app.run_polling()

if __name__ == "__main__":
    main()
