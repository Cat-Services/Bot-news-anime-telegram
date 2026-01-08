
import os
import re
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Carga las variables de entorno desde .env
load_dotenv()

# --- CONFIGURACIÓN ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
KITSU_API_BASE_URL = "https://kitsu.io/api/edge"
LAST_ANIME_ID_FILE = "last_anime_id.txt"

# --- LÓGICA DEL BOT ---
def escape_markdown_v2(text: str) -> str:
    """Escapa los caracteres especiales para el formato MarkdownV2 de Telegram."""
    if not isinstance(text, str):
        return ""
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para el comando /start."""
    await update.message.reply_text(
        "¡Hola\! Soy tu bot de noticias de anime\.\n\n"
        "Puedes usar los siguientes comandos:\n"
        "• `/recent` \- Muestra los 5 animes más recientes\.\n"
        "• `/trending` \- Muestra los 5 animes más populares en emisión\.\n"
        "• `/search <nombre>` \- Busca un anime por su nombre\.",
        parse_mode='MarkdownV2'
    )

async def check_new_anime(context: ContextTypes.DEFAULT_TYPE):
    """(Tarea automática) Revisa si hay nuevos animes y notifica."""
    print("Revisando animes (tarea automática)... ")
    try:
        params = {"sort": "-createdAt", "page[limit]": 1}
        response = requests.get(f"{KITSU_API_BASE_URL}/anime", params=params)
        response.raise_for_status()
        animes = response.json().get("data", [])
        if not animes:
            print("Tarea automática: No se pudo obtener el anime más reciente de Kitsu.")
            return
        
        latest_anime = animes[0]
        latest_anime_id = int(latest_anime["id"])

        last_sent_id = 0
        if os.path.exists(LAST_ANIME_ID_FILE):
            with open(LAST_ANIME_ID_FILE, 'r') as f:
                content = f.read().strip()
                if content.isdigit():
                    last_sent_id = int(content)

        if latest_anime_id > last_sent_id:
            print(f"¡Nuevo anime encontrado! ID: {latest_anime_id}")
            attrs = latest_anime.get("attributes", {})
            title = escape_markdown_v2(attrs.get("canonicalTitle", "N/A"))
            synopsis = escape_markdown_v2((attrs.get("synopsis") or "No disponible")[:400])
            kitsu_link = f"https://kitsu.io/anime/{latest_anime_id}"
            poster = attrs.get("posterImage", {}).get("small")
            
            message_header = escape_markdown_v2("¡Hey! ¡Ha salido un nuevo anime en Kitsu!")
            message_body = f"*{title}*\n\n{synopsis}\.\.\.\n\n[Ver más en Kitsu]({kitsu_link})"
            
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_header, parse_mode='MarkdownV2')
            await context.bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=poster, caption=message_body, parse_mode='MarkdownV2')
            
            with open(LAST_ANIME_ID_FILE, 'w') as f:
                f.write(str(latest_anime_id))
        else:
            print("Tarea automática: No hay animes nuevos.")

    except Exception as e:
        print(f"Error en la tarea automática (check_new_anime): {e}")

async def recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para el comando /recent. Envía los 5 animes más recientes."""
    await update.message.reply_text("Buscando los 5 animes más recientes en Kitsu...")
    try:
        params = {"sort": "-createdAt", "page[limit]": 5}
        response = requests.get(f"{KITSU_API_BASE_URL}/anime", params=params)
        response.raise_for_status()
        animes = response.json().get("data", [])
        if not animes:
            await update.message.reply_text("No se pudieron obtener los animes recientes de Kitsu.")
            return
        await update.message.reply_text(f"Estos son los {len(animes)} animes más recientes:")
        for anime in animes:
            attrs = anime.get("attributes", {})
            title = escape_markdown_v2(attrs.get("canonicalTitle", "N/A"))
            synopsis = escape_markdown_v2((attrs.get("synopsis") or "No disponible")[:400])
            kitsu_link = f"https://kitsu.io/anime/{anime['id']}"
            poster = attrs.get("posterImage", {}).get("small")
            message = f"*{title}*\n\n{synopsis}\.\.\.\n\n[Ver más en Kitsu]({kitsu_link})"
            await context.bot.send_photo(chat_id=update.message.chat_id, photo=poster, caption=message, parse_mode='MarkdownV2')
    except Exception as e:
        print(f"Error en /recent: {e}")
        await update.message.reply_text("Ocurrió un error al buscar los animes recientes.")

