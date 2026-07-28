# LohnMail — Landing Page

Одностраничный сайт для LohnMail на **Next.js 15 (App Router) + TypeScript**, без внешних UI-библиотек (чистый CSS с дизайн-токенами из брендбука).

## Локальный запуск

```bash
npm install
npm run dev
```

Сайт откроется на http://localhost:3000

## Деплой на Vercel

Вариант 1 — через GitHub:
1. Залей проект в репозиторий GitHub.
2. На https://vercel.com → **Add New Project** → выбери репозиторий.
3. Vercel сам определит Next.js — жми **Deploy**, ничего настраивать не нужно.

Вариант 2 — через CLI:
```bash
npm i -g vercel
vercel
```

## Контактная форма

Форма отправляет POST на `/api/contact` (`app/api/contact/route.ts`) и доставляет
заявку через серверный SMTP с помощью Nodemailer. Для Google используются
`smtp.gmail.com`, порт `587` и STARTTLS.

Добавь в `.env.local` для локальной разработки и в Vercel Environment Variables:

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your-google-account@gmail.com
SMTP_PASS=your-16-character-app-password
SMTP_FROM=your-google-account@gmail.com
CONTACT_TO=support@lohn-mail.de
```

`SMTP_USER` и `SMTP_PASS` обязательны. Остальные значения имеют указанные выше
значения по умолчанию. Для Google-аккаунта должна быть включена двухэтапная
аутентификация, а в `SMTP_PASS` указывается отдельный 16-значный App Password.
Обычный пароль Google-аккаунта использовать нельзя.

## Структура

```
app/
  layout.tsx        — шрифты (Inter + Archivo), SEO-метаданные
  globals.css       — дизайн-токены и все стили
  page.tsx          — все 14 секций лендинга
  api/contact/route.ts — endpoint формы
components/
  Header.tsx        — шапка с мобильным меню
  AppMockup.tsx     — мокап desktop-приложения в hero
  ContactForm.tsx   — форма «Testzugang anfragen»
  icons.tsx         — inline SVG-иконки
```

## Дизайн-токены

Все цвета из ТЗ заданы в `:root` в `globals.css`:
`--brand: #008A5B`, `--text: #0F172A`, `--text-secondary: #64748B`,
`--bg: #F6F8FA`, `--card: #FFFFFF`, `--border: #E2E8F0` и т.д.
Поменять брендовый цвет можно в одном месте.
