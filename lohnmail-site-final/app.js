const menuButton = document.querySelector('.menu-button');
const navigation = document.querySelector('.main-navigation');

menuButton?.addEventListener('click', () => {
  const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
  menuButton.setAttribute('aria-expanded', String(!isOpen));
  menuButton.setAttribute('aria-label', isOpen ? 'Navigation öffnen' : 'Navigation schließen');
  navigation.classList.toggle('is-open', !isOpen);
  document.body.classList.toggle('menu-open', !isOpen);
});

navigation?.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    menuButton?.setAttribute('aria-expanded', 'false');
    menuButton?.setAttribute('aria-label', 'Navigation öffnen');
    navigation.classList.remove('is-open');
    document.body.classList.remove('menu-open');
  });
});

const benefitCarousel = document.querySelector('[data-benefit-carousel]');
const benefitSlides = Array.from(document.querySelectorAll('.benefit-slide'));
const benefitTabs = Array.from(document.querySelectorAll('.carousel-tab'));
const benefitCounter = document.querySelector('[data-carousel-count]');
const benefitPrevious = document.querySelector('[data-carousel-prev]');
const benefitNext = document.querySelector('[data-carousel-next]');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let activeBenefitIndex = 0;
let benefitTimer;

const showBenefit = (index, restart = true) => {
  if (!benefitSlides.length) return;
  activeBenefitIndex = (index + benefitSlides.length) % benefitSlides.length;

  benefitSlides.forEach((slide, slideIndex) => {
    const isActive = slideIndex === activeBenefitIndex;
    slide.classList.toggle('is-active', isActive);
    slide.setAttribute('aria-hidden', String(!isActive));
  });

  benefitTabs.forEach((tab, tabIndex) => {
    const isActive = tabIndex === activeBenefitIndex;
    tab.classList.toggle('is-active', isActive);
    tab.setAttribute('aria-selected', String(isActive));
  });

  if (benefitCounter) {
    benefitCounter.textContent = `${String(activeBenefitIndex + 1).padStart(2, '0')} / ${String(benefitSlides.length).padStart(2, '0')}`;
  }

  if (restart) startBenefitRotation();
};

const stopBenefitRotation = () => {
  window.clearInterval(benefitTimer);
};

function startBenefitRotation() {
  stopBenefitRotation();
  if (reduceMotion.matches || document.hidden || benefitSlides.length < 2) return;
  benefitTimer = window.setInterval(() => showBenefit(activeBenefitIndex + 1, false), 6500);
}

benefitTabs.forEach((tab) => {
  tab.addEventListener('click', () => showBenefit(Number(tab.dataset.benefitIndex)));
});

benefitPrevious?.addEventListener('click', () => showBenefit(activeBenefitIndex - 1));
benefitNext?.addEventListener('click', () => showBenefit(activeBenefitIndex + 1));

benefitCarousel?.addEventListener('mouseenter', stopBenefitRotation);
benefitCarousel?.addEventListener('mouseleave', startBenefitRotation);
benefitCarousel?.addEventListener('focusin', stopBenefitRotation);
benefitCarousel?.addEventListener('focusout', () => {
  window.setTimeout(() => {
    if (!benefitCarousel.contains(document.activeElement)) startBenefitRotation();
  }, 0);
});

document.addEventListener('visibilitychange', () => {
  if (document.hidden) stopBenefitRotation();
  else startBenefitRotation();
});

reduceMotion.addEventListener?.('change', startBenefitRotation);
startBenefitRotation();

const showcaseImage = document.querySelector('#showcase-image');
const showcaseSource = document.querySelector('#showcase-source');
const showcaseTitle = document.querySelector('#showcase-caption-title');
const showcaseCopy = document.querySelector('#showcase-caption-copy');
const showcaseTabs = document.querySelectorAll('.showcase-tab');

showcaseTabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    if (tab.classList.contains('is-active')) return;

    showcaseTabs.forEach((item) => {
      const active = item === tab;
      item.classList.toggle('is-active', active);
      item.setAttribute('aria-selected', String(active));
    });

    showcaseImage.classList.add('is-changing');
    window.setTimeout(() => {
      showcaseImage.src = tab.dataset.image;
      showcaseSource.srcset = tab.dataset.imageMobile;
      showcaseImage.alt = tab.dataset.alt;
      showcaseTitle.textContent = tab.dataset.title;
      showcaseCopy.textContent = tab.dataset.copy;
      showcaseImage.classList.remove('is-changing');
    }, 120);
  });
});

const contactForm = document.querySelector('#contact-form');
const formNote = document.querySelector('#form-note');
const downloadDialog = document.querySelector('#download-dialog');
const downloadDialogClose = downloadDialog?.querySelector('.dialog-close');

const openDownloadDialog = () => {
  if (!downloadDialog) return;
  if (typeof downloadDialog.showModal === 'function') {
    downloadDialog.showModal();
  } else {
    downloadDialog.setAttribute('open', '');
  }
};

downloadDialogClose?.addEventListener('click', () => downloadDialog.close());

downloadDialog?.addEventListener('click', (event) => {
  if (event.target === downloadDialog) downloadDialog.close();
});

contactForm?.addEventListener('submit', (event) => {
  event.preventDefault();
  const data = new FormData(contactForm);
  const subject = `LohnMail Testzugang – ${data.get('company')}`;
  const body = [
    `Firmenname: ${data.get('company')}`,
    `Ansprechpartner: ${data.get('name')}`,
    `E-Mail: ${data.get('email')}`,
    `Anzahl Mitarbeitende: ${data.get('employees')}`,
    '',
    'Nachricht:',
    data.get('message') || 'Keine zusätzliche Nachricht.'
  ].join('\n');

  const mailto = `mailto:support@lohn-mail.de?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  openDownloadDialog();
  if (formNote) formNote.textContent = 'Die Anfrage wurde für support@lohn-mail.de vorbereitet. Wählen Sie anschließend Ihre Version.';
  window.setTimeout(() => {
    window.location.href = mailto;
  }, 120);
});

document.querySelector('#current-year').textContent = new Date().getFullYear();
