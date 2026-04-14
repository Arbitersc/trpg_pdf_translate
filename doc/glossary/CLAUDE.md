# Glossary Parquet Format Specification

## Overview
Glossary files are stored in Apache Parquet format with a simple two-column structure for managing translation mappings.

## Format Details

### File Extension
`.parquet`

### Encoding
UTF-8

### Compression
Default Parquet compression (typically Snappy)

### Schema

| Column Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `original` | string (unicode) | Source text or term | "aberration", "Achaekek" |
| `translation` | string (unicode) | Translated text | "异怪", "阿卡凯克" |

### Technical Specification
- **Format**: Apache Parquet
- **Library**: pyarrow (version 8.0.0)
- **Pandas Version**: 1.5.3
- **Column Types**: `pandas_type: unicode`, `numpy_type: object`

### Data Organization
- Each row represents a single glossary entry
- No duplicate entries for the same `original` value
- Sorted alphabetically by `original` column (recommended but not required)

### Example Usage (Python)

```python
import pandas as pd

# Reading glossary
glossary_df = pd.read_parquet('path/to/glossary.parquet')

# Creating new glossary
entries = {
    'original': ['term1', 'term2'],
    'translation': ['翻译1', '翻译2']
}
glossary_df = pd.DataFrame(entries)
glossary_df.to_parquet('output.parquet', index=False)
```

### Existing Glossary Files
- `default.parquet` - Default/cross-game term glossary
- `pf2_glossary.parquet` - Pathfinder 2nd Edition specific glossary
