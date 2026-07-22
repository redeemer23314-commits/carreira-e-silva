// Menu mobile (hamburger)
const navToggle = document.getElementById('navToggle');
const mainNav = document.getElementById('mainNav');

if (navToggle && mainNav) {
  navToggle.addEventListener('click', () => {
    const isOpen = mainNav.classList.toggle('is-open');
    navToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  });

  // Fecha o menu ao clicar num link (mobile)
  mainNav.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      mainNav.classList.remove('is-open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

// Ano atual no rodapé
const yearEl = document.getElementById('year');
if (yearEl) {
  yearEl.textContent = new Date().getFullYear();
}

// Mapa: so carrega o iframe da Google depois de o visitante consentir.
// O URL vem do data-map-embed e o titulo do data-map-title, para funcionar
// nas tres versoes de idioma sem duplicar codigo.
document.querySelectorAll('[data-map-embed]').forEach((caixa) => {
  const botao = caixa.querySelector('.map-embed__btn');
  if (!botao) return;

  botao.addEventListener('click', () => {
    const iframe = document.createElement('iframe');
    iframe.src = caixa.dataset.mapEmbed;
    iframe.title = caixa.dataset.mapTitle || 'Mapa';
    iframe.setAttribute('allowfullscreen', '');
    iframe.setAttribute('loading', 'lazy');
    iframe.setAttribute('referrerpolicy', 'no-referrer-when-downgrade');

    caixa.textContent = '';
    caixa.appendChild(iframe);
    caixa.classList.add('is-loaded');
  });
});
