with open('D:/myts/ter-u24w.hex') as f:
    glyphs = {}
    for line in f:
        line = line.strip()
        if ':' in line:
            parts = line.split(':')
            cp = int(parts[0], 16)
            if cp < 128 or (0x0400 <= cp <= 0x04FF) or cp in [0x2122, 0x2026, 0x2014, 0x2013, 0x00AB, 0x00BB]:
                glyphs[cp] = parts[1]

print(f'Selected {len(glyphs)} glyphs for embedding')

with open('C:/Users/Biba/kindle-display-utils/font_data.go', 'w', encoding='utf-8') as out:
    out.write('package main\n\n')
    out.write('// Font24 maps Unicode rune to 48-byte bitmap (12x24 pixels, 2 bytes per row)\n')
    out.write('var Font24 = map[rune][48]byte{\n')
    for cp in sorted(glyphs.keys()):
        hex_str = glyphs[cp]
        byte_vals = [f'0x{hex_str[i:i+2]}' for i in range(0, len(hex_str), 2)]
        joined = ", ".join(byte_vals)
        out.write(f'\t0x{cp:04X}: {{{joined}}},\n')
    out.write('}\n')

print('Generated font_data.go successfully')
