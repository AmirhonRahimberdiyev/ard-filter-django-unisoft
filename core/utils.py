def clean_phone(raw):
    digits = ''.join(c for c in raw if c.isdigit())
    if len(digits) < 9:
        return ""
    return f"+998 {digits[0:2]} {digits[2:5]} {digits[5:7]} {digits[7:]}"

def clean_card(raw):
    digits = ''.join(c for c in raw if c.isdigit())
    if len(digits) != 16:
        return ""
    return " ".join([digits[i:i+4] for i in range(0, 16, 4)])