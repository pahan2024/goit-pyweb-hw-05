import asyncio
import logging
import websockets
from websockets import WebSocketServerProtocol
from aiopath import AsyncPath
from aiofile import async_open
from datetime import datetime
import aiohttp

# Імпортуємо логіку нашого клієнта з першого файлу
from main import PrivatBankClient, CurrencyFormatter, DateProvider

logging.basicConfig(level=logging.INFO)

class ChatLogger:
    """Асинхронне логування викликів команд у файл за допомогою aiofile та aiopath."""
    LOG_FILE = "exchange_commands.log"

    @classmethod
    async def log_command(cls, message: str):
        path = AsyncPath(cls.LOG_FILE)
        if not await path.exists():
            await path.touch()
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with async_open(cls.LOG_FILE, 'a', encoding='utf-8') as afp:
            await afp.write(f"[{timestamp}] Виконано команду: {message}\n")

class ChatServer:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connect')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnect')

    async def send_to_clients(self, message: str):
        if self.clients:
            await asyncio.gather(*[client.send(message) for client in self.clients])

    async def handle_exchange_command(self, ws: WebSocketServerProtocol, cmd_args: list[str]):
        """Обробка команди exchange всередині чату."""
        days = 1
        if cmd_args:
            try:
                days = int(cmd_args[0])
                if days < 1 or days > 10:
                    await ws.send("Система: Можна переглянути курс лише від 1 до 10 днів.")
                    return
            except ValueError:
                await ws.send("Система: Невірний формат днів. Використовуйте: exchange 2")
                return

        await ws.send(f"Система: Завантажую курс валют за останні {days} дн...")
        
        # Асинхронно логуємо команду у файл
        await ChatLogger.log_command(f"exchange {' '.join(cmd_args)}")

        # Робимо запит до API ПриватБанку через наш клієнт
        dates = DateProvider.get_past_dates(days)
        async with aiohttp.ClientSession() as session:
            client = PrivatBankClient(session)
            formatter = CurrencyFormatter(["USD", "EUR"])
            
            tasks = [client.fetch_rates_for_date(date) for date in dates]
            raw_results = await asyncio.gather(*tasks)
            
            # Форматуємо відповідь у текстовий вигляд для чату
            response_lines = ["📊 Поточний курс валют від ПриватБанку:"]
            for raw_data in raw_results:
                formatted = formatter.format(raw_data)
                if formatted:
                    for date, currencies in formatted.items():
                        response_lines.append(f"📅 Дата: {date}")
                        for curr, rates in currencies.items():
                            response_lines.append(f"  {curr} -> Купівля: {rates['purchase']}, Продаж: {rates['sale']}")
                else:
                    response_lines.append("⚠️ Не вдалося отримати дані для однієї з дат.")
            
            await ws.send("\n".join(response_lines))

    async def distribute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            cleaned_message = message.strip()
            
            if cleaned_message.startswith("exchange"):
                parts = cleaned_message.split()
                await self.handle_exchange_command(ws, parts[1:])
            else:
                await self.send_to_clients(f"{ws.remote_address}: {message}")

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distribute(ws)
        except websockets.ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

async def main():
    server = ChatServer()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # утримує сервер запущеним

if __name__ == '__main__':
    print("Сервер чату запущено на ws://localhost:8080")
    asyncio.run(main())