async def trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /trending. Muestra los animes en emisión más populares."""
    await update.message.reply_text("Buscando los 5 animes más populares en emisión...")
    try:
        params = {
            "filter[status]": "current",
            "sort": "popularityRank",
            "page[limit]": 5
        }
        response = requests.get(f"{KITSU_API_BASE_URL}/anime", params=params)
        response.raise_for_status()
        animes = response.json().get("data", [])

        if not animes:
            await update.message.reply_text("No se pudieron obtener los animes populares en emisión de Kitsu.")
            return

        await update.message.reply_text(f"Estos son los {len(animes)} animes en emisión más populares del momento:")
        for anime in animes:
            attrs = anime.get("attributes", {})
            title = escape_markdown_v2(attrs.get("canonicalTitle", "N/A"))
            synopsis = escape_markdown_v2((attrs.get("synopsis") or "No disponible")[:400])
            kitsu_link = f"https://kitsu.io/anime/{anime['id']}"
            poster = attrs.get("posterImage", {}).get("small")
            caption = f"*{title}*\n\n{synopsis}\.\.\.\n\n[Ver más en Kitsu]({kitsu_link})"
            await context.bot.send_photo(chat_id=update.message.chat_id, photo=poster, caption=caption, parse_mode='MarkdownV2')

    except Exception as e:
        print(f"Error en /trending: {e}")
        await update.message.reply_text("Ocurrió un error al buscar los animes en tendencia.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /search. Lógica simplificada y robusta."""
    if not context.args:
        await update.message.reply_text("Por favor, dime qué anime quieres buscar. Ejemplo: /search Cowboy Bebop")
        return

    search_term = ' '.join(context.args)
    await update.message.reply_text(f'Buscando animes para "{search_term}"...')

    try:
        params = {"filter[text]": search_term, "page[limit]": 5}
        response = requests.get(f"{KITSU_API_BASE_URL}/anime", params=params)
        response.raise_for_status()
        animes = response.json().get("data", [])

        if not animes:
            await update.message.reply_text(f'No encontré ningún anime que coincida con "{search_term}".')
            return

        await update.message.reply_text(f'Encontré estos {len(animes)} resultados para "{search_term}":')
        for anime in animes:
            attrs = anime.get("attributes", {})
            title = escape_markdown_v2(attrs.get("canonicalTitle", "N/A"))
            synopsis = escape_markdown_v2((attrs.get("synopsis") or "No disponible")[:400])
            kitsu_link = f"https://kitsu.io/anime/{anime['id']}"
            poster = attrs.get("posterImage", {}).get("small")
            caption = f"*{title}*\n\n{synopsis}\.\.\.\n\n[Ver más en Kitsu]({kitsu_link})"
            await context.bot.send_photo(chat_id=update.message.chat_id, photo=poster, caption=caption, parse_mode='MarkdownV2')

    except Exception as e:
        print(f"Error en /search: {e}")
        await update.message.reply_text("Ocurrió un error al realizar la búsqueda.")

def main():
    """Configura y ejecuta el bot de Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: La variable de entorno TELEGRAM_BOT_TOKEN no está configurada.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("recent", recent))
    application.add_handler(CommandHandler("trending", trending))
    application.add_handler(CommandHandler("search", search))
    
    job_queue = application.job_queue
    job_queue.run_repeating(check_new_anime, interval=3600, first=10)

    print("Bot completamente restaurado. Iniciado y escuchando...")
    application.run_polling()

if __name__ == "__main__":
    main()
