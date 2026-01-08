
import os
import logging
import asyncio
import threading
from multiprocessing import Event
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler

# Importa los handlers del bot desde bot.py
from bot import start, recent, trending, search, check_new_anime

# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- VARIABLES DE ENTORNO ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

# --- EVENTO DE SINCRONIZACIÓN ---
# Esta bandera es visible entre el proceso maestro de Gunicorn y sus workers.
bot_initialized_event = Event()

# --- INICIALIZACIÓN DE LA APLICACIÓN DE TELEGRAM ---
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# --- INICIALIZACIÓN DE LA APLICACIÓN FLASK ---
app = Flask(__name__)

@app.route("/")
def index():
    """Ruta de salud para confirmar que el servidor está activo."""
    return "Servidor web activo. El bot se está ejecutando en un hilo de fondo."

@app.route("/webhook", methods=["POST"])
async def webhook():
    """Esta ruta recibe las actualizaciones de Telegram."""
    logger.info("Webhook recibido. Esperando a que el bot esté inicializado...")
    # Detiene la ejecución aquí hasta que el hilo de fondo llame a bot_initialized_event.set()
    # El timeout es una salvaguarda para no bloquear indefinidamente si algo sale mal.
    is_set = await asyncio.to_thread(bot_initialized_event.wait, timeout=30)
    
    if not is_set:
        logger.error("Timeout esperando la inicialización del bot. Abortando webhook.")
        return "Error: Timeout de inicialización", 500

    logger.info("Bot inicializado. Procesando actualización...")
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error procesando el webhook: {e}", exc_info=True)
    return "OK", 200

async def setup_and_start_bot():
    """
    Configura y arranca todo lo relacionado con el bot. Al final, levanta
    la bandera de 'bot_initialized_event' para notificar a los workers.
    """
    logger.info("1. Inicializando la aplicación del bot...")
    await application.initialize()
    logger.info("Aplicación inicializada.")

    logger.info("2. Registrando handlers de comandos...")
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("recent", recent))
    application.add_handler(CommandHandler("trending", trending))
    application.add_handler(CommandHandler("search", search))
    logger.info("Handlers registrados.")

    logger.info("3. Configurando el webhook...")
    if WEBHOOK_URL:
        webhook_full_url = f"{WEBHOOK_URL}/webhook"
        await application.bot.set_webhook(url=webhook_full_url, allowed_updates=Update.ALL_TYPES)
        logger.info(f"Webhook configurado en: {webhook_full_url}")
    else:
        logger.error("La variable RENDER_EXTERNAL_URL no está configurada.")

    logger.info("4. Registrando tareas programadas (jobs)...")
    if application.job_queue:
        application.job_queue.run_repeating(check_new_anime, interval=3600, first=10)
        logger.info("Job 'check_new_anime' registrado.")
    
    logger.info("5. Iniciando la aplicación del bot (para que la job_queue se ejecute)...")
    await application.start()
    logger.info("La aplicación del bot se ha iniciado.")
    
    logger.info("===> ¡BOT LISTO! Levantando bandera de inicialización para los workers. <===")
    bot_initialized_event.set()

def run_bot_in_background():
    """
    Se ejecuta en un hilo separado. Crea un nuevo loop de eventos de asyncio
    y lo mantiene vivo para las tareas de fondo del bot.
    """
    logger.info("Iniciando hilo de fondo para el bot...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(setup_and_start_bot())
        loop.run_forever()
    except Exception as e:
        logger.critical(f"Error crítico en el hilo de fondo del bot: {e}", exc_info=True)
    finally:
        logger.info("Cerrando el loop de eventos del bot.")
        loop.run_until_complete(application.stop())
        loop.run_until_complete(application.shutdown())
        loop.close()

# --- ARRANQUE ---
# Esto asegura que el hilo solo se inicie una vez en el proceso maestro de Gunicorn.
if __name__ != '__main__':
    if not any(t.name == 'BotThread' for t in threading.enumerate()):
        logger.info("Proceso maestro de Gunicorn detectado. Iniciando hilo del bot.")
        bot_thread = threading.Thread(target=run_bot_in_background, name='BotThread', daemon=True)
        bot_thread.start()
