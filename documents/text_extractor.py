import pdfplumber

def extract_text_from_txt(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()
    
def extract_text_from_pdf(file_path):
    
    text=[]

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text=page.extract_text()
            if page_text:
                text.append(page_text)

    return "\n".join(text)


def extract_text(file_path,file_type):
    if file_type == "txt":
        return extract_text_from_txt(file_path)
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    raise ValueError(f"Unsupported file type:{file_type}")