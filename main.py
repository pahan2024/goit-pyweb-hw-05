import sys
import asyncio
import logging
from datetime import datetime, timedelta
import aiohttp

# Базове логування для відлову помилок мережі у консолі
logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s"
)


class DateProvider:
    """Генерує список дат у форматі ДД.ММ.РРРР за останні N днів."""

    @staticmethod
    def get_past_dates(days: int) -> list[str]:
        dates = []
        today = datetime.now()
        for i in range(days):
            date_obj = today - timedelta(days=i)
            dates.append(date_obj.strftime("%d.%m.2024"))
        return dates


class PrivatBankClient:
    """Відповідає виключно за виконання мережевих запитів до API ПриватБанку."""

    BASE_URL = "https://api.privatbank.ua/p24api/exchange_rates?json=true&date="

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def fetch_rates_for_date(self, date: str) -> dict | None:
        url = f"{self.BASE_URL}{date}"
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                logging.error(f"Помилка API для дати {date}: Статус {response.status}")
        except aiohttp.ClientConnectorError as e:
            logging.error(f"Помилка з'єднання під час запиту за {date}: {e}")
        except asyncio.TimeoutError:
            logging.error(f"Таймаут запиту для дати {date}")
        except Exception as e:
            logging.error(f"Непередбачувана помилка для дати {date}: {e}")
        return None


class CurrencyFormatter:
    """Фільтрує та форматує сирі дані від API у фінальний формат."""

    def __init__(self, target_currencies: list[str] = None):
        # За замовчуванням беремо USD та EUR, але можна передати й інші (Додаткова частина #1)
        self.target_currencies = target_currencies or ["USD", "EUR"]

    def format(self, raw_data: dict) -> dict | None:
        if not raw_data or "exchangeRate" not in raw_data:
            return None

        date = raw_data.get("date")
        rates_dict = {}

        for rate in raw_data["exchangeRate"]:
            currency = rate.get("currency")
            if currency in self.target_currencies:
                # Використовуємо картковий курс, а якщо його немає — курс НБУ (saleRateNB)
                rates_dict[currency] = {
                    "sale": rate.get("saleRate", rate.get("saleRateNB")),
                    "purchase": rate.get("purchaseRate", rate.get("purchaseRateNB")),
                }

        return {date: rates_dict} if rates_dict else None


class CurrencyUtility:
    """(Фасад) для запуску з консолі."""

    def __init__(self, days: int, extra_currencies: list[str] = None):
        self.days = days
        self.currencies = ["USD", "EUR"] + (extra_currencies or [])

    async def run(self):
        dates = DateProvider.get_past_dates(self.days)

        async with aiohttp.ClientSession() as session:
            client = PrivatBankClient(session)
            formatter = CurrencyFormatter(self.currencies)

            tasks = [client.fetch_rates_for_date(date) for date in dates]
            raw_results = await asyncio.gather(*tasks)

            final_result = []
            for raw_data in raw_results:
                formatted = formatter.format(raw_data)
                if formatted:
                    final_result.append(formatted)

            import pprint

            pprint.pprint(final_result)


def parse_arguments() -> tuple[int, list[str]]:
    """Парсить аргументи командного рядка та валідує обмеження."""
    if len(sys.argv) < 2:
        print("Помилка: Вкажіть кількість днів. Приклад: py main.py 2")
        sys.exit(1)

    try:
        days = int(sys.argv[1])
        if days < 1 or days > 10:
            print("Помилка: Кількість днів повинна бути від 1 до 10.")
            sys.exit(1)
    except ValueError:
        print("Помилка: Кількість днів має бути цілим числом.")
        sys.exit(1)

    # Додаткові валюти -> наприклад: py main.py 2 PLN GBP
    extra_currencies = [curr.upper() for curr in sys.argv[2:]]
    return days, extra_currencies


if __name__ == "__main__":
    days_arg, extra_curr_arg = parse_arguments()
    asyncio.run(CurrencyUtility(days_arg, extra_curr_arg).run())
