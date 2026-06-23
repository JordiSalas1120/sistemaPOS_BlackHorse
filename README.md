# 🐴 BlackHorse — Sistema POS · CMS · CRM

Sistema de gestión completo para tienda de artículos de cuero (talabartería), desarrollado para **Bolivia**. Incluye punto de venta (POS), gestión de inventario, CRM de clientes y motor de precios diferenciados retail/mayorista.

---

## ✨ Funcionalidades

| Módulo | Descripción |
|--------|-------------|
| **POS / Ventas** | Registro de ventas con búsqueda de productos, aplicación automática de descuentos, numeración `VTA-YYYY-NNNNN` y ticket TXT para impresora |
| **Productos** | Catálogo con SKU automático por categoría (`EQU-00001`), precios retail/mayorista, atributos dinámicos |
| **Inventario** | Control de stock en tiempo real, alertas de stock bajo, historial completo de movimientos |
| **Clientes** | Ficha con segmentación retail/mayorista, tags CRM, historial de compras |
| **Reglas de precio** | Descuentos por volumen, tipo de cliente o categoría — se aplica la regla de mayor prioridad |
| **Exportaciones** | Reportes Excel para productos, inventario y ventas; ticket TXT de 40 chars |
| **Auditoría** | Log automático de toda mutación con payload before/after |
| **Dashboard** | KPIs en tiempo real: ventas del día (Bs.), total ventas, clientes, alertas de stock |

---

## 🏗️ Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI 0.115 · Python 3.12 · Arquitectura hexagonal |
| Frontend | Next.js 14 · TypeScript · App Router · Tailwind CSS |
| Base de datos | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 async · Alembic |
| Exportación | pandas · openpyxl · tickets TXT |
| Estado frontend | Zustand · Zod · react-hook-form |
| Infraestructura | Docker Compose · nginx · pgAdmin 4 |

---

## 🚀 Instalación rápida

**Requisito único: Docker Desktop instalado.**

```bash
# 1. Clonar el repositorio
git clone https://github.com/JordiSalas1120/sistemaPOS_BlackHorse.git
cd sistemaPOS_BlackHorse

# 2. Configurar variables de entorno
cp .env.example .env

# 3. Construir y levantar todos los servicios
docker-compose up --build -d
```

En el primer arranque el sistema crea las tablas y siembra las categorías base automáticamente.

---

## 🌐 URLs del sistema

| Servicio | URL | Credenciales |
|----------|-----|-------------|
| **Aplicación** | http://localhost | — |
| **Swagger / API Docs** | http://localhost/docs | — |
| **ReDoc** | http://localhost/redoc | — |
| **pgAdmin** (BD visual) | http://localhost:5050 | `admin@admin.com` / `admin` |

> La contraseña de la base de datos en pgAdmin es `changeme` (configurable en `.env`)

---

## ⚙️ Variables de entorno

Copiar `.env.example` a `.env` y ajustar según el entorno:

```env
# Base de datos
POSTGRES_USER=talabarteria
POSTGRES_PASSWORD=changeme
POSTGRES_DB=talabarteria_db

# pgAdmin
PGADMIN_EMAIL=admin@admin.com
PGADMIN_PASSWORD=admin
```

---

## 🗂️ Estructura del proyecto

```
sistemaPOS_BlackHorse/
├── backend/                # FastAPI · arquitectura hexagonal
│   ├── src/
│   │   ├── domain/         # Entidades y servicios de negocio (sin dependencias externas)
│   │   ├── application/    # Casos de uso, puertos e interfaces
│   │   └── infrastructure/ # FastAPI, SQLAlchemy, adaptadores
│   ├── alembic/            # Migraciones de base de datos
│   └── tests/              # Tests unitarios de dominio
├── frontend/               # Next.js 14 · App Router
│   └── src/
│       ├── app/dashboard/  # Páginas: productos, clientes, inventario, ventas, precios
│       ├── components/     # Componentes reutilizables y formularios
│       ├── services/       # Clientes HTTP por módulo
│       └── types/          # Interfaces TypeScript
├── nginx/                  # Configuración del proxy reverso
├── pgadmin/                # Configuración pre-cargada de pgAdmin
├── docker-compose.yml      # Orquestación de los 5 servicios
└── .env.example            # Plantilla de configuración
```

---

## 📦 Servicios Docker

| Contenedor | Puerto | Descripción |
|------------|--------|-------------|
| `talabarteria_nginx` | 80 | Proxy reverso — punto de entrada único |
| `talabarteria_frontend` | 3000 | Next.js (producción standalone) |
| `talabarteria_backend` | 8000 | FastAPI con hot-reload |
| `talabarteria_db` | 5432 | PostgreSQL 16 |
| `talabarteria_pgadmin` | 5050 | pgAdmin 4 |

---

## 🧪 Ejecutar tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest --cov=src --cov-report=term-missing
```

Cobertura de tests unitarios en servicios de dominio:
- `test_pricing_service.py` — 11 casos (motor de precios)
- `test_inventory_service.py` — 10 casos (control de stock)
- `test_crm_tagging_service.py` — 8 casos (etiquetado automático)

---

## 📄 Licencia

Proyecto privado — BlackHorse Talabartería · Bolivia
