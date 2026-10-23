# Importing market-price data

AgriConnect never scrapes websites and ships no API keys. Real data enters through a validated CSV import (or a provider class you add, see the end of this page).

## CSV format

UTF-8, comma separated, header row required. Column names are case-insensitive.

| Column | Required | Example | Rules |
|---|---|---|---|
| `state` | yes | `Bihar` | max 80 chars |
| `district` | yes | `Patna` | max 80 chars |
| `market` | yes | `Patna` | max 120 chars (the mandi / APMC name) |
| `commodity` | yes | `Wheat` | max 100 chars; becomes the crop name |
| `category` | no | `Cereals` | default `Uncategorised` |
| `unit` | no | `Rs/quintal` | default `Rs/quintal` |
| `arrival_date` | yes | `2026-10-16` | `YYYY-MM-DD` or `DD/MM/YYYY` |
| `min_price` | yes | `2300` | number > 0 and ≤ 1,000,000 |
| `max_price` | yes | `2500` | same |
| `modal_price` | yes | `2400` | same, and `min_price ≤ modal_price ≤ max_price` |
| `source` | no | `Agmarknet export 2026-10` | default `CSV import: <file name>` or `--source` |

Example:
```csv
state,district,market,commodity,category,unit,arrival_date,min_price,max_price,modal_price,source
Bihar,Patna,Patna,Wheat,Cereals,Rs/quintal,2026-10-16,2300,2500,2400,Agmarknet export
```

One row per crop, market and date. Crops and markets that don't exist yet are created automatically.

## Validate, then import

```bash
# 1. validate only (nothing is saved); lists each bad row with its line number
python database/import_prices.py path/to/prices.csv --dry-run

# 2. import (existing crop/market/date rows are skipped)
python database/import_prices.py path/to/prices.csv --source "Agmarknet export, Oct 2026"

# overwrite existing rows instead of skipping them
python database/import_prices.py path/to/prices.csv --on-duplicate update
```

Rejected rows are never written; the exit code is 1 if any row was rejected. The whole import runs in one transaction. Imported rows have `is_demo = false` and show an **Imported** badge in the UI. Use `--demo` only for synthetic or test files.

The same is available as a Flask command: `flask --app run.py import-prices path.csv --dry-run`.

## Getting genuine data

Good sources of Indian mandi prices are the Agmarknet portal and the "Current Daily Price of Various Commodities from Various Markets (Mandi)" datasets on data.gov.in (Open Government Data Platform India). Before using any dataset:

1. Read and follow its licence and terms of use (data.gov.in publishes under the Government Open Data License – India; attribution is required).
2. Download the export manually or through the official API with your own key.
3. Map its columns to the format above. Agmarknet/data.gov.in exports usually have `State, District, Market, Commodity, Variety, Grade, Arrival_Date, Min_x0020_Price, Max_x0020_Price, Modal_x0020_Price` — rename those to `state, district, market, commodity, arrival_date, min_price, max_price, modal_price`. If the same commodity appears with several varieties, either keep one variety or include it in the commodity name (e.g. `Onion (Red)`), otherwise you will get duplicate-date rows.

## Retrain on real data

```bash
python database/export_prices.py --out ml/data/real_prices.csv --only-imported
python ml/train.py --csv ml/data/real_prices.csv --data-kind real
```
Review the printed validation table: if the selected model does not beat the naive baseline on your data, the estimates are not adding value. Once a real model is active and the price history used is imported data, estimates are no longer labelled "Demo".

To remove the demo rows from the database once real data is loaded:
```sql
DELETE FROM market_prices WHERE is_demo = 1;
```
(Old predictions referencing demo crops/markets stay in history.)

## Adding a new data provider

Implement `PriceProvider` in `backend/app/services/providers.py`:

```python
class MyApiProvider(PriceProvider):
    name = "my-licensed-api"
    is_demo = False

    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch(self) -> pd.DataFrame:
        # call the API with self.api_key, map fields to STANDARD_COLUMNS, return a DataFrame
        ...
```

then call `import_prices(MyApiProvider(key))`. Validation, de-duplication and DB writes are shared with the CSV path, so every source meets the same rules. Read keys from environment variables, never hard-code them.
