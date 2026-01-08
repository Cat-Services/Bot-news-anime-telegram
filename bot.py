
import os
import re
import requests
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carga las variables de entorno desde .env (para desarrollo local)
load_dotenv()

# --- CONFIGURACIÓN DEL BOT ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
KITSU_API_BASE_URL = "https://kitsu.io/api/edge"
LAST_ANIME_ID_FILE = "/tmp/last_anime_id.txt" # Usar /tmp para compatibilidad con Render

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
    logger.info("Revisando animes (tarea automática)...")
    try:
        params = {"sort": "-createdAt", "page[limit]": 1}
        response = requests.get(f"{KITSU_API_BASE_URL}/anime", params=params)
        response.raise_for_status()
        animes = response.json().get("data", [])
        if not animes:
            logger.warning("Tarea automática: No se pudo obtener el anime más reciente de Kitsu.")
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
            logger.info(f"¡Nuevo anime encontrado! ID: {latest_anime_id}")
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
            logger.info("Tarea automática: No hay animes nuevos.")

    except Exception as e:
        logger.error(f"Error en la tarea automática (check_new_anime): {e}", exc_info=True)

async def recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para el comando /recent."""
    await update.message.reply_text("Buscando los 5 animes más recientes en Kitsu...")
    try:
        params = {"sort": "-createdAt", "page[limit]": 5}
        response = requests.get(f"{KITSU_API_BASE_URL}/anime", params=params)
        response.raise_for_status()
        animes = response.json().get("data", [])
        if not animes:
            await update.message.reply_text("No se pudieron obtener los animes recientes.")
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
        logger.error(f"Error en /recent: {e}", exc_info=True)
        await update.message.reply_text("Ocurrió un error al buscar los animes recientes.")

async def trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /trending."""
    await update.message.reply_text("Buscando los 5 animes más populares en emisión...")
    try:
        params = {"filter[status]": "current", "sort": "popularityRank", "page[limit]": 5}
        response = requests.get(f"{KITSU_API_BASE_URL}/anime", params=params)
        response.raise_for_status()
        animes = response.json().get("data", [])
        if not animes:
            await update.message.reply_text("No se pudieron obtener los animes populares.")
            return
        await update.message.reply_text(f"Estos son los {len(animes)} animes en emisión más populares:")
        for anime in animes:
            attrs = anime.get("attributes", {})
            title = escape_markdown_v2(attrs.get("canonicalTitle", "N/A"))
            synopsis = escape_markdown_v2((attrs.get("synopsis") or "No disponible")[:400])
            kitsu_link = f"https://kitsu.io/anime/{anime['id']}"
            poster = attrs.get("posterImage", {}).get("small")
            caption = f"*{title}*\n\n{synopsis}\.\.\.\n\n[Ver más en Kitsu]({kitsu_link})"
            await context.bot.send_photo(chat_id=update.message.chat_id, photo=poster, caption=caption, parse_mode='MarkdownV2')
    except Exception as e:
        logger.error(f"Error en /trending: {e}", exc_info=True)
        await update.message.reply_text("Ocurrió un error al buscar los animes en tendencia.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /search."""
    if not context.args:
        await update.message.reply_text("Uso: /search <nombre del anime>")
        return
    search_term = ' '.join(context.args)
    await update.message.reply_text(f'Buscando animes para "{search_term}"...')
    try:
        params = {"filter[text]": search_term, "page[limit]": 5}
        response = requests.get(f"{KITSU_API_BASE_URL}/anime", params=params)
        response.raise_for_status()
        animes = response.json().get("data", [])
        if not animes:
            await update.message.reply_text(f'No encontré resultados para "{search_term}".')
            return
        await update.message.reply_text(f'Encontré {len(animes)} resultados:')
        for anime in animes:
            attrs = anime.get("attributes", {})
            title = escape_markdown_v2(attrs.get("canonicalTitle", "N/A"))
            synopsis = escape_markdown_v2((attrs.get("synopsis") or "No disponible")[:400])
            kitsu_link = f"https://kitsu.io/anime/{anime['id']}"
            poster = attrs.get("posterImage", {}).get("small")
            caption = f"*{title}*\n\n{synopsis}\.\.\.\n\n[Ver más en Kitsu]({kitsu_link})"
            await context.bot.send_photo(chat_id=update.message.chat_id, photo=poster, caption=caption, parse_mode='MarkdownV2')
    except Exception as e:
        logger.error(f"Error en /search: {e}", exc_info=True)
        await update.message.reply_text("Ocurrió un error al realizar la búsqueda.")

def run_bot():
    """Configura y ejecuta el bot de Telegram."""
    logger.info("Iniciando configuración del bot...")
    
    # --- VERIFICACIÓN CRUCIAL DE VARIABLES DE ENTORNO ---
    if not TELEGRAM_BOT_TOKEN:
        logger.critical("FATAL: La variable de entorno TELEGRAM_BOT_TOKEN no está configurada.")
        return
    else:
        logger.info(f"TELEGRAM_BOT_TOKEN encontrado (comienza con: {TELEGRAM_BOT_TOKEN[:4]}...).")

    if not TELEGRAM_CHAT_ID:
        logger.critical("FATAL: La variable de entorno TELEGRAM_CHAT_ID no está configurada.")
        return
    else:
        logger.info("TELEGRAM_CHAT_ID encontrado.")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("recent", recent))
    application.add_handler(CommandHandler("trending", trending))
    application.add_handler(CommandHandler("search", search))
    
    job_queue = application.job_queue
    job_queue.run_repeating(check_new_anime, interval=3600, first=10)

    logger.info("Bot configurado. Iniciando polling...")
    application.run_polling()
    logger.info("El bot se ha detenido.")
