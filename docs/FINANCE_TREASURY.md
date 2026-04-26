# Treasury & Cash Management

This module provides **cash boxes** and **treasury transactions** with strong accounting guarantees:

- **No floating point mutations** (all amounts are `Decimal`)
- **Idempotent writes** (header: `X-Idempotency-Key`)
- **Server-side farm scope injection** (header: `X-Farm-ID`)
- **Immutable ledger posting** (treasury creates exactly two ledger lines)

## Data model

### CashBox (`core_cashbox`)

Represents a cash account for a farm:
- `farm` (FK)
- `name`
- `currency` (ISO code)
- `balance` (`Decimal`)

### TreasuryTransaction (`core_treasurytransaction`)

A movement in/out of a cash box:
- `farm` (FK)
- `cash_box` (FK)
- `transaction_type`: `DEPOSIT` or `WITHDRAWAL`
- `amount` (`Decimal`)
- `exchange_rate` (`Decimal`, optional)
- `reference` (optional)
- `note` (optional)
- `party_content_type` + `party_object_id` (optional)
- `idempotency_key` (unique, derived from the request header)

## API

All endpoints are under:
- `/api/v1/finance/`

### List cash boxes

`GET /finance/cash-boxes/`

### Create a treasury transaction

`POST /finance/treasury-transactions/`

Required headers:
- `Authorization: Bearer ...`
- `X-Farm-ID: <farm_id>`
- `X-Idempotency-Key: <client_uuid>`

Payload:
```json
{
  "cash_box": 1,
  "transaction_type": "DEPOSIT",
  "amount": "100.00",
  "exchange_rate": "1.0000",
  "reference": "RCPT-2026-0001",
  "note": "Cash received",
  "party_model": "customer",
  "party_id": "123"
}
```

Notes:
- `party_model`/`party_id` are convenience fields; the backend maps them to Django ContentTypes.
- The server sets `farm` and `idempotency_key` and ignores any `farm` in the payload.

## Accounting behaviour

On successful creation, the backend posts **two** ledger lines:
- Debit and Credit to the configured treasury ledger accounts.

The posting is implemented in:
- `backend/smart_agri/finance/signals.py`

Ledger idempotency keys are deterministic:
- `LEDGER-<tx_idempotency_key>-D`
- `LEDGER-<tx_idempotency_key>-C`

## Fiscal period safety

Treasury transactions are rejected if the relevant fiscal period is **CLOSED**.

## Security

PostgreSQL Row Level Security (RLS) policies enforce:
- users may only see data for farms they are members of

See migration:
- `backend/smart_agri/finance/migrations/0027_treasury_rls_and_immutability.py`
