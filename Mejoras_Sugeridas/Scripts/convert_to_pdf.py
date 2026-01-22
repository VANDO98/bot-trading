import os
import re
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import grey, black, blue

def parse_markdown_to_pdf(input_file, output_file):
    doc = SimpleDocTemplate(output_file, pagesize=LETTER,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    Story = []
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    
    # Custom Styles
    title_style = styles["Title"]
    h1_style = styles["Heading1"]
    h2_style = styles["Heading2"]
    normal_style = styles["BodyText"]
    code_style = ParagraphStyle('Code', parent=styles['BodyText'], fontName='Courier', fontSize=9, backColor=grey, textColor=black)

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False
    code_buffer = []

    for line in lines:
        line = line.strip()
        
        # Code Blocks
        if line.startswith('```'):
            if in_code_block:
                # End block
                text = "<br/>".join(code_buffer)
                p = Paragraph(text, code_style)
                Story.append(p)
                Story.append(Spacer(1, 12))
                in_code_block = False
                code_buffer = []
            else:
                in_code_block = True
            continue
        
        if in_code_block:
            code_buffer.append(line)
            continue

        if not line:
            continue

        # Headers
        if line.startswith('# '):
            Story.append(Paragraph(line[2:], title_style))
            Story.append(Spacer(1, 12))
        elif line.startswith('## '):
            Story.append(Paragraph(line[3:], h1_style))
            Story.append(Spacer(1, 10))
        elif line.startswith('### '):
            Story.append(Paragraph(line[4:], h2_style))
            Story.append(Spacer(1, 10))
            
        # Lists
        elif line.startswith('* ') or line.startswith('- '):
            # Clean bold syntax **text** -> <b>text</b>
            clean_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line[2:])
            Story.append(Paragraph(f"• {clean_line}", normal_style))
            Story.append(Spacer(1, 6))
            
        # Normal Text
        else:
            # Bold syntax
            clean_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            Story.append(Paragraph(clean_line, normal_style))
            Story.append(Spacer(1, 8))

    doc.build(Story)
    print(f"✅ PDF Generado: {output_file}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Asumimos que el script corre desde root o similar, ajustamos rutas
    # El archivo origen esta en Mejoras_Sugeridas/Propuesta_Estrategias.md
    
    root_dir = os.getcwd() 
    if "Mejoras_Sugeridas" not in os.listdir(root_dir):
        # Si corremos desde Scripts/ puede fallar si no ajustamos
        pass

    input_path = "Mejoras_Sugeridas/Propuesta_Estrategias.md"
    output_path = "Mejoras_Sugeridas/Propuesta_Estrategias.pdf"
    
    if os.path.exists(input_path):
        parse_markdown_to_pdf(input_path, output_path)
    else:
        print(f"❌ No encuentro el archivo de entrada: {input_path}")
