"""
Filtro de conteúdo das mensagens.

Faz três coisas:
  1. limpar_texto()   -> remove HTML/scripts (proteção contra XSS) antes de guardar.
  2. validar_conteudo() -> rejeita palavrões, spam (muitos links) e injeções.

O objetivo é impedir que alguém mal-intencionado escreva código malicioso,
insultos ou spam no formulário. As listas são simples de propósito para
poderes ajustá-las facilmente.
"""

import re
import unicodedata
from html import escape

# ---------------------------------------------------------------------------
# Lista de palavras bloqueadas (podes acrescentar/remover à vontade).
# Guardadas sem acentos e em minúsculas, porque a comparação é feita assim.
# ---------------------------------------------------------------------------
PALAVRAS_BLOQUEADAS = {
    # Português
    "merda", "caralho", "foda", "fode", "foder", "puta", "puto", "cabrao",
    "cabra", "corno", "otario", "paneleiro", "burro", "idiota", "estupido",
    "imbecil", "cona", "piroca", "broche", "badalhoco",
    # Inglês (spam/insultos comuns)
    "fuck", "shit", "bitch", "asshole", "dick", "cunt", "bastard",
    # Termos típicos de spam
    "viagra", "casino", "bitcoin", "crypto", "loan", "porn", "xxx",
}

# Padrões de injeção de código / tentativas de ataque.
PADROES_PERIGOSOS = [
    r"<\s*script",          # <script>
    r"javascript\s*:",      # javascript:
    r"on\w+\s*=",           # onerror=, onclick=, ...
    r"<\s*iframe",          # <iframe>
    r"(union\s+select|drop\s+table|insert\s+into|delete\s+from)",  # SQL injection
]

# Limites anti-spam
MAX_LINKS = 3          # nº máximo de links permitidos numa mensagem
MAX_CARACTERES = 3000  # tamanho máximo por campo de texto


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar palavras de forma fiável."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def limpar_texto(texto) -> str:
    """
    Prepara um texto para ser guardado com segurança:
      - remove etiquetas HTML (<b>, <script>, ...)
      - escapa caracteres perigosos (< > &)
    Assim, mesmo que a mensagem seja mostrada depois numa página, não corre código.
    """
    if texto is None:
        return ""
    texto = str(texto).strip()
    texto = re.sub(r"<[^>]*>", "", texto)  # remove qualquer tag HTML
    return escape(texto)                    # neutraliza < > & restantes


def validar_conteudo(*textos) -> tuple[bool, str]:
    """
    Analisa um ou mais textos. Devolve (ok, motivo).
      ok = True  -> conteúdo aceite
      ok = False -> motivo explica porque foi rejeitado
    """
    for texto in textos:
        if not texto:
            continue
        texto = str(texto)

        # 1) Tamanho
        if len(texto) > MAX_CARACTERES:
            return False, "A mensagem é demasiado longa."

        # 2) Injeção de código / ataques
        for padrao in PADROES_PERIGOSOS:
            if re.search(padrao, texto, re.IGNORECASE):
                return False, "A mensagem contém conteúdo não permitido."

        # 3) Spam: demasiados links
        links = re.findall(r"https?://|www\.", texto, re.IGNORECASE)
        if len(links) > MAX_LINKS:
            return False, "A mensagem parece spam (demasiados links)."

        # 4) Palavrões / linguagem imprópria
        normalizado = _normalizar(texto)
        palavras = re.findall(r"[a-z]+", normalizado)
        if PALAVRAS_BLOQUEADAS.intersection(palavras):
            return False, "A mensagem contém linguagem imprópria."

    return True, ""
