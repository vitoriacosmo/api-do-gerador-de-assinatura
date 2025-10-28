from flask import Flask, request, send_file, jsonify, render_template_string
from PIL import Image, ImageFilter, ImageDraw, ImageFont, ImageEnhance
import requests
import io, os

app = Flask(__name__)
API_KEY = os.getenv("REMBG_API_KEY")

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Gerador de Assinaturas</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }
        input, button { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }
        button { background: #007bff; color: white; border: none; cursor: pointer; font-size: 16px; }
        button:hover { background: #0056b3; }
        #resultado { margin-top: 20px; text-align: center; }
        img { max-width: 100%; border: 1px solid #ddd; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>📝 Gerador de Assinaturas Médicas</h1>
    <form id="form" enctype="multipart/form-data">
        <input type="text" name="nome" placeholder="Nome do médico (ex: Dr. João Silva)" required>
        <input type="text" name="crm" placeholder="CRM com estado (ex: CRM 12345-SP)" required>
        <input type="text" name="frase" placeholder="Frase adicional (opcional)">
        <input type="file" name="imagem" accept="image/*" required>
        <button type="submit">Gerar Assinatura</button>
    </form>
    <div id="resultado"></div>
    
    <script>
        document.getElementById('form').onsubmit = async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button');
            btn.textContent = 'Processando...';
            btn.disabled = true;
            
            const formData = new FormData(e.target);
            const res = await fetch('/gerar', { method: 'POST', body: formData });
            
            if (res.ok) {
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                document.getElementById('resultado').innerHTML = 
                    `<h3>✅ Assinatura gerada!</h3>
                     <img src="${url}">
                     <br><a href="${url}" download="assinatura.png">
                     <button type="button">Baixar Imagem</button></a>`;
            } else {
                document.getElementById('resultado').innerHTML = 
                    '<p style="color:red">❌ Erro ao processar imagem</p>';
            }
            
            btn.textContent = 'Gerar Assinatura';
            btn.disabled = false;
        };
    </script>
</body>
</html>
'''

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

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/gerar', methods=['POST'])
def gerar():
    try:
        nome = request.form['nome']
        crm = request.form['crm']
        frase = request.form.get('frase', '')
        img_file = request.files['imagem']
        
        # processa imagem
        img_bytes = img_file.read()
        img = processar_assinatura(img_bytes)
        if not img:
            return jsonify({'erro': 'Erro ao processar imagem'}), 500
        
        # cria assinatura final
        final = criar_imagem_final(img, nome, crm, frase)
        
        # retorna imagem
        buffer = io.BytesIO()
        final.save(buffer, 'PNG', optimize=True, dpi=(300,300))
        buffer.seek(0)
        
        return send_file(buffer, mimetype='image/png', 
                        as_attachment=True, 
                        download_name=f'Assinatura - {nome}.png')
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Servidor rodando em http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)