import aiohttp
import asyncio
from datetime import datetime, timedelta
import json

BASE_URL = "http://api.nbp.pl/api/exchangerates/rates/C/{}/{}?format=json"
CURRENCIES = ["EUR", "USD"]


class CurrencyRateFetcher:
    def __init__(self, session, currency):
        self.session = session
        self.currency = currency

    async def fetch_rate(self, date):
        url = BASE_URL.format(self.currency, date)
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    rate = {
                        "sale": data["rates"][0]["ask"],
                        "purchase": data["rates"][0]["bid"],
                    }
                    return rate
                elif response.status == 404:
                    return None
                else:
                    response.raise_for_status()
        except aiohttp.ClientError as e:
            print(f"Request failed: {e}")
            return None


class ExchangeRateService:
    def __init__(self):
        self.currency_rate_fetchers = []

    async def get_rates_for_last_days(self, days):
        async with aiohttp.ClientSession() as session:
            self.currency_rate_fetchers = [
                CurrencyRateFetcher(session, currency) for currency in CURRENCIES
            ]
            tasks = [
                self._fetch_rates_for_currency(fetcher, days)
                for fetcher in self.currency_rate_fetchers
            ]
            results = await asyncio.gather(*tasks)
            combined_results = self._combine_results(results, days)
            return combined_results

    async def _fetch_rates_for_currency(self, fetcher, days):
        rates = {}
        day_offset = 0
        while len(rates) < days and day_offset < days + 10:
            date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            rate = await fetcher.fetch_rate(date)
            if rate is not None:
                rates[date] = rate
            day_offset += 1
        return fetcher.currency, rates

    def _combine_results(self, results, days):
        combined_results = []
        dates = sorted(set(date for _, rates in results for date in rates.keys()))[
            :days
        ]

        for date in dates:
            daily_rates = {date: {}}
            for currency, rates in results:
                if date in rates:
                    daily_rates[date][currency] = rates[date]
            combined_results.append(daily_rates)
        return combined_results


async def main():
    exchange_rate_service = ExchangeRateService()
    last_10_days_rates = await exchange_rate_service.get_rates_for_last_days(10)

    print(json.dumps(last_10_days_rates, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
