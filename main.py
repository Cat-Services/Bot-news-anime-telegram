
import logging
import threading
from flask import Flask
from bot import run_bot

# --- CONFIGURACIÓN DE LOGGING ---
# Configuración básica para ver logs en la salida de Gunicorn
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- FLASK APP ---
app = Flask(__name__)

@app.route("/")
def index():
    """Una ruta simple para confirmar que el servidor web está funcionando."""
    logger.info("Ruta principal del servidor web accedida.")
    return "Servidor web en línea. El bot debería estar activo."

# --- HILO DEL BOT ---
def start_bot_in_thread():
    """Función para ejecutar el bot en un hilo separado."""
    logger.info("Iniciando el hilo del bot...")
    try:
        run_bot()
    except Exception as e:
        logger.critical(f"El hilo del bot falló con un error crítico: {e}", exc_info=True)

# --- INICIO ---
# Gunicorn cargará este archivo y verá el objeto 'app'.
# El código a continuación se ejecutará una vez por cada proceso de Gunicorn.
logger.info("Iniciando hilo de fondo para el bot de Telegram.")
bot_thread = threading.Thread(target=start_bot_in_thread)
bot_thread.daemon = True
bot_thread.start()

# Esta parte es solo para desarrollo local (cuando ejecutas 'python main.py')
# Gunicorn no usa esto.
if __name__ == "__main__":
    logger.info("Ejecutando Flask en modo de depuración para desarrollo local.")
    # Nota: El recargador de Flask hará que el hilo del bot se inicie dos veces. Esto es normal.
    app.run(debug=True, host="0.0.0.0", port=8080)
