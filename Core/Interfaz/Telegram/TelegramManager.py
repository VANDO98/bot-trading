import time
import threading
import requests
from colorama import Fore
from .Comandos import GestorComandos

class TelegramManager:
    def __init__(self, token, admin_id, bot_controller):
        self.token = token
        self.admin_id = str(admin_id)
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.bot_controller = bot_controller
        self.gestor_comandos = GestorComandos(bot_controller)
        
        self.running = False
        self.thread = None
        self.last_update_id = 0

    def iniciar(self):
        if not self.token or not self.admin_id:
            print(Fore.RED + "❌ Telegram no configurado (Falta TOKEN o ID).")
            return

        self.running = True
        self.thread = threading.Thread(target=self._loop_polling, daemon=True)
        self.thread.start()
        print(Fore.GREEN + "📡 Telegram Manager: ONLINE")
        self.enviar_mensaje(self.admin_id, "🚀 **BinanceBot Reiniciado**\nSistema listo y escuchando.\nUsa /help para ver lista de comandos.")
        

    def detener(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _loop_polling(self):
        while self.running:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._procesar_mensaje(update)
                    self.last_update_id = update["update_id"] + 1
                time.sleep(2)
            except Exception as e:
                print(Fore.RED + f"⚠️ Error Telegram: {e}")
                time.sleep(5)

    def _get_updates(self):
        params = {"offset": self.last_update_id, "timeout": 30}
        try:
            resp = requests.get(f"{self.api_url}/getUpdates", params=params, timeout=40)
            if resp.status_code == 200:
                return resp.json().get("result", [])
        except:
            return []
        return []

    def _procesar_mensaje(self, update):
        msg = update.get("message")
        if not msg: return
        
        remitente_id = str(msg["chat"]["id"])
        texto = msg.get("text", "")

        if remitente_id != self.admin_id:
            print(Fore.YELLOW + f"🚫 Intruso bloqueado en Telegram: {remitente_id}")
            return

        if texto.startswith("/"):
            partes = texto.split()
            comando = partes[0]
            argumentos = partes[1:]
            
            print(Fore.CYAN + f"📩 Comando recibido: {texto}")
            self.gestor_comandos.ejecutar(
                comando, argumentos, remitente_id, 
                self.enviar_mensaje, 
                self.enviar_foto,
                self.enviar_documento
            )

    def enviar_mensaje(self, chat_id, texto):
        payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
        try:
            requests.post(f"{self.api_url}/sendMessage", data=payload)
        except Exception as e:
            print(f"Error enviando msg: {e}")

    def enviar_foto(self, chat_id, ruta_foto):
        payload = {"chat_id": chat_id}
        try:
            with open(ruta_foto, "rb") as f:
                archivos = {"photo": f}
                requests.post(f"{self.api_url}/sendPhoto", data=payload, files=archivos)
        except Exception as e:
            self.enviar_mensaje(chat_id, f"❌ Error enviando foto: {e}")

    def enviar_documento(self, chat_id, ruta_archivo):
        payload = {"chat_id": chat_id}
        try:
            with open(ruta_archivo, "rb") as f:
                archivos = {"document": f}
                requests.post(f"{self.api_url}/sendDocument", data=payload, files=archivos)
        except Exception as e:
            self.enviar_mensaje(chat_id, f"❌ Error enviando archivo: {e}")