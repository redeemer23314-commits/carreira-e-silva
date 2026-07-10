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
    : "https://SUBSTITUIR-pela-tua-api.onrender.com/api/orcamento";

const COOLDOWN_SEGUNDOS = 30;

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
    status.textContent = "A enviar pedido...";

    try {
      const resposta = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dados),
      });

      const json = await resposta.json().catch(() => ({}));

      if (resposta.ok) {
        status.style.color = "#1a7f37";
        status.textContent = "✅ " + (json.mensagem || "Pedido enviado com sucesso!");
        form.reset();
        iniciarCooldown(botao, textoBotao);
      } else {
        status.style.color = "#c0392b";
        status.textContent = "⚠️ " + (json.error || "Não foi possível enviar. Tente novamente.");
        botao.disabled = false;
      }
    } catch (erro) {
      status.style.color = "#c0392b";
      status.textContent = "⚠️ Erro de ligação ao servidor. Tente novamente dentro de momentos.";
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
  botao.textContent = `Aguarde ${restante}s...`;

  const cronometro = setInterval(() => {
    restante--;
    if (restante <= 0) {
      clearInterval(cronometro);
      emCooldown = false;
      botao.disabled = false;
      botao.textContent = textoOriginal;
    } else {
      botao.textContent = `Aguarde ${restante}s...`;
    }
  }, 1000);
}
