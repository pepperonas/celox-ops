<p align="center">
  <img src="docs/screenshot.png" alt="celox ops" width="1024">
</p>

<h1 align="center">celox ops</h1>

<p align="center">
  Business management for freelancers & IT consultants — invoices, customers, contracts, AI usage tracking.<br>
  Gesch&auml;ftsverwaltung f&uuml;r Freelancer & IT-Berater — Rechnungen, Kunden, Vertr&auml;ge, KI-Nutzungstracking.
</p>

<p align="center">

[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![WeasyPrint](https://img.shields.io/badge/WeasyPrint-PDF-E44D26)](https://weasyprint.org/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4-FF6384?logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![JWT](https://img.shields.io/badge/JWT-Auth-000000?logo=jsonwebtokens&logoColor=white)](https://jwt.io/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)](https://www.sqlalchemy.org/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-6BA81E)](https://alembic.sqlalchemy.org/)
[![Nginx](https://img.shields.io/badge/Nginx-Reverse_Proxy-009639?logo=nginx&logoColor=white)](https://nginx.org/)
[![License](https://img.shields.io/badge/License-MIT-blue)](#license)
[![Platform](https://img.shields.io/badge/Platform-Linux-FCC624?logo=linux&logoColor=black)](https://www.linux.org/)
[![Zustand](https://img.shields.io/badge/Zustand-State-443E38)](https://zustand-demo.pmnd.rs/)
[![Axios](https://img.shields.io/badge/Axios-HTTP-5A29E4?logo=axios&logoColor=white)](https://axios-http.com/)

</p>

<p align="center">
  <a href="README_DE.md"><img src="https://img.shields.io/badge/%F0%9F%87%A9%F0%9F%87%AA_Deutsch-Dokumentation-black?style=for-the-badge" alt="Deutsch"></a>
  &nbsp;&nbsp;
  <a href="README_EN.md"><img src="https://img.shields.io/badge/%F0%9F%87%AC%F0%9F%87%A7_English-Documentation-black?style=for-the-badge" alt="English"></a>
</p>

---

## Quick Start

```bash
git clone https://github.com/pepperonas/celox-ops.git
cd OPS
cp .env.example .env    # configure passwords, JWT_SECRET, business details
docker compose up -d --build
# → http://localhost:8090
```

---

## Highlights

- **Customer, Order, Contract & Invoice Management** — full CRUD with status workflows
- **Professional PDF Invoices** — WeasyPrint + Jinja2, A4 layout with branding
- **AI Usage Dashboard** — Token Tracker integration with charts, KPIs, CSV/HTML export
- **Invoice Number Auto-Generation** — `CO-YYYY-NNNN` format, sequential per year
- **Kleinunternehmerregelung** — small business tax exemption support
- **GitHub-Inspired Dark Theme** — responsive React SPA with TailwindCSS
- **Docker Compose Deployment** — single command, production-ready
- **JWT Authentication** — secure single-user setup with bcrypt

---

## Better Together

Combines with [Claude Token Tracker](https://github.com/pepperonas/claude-token-tracker) for transparent AI usage reporting — active work time, code lines, cost per project, exportable reports, and invoice PDF attachments.

---

## Links

- **GitHub**: [github.com/pepperonas/celox-ops](https://github.com/pepperonas/celox-ops)
- **Token Tracker**: [github.com/pepperonas/claude-token-tracker](https://github.com/pepperonas/claude-token-tracker)
- **Author**: [Martin Pfeffer](https://celox.io)

## License

MIT

---

*Built by [Martin Pfeffer](https://celox.io)*
