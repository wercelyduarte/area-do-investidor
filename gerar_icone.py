# Gera icone.ico (grafico de barras subindo) - rode se quiser recriar/alterar o icone
from PIL import Image, ImageDraw

S = 1024  # desenha grande e reduz (suaviza as bordas)
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# fundo: quadrado arredondado azul-escuro
d.rounded_rectangle((32, 32, S - 32, S - 32), radius=220, fill=(44, 62, 80, 255))

# barras crescentes
VERDE = (24, 188, 156, 255)
for i, h in enumerate((260, 400, 560)):
    x = 220 + i * 210
    d.rounded_rectangle((x, 820 - h, x + 150, 820), radius=30, fill=VERDE)
# linha de base
d.rounded_rectangle((180, 840, 844, 880), radius=20, fill=(255, 255, 255, 255))

sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save("icone.ico", sizes=sizes)
print("ok")
