
import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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
# La URL externa es proporcionada por Render
WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL")

# --- INICIALIZACIÓN DE LA APLICACIÓN DE TELEGRAM ---
# Se crea la aplicación del bot aquí para que esté disponible globalmente
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# --- INICIALIZACIÓN DE LA APLICACIÓN FLASK ---
app = Flask(__name__)

@app.route("/")
def index():
    """Ruta de salud para confirmar que el servidor está activo."""
    return "Servidor web y bot listos para recibir webhooks."

@app.route("/webhook", methods=["POST"])
async def webhook():
    """Esta ruta recibe las actualizaciones de Telegram."""
    # Convierte el cuerpo de la petición en un objeto Update de Telegram
    update = Update.de_json(request.get_json(force=True), application.bot)
    # Procesa la actualización. Esto ejecutará el handler de comando correspondiente.
    await application.process_update(update)
    return "OK", 200

async def setup_bot():
    """Configura el bot, los handlers y el webhook."""
    logger.info("Configurando handlers y webhook...")

    # 1. Registrar los handlers de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("recent", recent))
    application.add_handler(CommandHandler("trending", trending))
    application.add_handler(CommandHandler("search", search))

    # 2. Registrar la tarea programada
    application.job_queue.run_repeating(check_new_anime, interval=3600, first=10)

    # 3. Configurar el webhook
    # Le dice a Telegram a dónde enviar las actualizaciones.
    if WEBHOOK_URL:
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook", allowed_updates=Update.ALL_TYPES)
        logger.info(f"Webhook configurado en: {WEBHOOK_URL}/webhook")
    else:
        logger.error("La variable RENDER_EXTERNAL_URL no está configurada. No se pudo establecer el webhook.")

# --- ARRANQUE ---
# Esta lógica asegura que la configuración asíncrona se ejecute una sola vez
# cuando la aplicación de producción (Gunicorn) inicia.

# Ejecuta la configuración del bot antes de la primera petición en un entorno de producción.
# En un entorno de desarrollo simple, esto también funciona.
# Usamos un lock para evitar que se ejecute en cada proceso de Gunicorn.
setup_has_run = False
@app.before_request
def before_first_request_setup():
    global setup_has_run
    if not setup_has_run:
        # Ejecutar la función asíncrona en un loop de eventos
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_bot())
        loop.close()
        setup_has_run = True

# Esto es para desarrollo local (ejecutando 'python main.py')
if __name__ == '__main__':
    # En local, el webhook no es ideal. Se podría cambiar a polling para tests.
    logger.info("Ejecutando en modo de desarrollo local.")
    # La configuración se ejecutará antes de la primera petición.
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
