# Static reference data

## `fmv_31jan2018.json`

Fair market values on 31 January 2018, used for the Section 112A cost step-up
on listed equity acquired before 1 February 2018.

Not committed with values, because a wrong FMV puts a wrong figure on a tax
filing. Populate it from the authoritative source before enabling
grandfathering for users:

1. Download the NSE bhavcopy for **31 January 2018** (or the BSE equivalent for
   BSE-listed scrips) from the exchange's historical data archive.
2. For each symbol take the **highest quoted price** on that date. For a scrip
   not traded on 31 Jan 2018, use the highest price on the last preceding day
   it did trade.
3. Write the file as a flat object keyed on the bare symbol, no exchange
   suffix, with values as strings:

```json
{
  "RELIANCE": "961.85",
  "TCS": "3054.75"
}
```

Symbols absent from this file get no step-up, and every affected lot is
reported back to the user under `grandfathering.symbols_missing_fmv` so the
gap is visible rather than silent.
