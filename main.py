import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler

# --- 1. IMPORTACIONES Y CONFIGURACIÓN ---

# Importa los manejadores de comandos desde tu archivo bot.py
from bot import start, recent, trending, search

# Configuración básica de logging para ver qué está pasando
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Obtiene el token del bot desde las variables de entorno
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.critical("Variable de entorno TELEGRAM_BOT_TOKEN no encontrada.")
    # En un entorno de producción, es mejor que la aplicación falle si falta el token.
    raise ValueError("El TELEGRAM_BOT_TOKEN debe estar configurado.")

# --- 2. INICIALIZACIÓN DEL BOT Y FLASK ---

# Inicializa la aplicación de python-telegram-bot (PTB)
# Esto se ejecutará una vez por cada worker que inicie Gunicorn.
ptb_app = (
    Application.builder()
    .token(TELEGRAM_BOT_TOKEN)
    .build()
)

# Registra los manejadores de comandos en la aplicación PTB
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(CommandHandler("recent", recent))
ptb_app.add_handler(CommandHandler("trending", trending))
ptb_app.add_handler(CommandHandler("search", search))

# Inicializa la aplicación Flask
app = Flask(__name__)


# --- 3. RUTAS DE FLASK (WEBHOOKS) ---

@app.route("/")
def index():
    """Ruta simple para verificar que el servidor web está activo."""
    return "Servidor Flask activo. El bot procesa actualizaciones vía /webhook."

@app.route("/webhook", methods=["POST"])
async def webhook():
    """
    Esta es la ruta clave. Telegram envía aquí las actualizaciones (comandos, mensajes, etc.).
    Es una función `async` para poder usar `await` con las funciones de PTB.
    """
    logger.info("Webhook recibido...")
    try:
        # Obtiene el cuerpo JSON de la petición
        update_data = request.get_json(force=True)
        
        # Convierte el JSON en un objeto `Update` de PTB
        update = Update.de_json(update_data, ptb_app.bot)
        
        # Procesa la actualización. PTB se encargará de buscar y ejecutar
        # el `CommandHandler` correcto que registramos antes.
        await ptb_app.process_update(update)
        
        logger.info("Webhook procesado exitosamente.")
        # Responde a Telegram con un código 200 OK para confirmar la recepción.
        return "ok"
    except Exception as e:
        logger.error(f"Error al procesar el webhook: {e}", exc_info=True)
        return "error", 500

# NOTA: Ya no necesitamos la lógica para configurar el webhook al inicio.
# El webhook ya está configurado en Telegram y apunta a esta URL.
# Esta nueva arquitectura es más simple y robusta para producción.
