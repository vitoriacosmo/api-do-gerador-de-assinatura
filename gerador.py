import requests
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageEnhance
import io, os
from tkinter import Tk, filedialog

API_KEY = os.getenv("REMBG_API_KEY")
url = "https://api.rembg.com/rmbg"
headers = {"x-api-key": API_KEY}

# constantes
LARGURA_FINAL = 480
ALTURA_FINAL = 120
MARGEM_HORIZONTAL = 40
MARGEM_SUPERIOR = 10
MARGEM_INFERIOR = 5
DPI_QUALIDADE = (300, 300)  
BLUR_MEDIO = 0.35 

def processar_imagem_api(caminho_imagem):
    # remove o fundo da imagem usando a API rembg
    try:
        with open(caminho_imagem, "rb") as input_file:
            print("Removendo fundo da assinatura (aguarde)...")
            response = requests.post(url, headers=headers, files={"image": input_file})
            
            if response.status_code != 200:
                print(f"Erro na remoção: {response.status_code} {response.text}")
                return None
            
            return response.content
    except Exception as e:
        print(f"Erro ao processar imagem: {e}")
        return None

def melhorar_assinatura(imagem_data):
    # melhora a qualidade e aplica efeitos na assinatura
    try:
        # abre imagem retornada
        output_image = Image.open(io.BytesIO(imagem_data)).convert("RGBA")
        
        # aumenta contraste 
        enhancer = ImageEnhance.Contrast(output_image)
        output_image = enhancer.enhance(2.0)  
        
        # nitidez reduzida
        output_image = output_image.filter(ImageFilter.EDGE_ENHANCE)
        
        # limpa pixels fracos e aplica preto puro
        r, g, b, a = output_image.split()
        a = a.point(lambda i: 0 if i < 25 else 255)
        preto = Image.new("RGBA", output_image.size, (0, 0, 0, 255))
        output_image = Image.composite(preto, Image.new("RGBA", output_image.size, (0,0,0,0)), a)
        
        # corrige corte com margem
        bbox = output_image.getbbox()
        if bbox:
            margem = 10
            bbox_expandido = (
                max(0, bbox[0] - margem),
                max(0, bbox[1] - margem),
                min(output_image.width, bbox[2] + margem),
                min(output_image.height, bbox[3] + margem)
            )
            output_image = output_image.crop(bbox_expandido)
        
        return output_image
    except Exception as e:
        print(f"Erro ao melhorar assinatura: {e}")
        return None

def redimensionar_assinatura(imagem, max_largura=280, max_altura=50):
    # redimensiona mantendo proporção e qualidade
    largura_img, altura_img = imagem.size
    proporcao = min(max_largura / largura_img, max_altura / altura_img)
    nova_largura = int(largura_img * proporcao)
    nova_altura = int(altura_img * proporcao)
    
    # BICUBIC melhor para assinaturas
    imagem_redim = imagem.resize((nova_largura, nova_altura), Image.BICUBIC)
    
    return imagem_redim

def aplicar_blur_final(imagem):
    # aplica blur moderado para aparência natural e suave
    imagem = imagem.filter(ImageFilter.GaussianBlur(BLUR_MEDIO))
    
    # suaviza ainda mais as bordas
    # imagem = imagem.filter(ImageFilter.SMOOTH_MORE)
    
    # ajustes finais mais sutis para manter suavidade
    enhancer_contraste = ImageEnhance.Contrast(imagem)
    imagem = enhancer_contraste.enhance(1.00)  
    
    enhancer_brilho = ImageEnhance.Brightness(imagem)
    imagem = enhancer_brilho.enhance(0.92)  
    
    return imagem

def criar_assinatura_completa(imagem_assinatura, nome, crm, frase_extra=""):
    """Cria a imagem final com assinatura e texto"""
    # carrega fonte
    try:
        font = ImageFont.truetype("arialbd.ttf", 11)
    except:
        font = ImageFont.load_default()
    
    # prepara texto
    texto = f"{nome}\nCRM: {crm}"
    if frase_extra:
        texto += f"\n{frase_extra}"
    
    # calcula dimensões do texto
    temp_img = Image.new("RGBA", (1,1))
    draw_temp = ImageDraw.Draw(temp_img)
    bbox_texto = draw_temp.multiline_textbbox((0,0), texto, font=font, spacing=1)
    altura_texto = bbox_texto[3] - bbox_texto[1]
    largura_texto = bbox_texto[2] - bbox_texto[0]
    
    # redimensiona assinatura
    espaco_texto = altura_texto + MARGEM_INFERIOR
    max_largura_assinatura = min(280, LARGURA_FINAL - MARGEM_HORIZONTAL)
    max_altura_assinatura = min(50, ALTURA_FINAL - MARGEM_SUPERIOR - espaco_texto - MARGEM_INFERIOR)
    
    imagem_assinatura = redimensionar_assinatura(imagem_assinatura, max_largura_assinatura, max_altura_assinatura)
    
    # aplica blur após redimensionamento
    imagem_assinatura = aplicar_blur_final(imagem_assinatura)
    
    # cria imagem final com fundo branco
    imagem_final = Image.new("RGBA", (LARGURA_FINAL, ALTURA_FINAL), "white")
    draw = ImageDraw.Draw(imagem_final)
    
    # centraliza verticalmente
    nova_largura, nova_altura = imagem_assinatura.size
    altura_conteudo = nova_altura + MARGEM_INFERIOR + altura_texto
    y_inicio_assinatura = (ALTURA_FINAL - altura_conteudo) // 2
    x_inicio_assinatura = (LARGURA_FINAL - nova_largura) // 2
    
    # cola assinatura
    imagem_final.paste(imagem_assinatura, (x_inicio_assinatura, y_inicio_assinatura), imagem_assinatura)
    
    # adiciona texto centralizado
    x_texto = (LARGURA_FINAL - largura_texto) // 2
    y_texto = y_inicio_assinatura + nova_altura + MARGEM_INFERIOR
    draw.multiline_text((x_texto, y_texto), texto, fill=(0,0,0), font=font, align="center", spacing=1)
    
    return imagem_final

def main():
    # função principal
    while True:
        nome = input("Digite o nome do médico com Dr./Dra.: ")
        crm = input("Digite o CRM com estado: ")
        
        add_frase = input("Adicionar frase adicional? (S/N): ").strip().lower()
        frase_extra = ""
        if add_frase == "s":
            frase_extra = input("Digite a frase que deseja adicionar: ")
        
        # seleciona imagem
        Tk().withdraw()
        img = filedialog.askopenfilename(title="Selecione a imagem da assinatura: ")
        if not img:
            print("Nenhuma imagem selecionada.")
            break
        
        # processa imagem na API
        imagem_data = processar_imagem_api(img)
        if not imagem_data:
            continue
        
        # melhora a assinatura
        assinatura_melhorada = melhorar_assinatura(imagem_data)
        if not assinatura_melhorada:
            continue
        
        # cria imagem final
        imagem_final = criar_assinatura_completa(assinatura_melhorada, nome, crm, frase_extra)
        
        # salva com boa qualidade e mostra
        arquivo_final = f"Assinatura - {nome}.png"
        imagem_final.save(arquivo_final, "PNG", optimize=True, dpi=DPI_QUALIDADE)
        imagem_final.show()

if __name__ == "__main__":
    main()