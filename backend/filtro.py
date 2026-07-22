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
    "merda", "caralho", "foda", "fode", "foder", "fodido", "fodida", "puta",
    "puto", "cabrao", "cabra", "corno", "otario", "paneleiro", "burro",
    "idiota", "estupido", "imbecil", "cona", "piroca", "broche", "badalhoco",
    "pariu", "fdp",
    # Inglês — palavrões e insultos
    "fuck", "fucks", "fucked", "fucking", "fuckin", "fucker", "fuckers",
    "motherfucker", "motherfucking", "shit", "shitty", "shithead", "bullshit",
    "bitch", "bitches", "asshole", "assholes", "arsehole", "ass", "arse",
    "dick", "dickhead", "prick", "cock", "cocksucker", "cunt", "twat",
    "pussy", "bastard", "whore", "slut", "wanker", "wank", "bollocks",
    "bugger", "douchebag", "dumbass", "jackass", "moron", "damn", "goddamn",
    # Inglês — insultos discriminatórios (bloqueio importante)
    "nigger", "nigga", "faggot", "retard", "retarded",
    # Termos típicos de spam
    "viagra", "cialis", "casino", "bitcoin", "crypto", "loan", "porn",
    "porno", "xxx", "gambling", "jackpot", "lottery", "pharmacy", "pills",
}

# Padrões de injeção de código / tentativas de ataque.
#
# NOTA: a proteção real contra SQL injection é o ORM (SQLAlchemy usa queries
# parametrizadas, por isso o texto nunca é executado como SQL). Estes padrões
# são apenas uma camada extra que rejeita tentativas óbvias logo à entrada.
# São propositadamente específicos para não bloquear mensagens legítimas.
PADROES_PERIGOSOS = [
    # XSS / injeção de HTML e scripts
    r"<\s*script",              # <script>
    r"javascript\s*:",          # javascript:
    r"on\w+\s*=",               # onerror=, onclick=, ...
    r"<\s*iframe",              # <iframe>
    # SQL injection — assinaturas claramente maliciosas
    r"\bunion\b\s+(all\s+)?\bselect\b",              # UNION SELECT / UNION ALL SELECT
    r"\bdrop\s+table\b",                             # DROP TABLE
    r"\binsert\s+into\b",                            # INSERT INTO
    r"\bdelete\s+from\b",                            # DELETE FROM
    r";\s*(drop|delete|update|insert|alter|truncate)\b",  # ; DROP ...  (encadear comandos)
    r"\binformation_schema\b",                       # ler a estrutura da BD
    r"\bxp_cmdshell\b",                              # executar comandos (SQL Server)
    r"\b(sleep|pg_sleep|benchmark)\s*\(",            # ataques baseados em tempo
    r"\binto\s+(out|dump)file\b",                    # exportar ficheiros
    r"('|\")\s*or\s+('|\")?\s*\d+\s*('|\")?\s*=\s*('|\")?\s*\d+",  # ' OR 1=1
]

# Limites anti-spam
MAX_LINKS = 3          # nº máximo de links permitidos numa mensagem
MAX_CARACTERES = 3000  # tamanho máximo por campo de texto

# Substituições "leet" comuns para disfarçar palavras (m3rda, c@ralho, $hit...).
LEET = {
    "0": "o", "1": "i", "3": "e", "4": "a",
    "5": "s", "7": "t", "@": "a", "$": "s",
}

# Separadores que as pessoas metem ENTRE letras para enganar o filtro
# (espaços, pontos, hífens, etc.). Não inclui letras nem dígitos — por isso
# o padrão nunca "salta" de uma palavra para a seguinte.
_SEP = r"[\s._\-*+~|/\\]*"


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar palavras de forma fiável."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


def _descodificar(texto: str) -> str:
    """Minúsculas, sem acentos e com o 'leet' desfeito (m3rda -> merda)."""
    texto = _normalizar(texto)
    return "".join(LEET.get(c, c) for c in texto)


def _padrao_palavra(palavra: str) -> "re.Pattern":
    """
    Constrói um padrão tolerante a disfarces para uma palavra bloqueada:
      - cada letra pode repetir-se           -> fuuuck
      - pode haver separadores entre letras  -> f.u.c.k  /  f u c k
      - tem de ser uma palavra isolada       -> NÃO apanha 'puta' dentro de 'computador'
    """
    nucleo = _SEP.join(re.escape(c) + "+" for c in palavra)
    return re.compile(r"(?<![a-z0-9])" + nucleo + r"(?![a-z0-9])")


# Pré-compila os padrões uma só vez (as palavras já estão normalizadas).
_PADROES_BLOQUEADAS = [_padrao_palavra(_descodificar(p)) for p in PALAVRAS_BLOQUEADAS]


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

        # 4) Palavrões / linguagem imprópria (resistente a disfarces:
        #    leet, letras repetidas e separadores entre letras)
        desofuscado = _descodificar(texto)
        for padrao in _PADROES_BLOQUEADAS:
            if padrao.search(desofuscado):
                return False, "A mensagem contém linguagem imprópria."

    return True, ""
