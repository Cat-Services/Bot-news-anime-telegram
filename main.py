import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler

# --- 1. IMPORTACIONES Y CONFIGURACIÓN ---

from bot import start, recent, trending, search

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.critical("Variable de entorno TELEGRAM_BOT_TOKEN no encontrada.")
    raise ValueError("El TELEGRAM_BOT_TOKEN debe estar configurado.")

# --- 2. INICIALIZACIÓN DEL BOT Y FLASK ---

# Se crea un "cerrojo" para garantizar que la inicialización solo ocurra una vez.
init_lock = asyncio.Lock()

ptb_app = (
    Application.builder()
    .token(TELEGRAM_BOT_TOKEN)
    .build()
)

ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(CommandHandler("recent", recent))
ptb_app.add_handler(CommandHandler("trending", trending))
ptb_app.add_handler(CommandHandler("search", search))

app = Flask(__name__)

# --- 3. RUTAS DE FLASK (WEBHOOKS) ---

@app.route("/")
def index():
    return "Servidor Flask activo. El bot procesa actualizaciones vía /webhook."

@app.route("/webhook", methods=["POST"])
async def webhook():
    """
    Esta ruta procesa las actualizaciones de Telegram.
    La primera vez que se ejecuta, inicializa la aplicación del bot de forma segura.
    """
    logger.info("Webhook recibido...")
    try:
        # Adquiere el cerrojo para evitar que múltiples peticiones inicialicen la app a la vez.
        async with init_lock:
            # Si la app no está inicializada, la inicializa. Esto solo pasará una vez.
            if not ptb_app.initialized:
                logger.info("Inicializando la aplicación de PTB...")
                await ptb_app.initialize()
                logger.info("Aplicación de PTB inicializada.")

        update_data = request.get_json(force=True)
        update = Update.de_json(update_data, ptb_app.bot)
        
        await ptb_app.process_update(update)
        
        logger.info("Webhook procesado exitosamente.")
        return "ok"
    except Exception as e:
        logger.error(f"Error al procesar el webhook: {e}", exc_info=True)
        return "error", 500
