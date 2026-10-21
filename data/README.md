# Local Training Data

Place your training catalogue Excel file in this folder using the filename:

`training.xlsx`

Expected columns:
- `Series Name`
- `Stage`
- `Architecture`
- `Program Track`
- `Track`
- `Role`
- `Language`
- `Learning Plan Type`
- `ENABLEMENT_BUSINESS_ENTITY`
- `Description`
- `Series URL`

Excel files (`*.xlsx`) are excluded by the repository `.gitignore` and should remain local. Do not upload the actual training workbook to GitHub. The ingestion script will read it from `data/training.xlsx` when run locally.
