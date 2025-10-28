import requests
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageEnhance
import io, os

API_KEY = os.getenv("REMBG_API_KEY")

def processar_assinatura(img_bytes):
    # remove fundo via API
    r = requests.post("https://api.rembg.com/rmbg", 
                     headers={"x-api-key": API_KEY}, 
                     files={"image": img_bytes})
    if r.status_code != 200:
        return None
    
    # abre e processa
    img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    
    # contraste e nitidez
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.filter(ImageFilter.EDGE_ENHANCE)
    
    # limpa fundo e aplica preto
    r, g, b, a = img.split()
    a = a.point(lambda i: 0 if i < 25 else 255)
    preto = Image.new("RGBA", img.size, (0, 0, 0, 255))
    img = Image.composite(preto, Image.new("RGBA", img.size, (0,0,0,0)), a)
    
    # recorta com margem
    bbox = img.getbbox()
    if bbox:
        img = img.crop((max(0, bbox[0]-10), max(0, bbox[1]-10),
                       min(img.width, bbox[2]+10), min(img.height, bbox[3]+10)))
    
    return img

def criar_imagem_final(img, nome, crm, frase=""):
    # fonte
    try:
        font = ImageFont.truetype("arialbd.ttf", 11)
    except:
        font = ImageFont.load_default()
    
    # texto
    texto = f"{nome}\nCRM: {crm}"
    if frase:
        texto += f"\n{frase}"
    
    # dimensões do texto
    draw_temp = ImageDraw.Draw(Image.new("RGBA", (1,1)))
    bbox_txt = draw_temp.multiline_textbbox((0,0), texto, font=font, spacing=1)
    h_txt = bbox_txt[3] - bbox_txt[1]
    w_txt = bbox_txt[2] - bbox_txt[0]
    
    # redimensiona assinatura
    max_w, max_h = 280, 50 - h_txt
    w, h = img.size
    escala = min(max_w/w, max_h/h)
    img = img.resize((int(w*escala), int(h*escala)), Image.BICUBIC)
    
    # blur e ajustes
    img = img.filter(ImageFilter.GaussianBlur(0.35))
    img = ImageEnhance.Brightness(img).enhance(0.92)
    
    # monta imagem final
    final = Image.new("RGBA", (480, 120), "white")
    draw = ImageDraw.Draw(final)
    
    # centraliza assinatura
    w_img, h_img = img.size
    x = (480 - w_img) // 2
    y = (120 - h_img - 5 - h_txt) // 2
    final.paste(img, (x, y), img)
    
    # adiciona texto
    draw.multiline_text(((480-w_txt)//2, y+h_img+5), texto, 
                       fill=(0,0,0), font=font, align="center", spacing=1)
    
    return final

# loop principal
while True:
    nome = input("Nome do médico com Dr./Dra.: ")
    crm = input("CRM com estado: ")
    frase = input("Frase adicional (Enter p/ pular): ").strip()
    
    img_path = input("Caminho ou URL da imagem: ").strip()
    if not img_path:
        break
    
    print("Processando...")
    
    # carrega imagem (local ou web)
    try:
        if img_path.startswith(('http://', 'https://')):
            img_bytes = requests.get(img_path).content
        else:
            with open(img_path, 'rb') as f:
                img_bytes = f.read()
    except Exception as e:
        print(f"Erro ao carregar imagem: {e}")
        continue
    
    img = processar_assinatura(img_bytes)
    if not img:
        print("Erro ao processar")
        continue
    
    final = criar_imagem_final(img, nome, crm, frase)
    arquivo = f"Assinatura - {nome}.png"
    final.save(arquivo, "PNG", optimize=True, dpi=(300,300))
    final.show()
    print(f"✓ Salvo: {arquivo}\n")