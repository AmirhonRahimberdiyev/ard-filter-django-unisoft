from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent

data = {
    'card_number': [
        '8600 4835 2559 2899',
        '8600855254356990',
        '8600327218840361',
        '8600 3901 0981 2774',
        '8600 0871 2045 1520',
        '8600910092834567',
        '8600 1234 5678 9012',
        '8600 7843 9910 1122'
    ],
    'expire': [
        '2025-07',
        '03.2026',
        '2026-08',
        '04/25',
        '11.2026',
        '07/26',
        '12/24',
        '06.2024'
    ],
    'phone': [
        '973-03-03',
        '',
        '99 973 03 03',
        '',
        '973-03-03',
        '',
        '99 973 03 03',
        ''
    ],
    'status': [
        'expired',
        'active',
        'active',
        'active',
        'expired',
        'expired',
        'inactive',
        'inactive'
    ],
    'balance': [
        '200.00',
        '842,714,800.00',
        '22,300.00',
        '8,911,200.00',
        '400.00',
        '684,214,300.00',
        '5,000.00',
        '0.00'
    ]
}

df = pd.DataFrame(data)
out = ROOT / 'sample_cards.xlsx'
df.to_excel(out, index=False)
print(f'Created {out}')