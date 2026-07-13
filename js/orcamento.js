/*
 * Envio do formulário de pedido de orçamento para a API.
 *
 * Faz:
 *   - recolhe os 17 campos (incluindo os checkboxes)
 *   - envia por POST em JSON para a API
 *   - mostra mensagem de sucesso/erro por baixo do botão
 *   - aplica um COOLDOWN (o botão fica bloqueado uns segundos após cada envio),
 *     para um script não conseguir enviar centenas de formulários seguidos.
 */

// ---------------------------------------------------------------------------
// CONFIGURAÇÃO
// ---------------------------------------------------------------------------
// Em local usa a API a correr no teu PC; online usa a do Render.
// >>> Depois de fazeres deploy no Render, substitui o URL abaixo. <<<
const API_URL =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://localhost:5000/api/orcamento"
    : "https://carreira-e-silva.onrender.com/api/orcamento";

const COOLDOWN_SEGUNDOS = 30;

// Mensagens em PT/EN — escolhidas pelo idioma da página (<html lang="...">).
const LANG = (document.documentElement.lang || "pt").toLowerCase().startsWith("en") ? "en" : "pt";
const MSG = {
  pt: {
    enviando: "A enviar pedido...",
    sucesso: "Pedido enviado com sucesso!",
    falha: "Não foi possível enviar. Tente novamente.",
    ligacao: "Erro de ligação ao servidor. Tente novamente dentro de momentos.",
    aguarde: (s) => `Aguarde ${s}s...`,
  },
  en: {
    enviando: "Sending request...",
    sucesso: "Request sent successfully!",
    falha: "Could not send. Please try again.",
    ligacao: "Server connection error. Please try again shortly.",
    aguarde: (s) => `Please wait ${s}s...`,
  },
}[LANG];

// ---------------------------------------------------------------------------
let emCooldown = false;

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".form-grid");
  if (!form) return;

  const botao = form.querySelector('button[type="submit"]');
  const textoBotao = botao ? botao.textContent : "Enviar";

  // Cria uma linha de estado por baixo do botão.
  const status = document.createElement("p");
  status.className = "form-status";
  status.style.marginTop = "12px";
  status.style.fontWeight = "600";
  form.appendChild(status);

  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();

    if (emCooldown) return;

    // Valida os campos obrigatórios usando o próprio HTML (required, type=email...).
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    const dados = recolherDados(form);

    botao.disabled = true;
    status.style.color = "inherit";
    status.textContent = MSG.enviando;

    try {
      const resposta = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dados),
      });

      const json = await resposta.json().catch(() => ({}));

      if (resposta.ok) {
        status.style.color = "#1a7f37";
        status.textContent = "✅ " + (LANG === "en" ? MSG.sucesso : (json.mensagem || MSG.sucesso));
        form.reset();
        iniciarCooldown(botao, textoBotao);
      } else {
        status.style.color = "#c0392b";
        status.textContent = "⚠️ " + (json.error || MSG.falha);
        botao.disabled = false;
      }
    } catch (erro) {
      status.style.color = "#c0392b";
      status.textContent = "⚠️ " + MSG.ligacao;
      botao.disabled = false;
    }
  });
});

// Recolhe todos os campos do formulário num objeto pronto a enviar.
function recolherDados(form) {
  const valor = (id) => {
    const el = form.querySelector("#" + id);
    return el ? el.value.trim() : "";
  };
  const marcados = (name) =>
    Array.from(form.querySelectorAll(`input[name="${name}"]:checked`)).map((c) => c.value);

  return {
    nome: valor("nome"),
    email: valor("email"),
    telefone: valor("telefone"),
    codigo_postal: valor("codigo-postal"),
    tipo: valor("tipo"),
    origem: valor("origem"),
    destino: valor("destino"),
    andar_origem: valor("andar-origem"),
    andar_destino: valor("andar-destino"),
    elevador_origem: valor("elevador-origem"),
    elevador_destino: valor("elevador-destino"),
    itens: valor("itens"),
    especial: marcados("especial"),
    servico: marcados("servico"),
    data: valor("data"),
    flexibilidade: valor("flexibilidade"),
    observacoes: valor("observacoes"),
  };
}

// Bloqueia o botão durante COOLDOWN_SEGUNDOS, com contagem decrescente.
function iniciarCooldown(botao, textoOriginal) {
  emCooldown = true;
  let restante = COOLDOWN_SEGUNDOS;
  botao.disabled = true;
  botao.textContent = MSG.aguarde(restante);

  const cronometro = setInterval(() => {
    restante--;
    if (restante <= 0) {
      clearInterval(cronometro);
      emCooldown = false;
      botao.disabled = false;
      botao.textContent = textoOriginal;
    } else {
      botao.textContent = MSG.aguarde(restante);
    }
  }, 1000);
}
