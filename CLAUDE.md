# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Principles

- **Neat code**: Keep code clean, consistent, and readable at all times.
- **Component-based**: Break UI and logic into focused, reusable components. Prefer many small files over few large ones.
- **File length**: Keep files under 300 lines. If a file grows beyond this, extract components or helpers into separate files.
- **Documentation**: Add up to 2 lines of comments per function or logical section — enough to explain intent, not implementation details.
- **Update this file**: When making significant architectural changes, adding new routes/components, or changing conventions — update CLAUDE.md to reflect the new state.

## Commands

### Frontend (Client/)
```bash
npm run dev       # Start Vite dev server with HMR
npm run build     # Type-check + build production bundle (tsc -b && vite build)
npm run lint      # Run ESLint
npm run preview   # Preview production build
```

### Backend (Server/)
```bash
python app.py     # Start Flask API on 0.0.0.0:5000
```

### Database (Docker)
```bash
docker-compose up -d                                                                          # Start PostgreSQL container
docker-compose down                                                                           # Stop container
docker exec -i dietitian_db psql -U admin -d hospital_system < hospital_backup.sql           # Restore backup
docker exec -t dietitian_db pg_dump -U admin -d hospital_system > hospital_backup.sql        # Create backup
```

## Architecture

Three-tier system: React SPA → Flask REST API → PostgreSQL (with pgvector).

### Frontend (`Client/src/`)
- **TypeScript + Tailwind CSS + React Router v6**
- **App.tsx** is the root — defines all `<Route>` entries; `SideMenu` is rendered globally
- Pages live in `pages/`, reusable components in `components/` (sub-folders: `layout/`, `products/`, `settings/`, `meal/`, `login/`, `admin/`)
- Shared types live in `types.ts`; auth context in `context/AuthContext.tsx`
- API base URL set via `VITE_API_URL` env variable; called as `` `${import.meta.env.VITE_API_URL}/api/...` ``
- `utils/apiAuth.ts` (installed in `main.tsx`) wraps `window.fetch` to attach the stored JWT to every API request and send the user to `/login` on 401, so plain `fetch()` calls are authenticated

**Routes:**
| Path | Page |
|------|------|
| `/` | ProductsPage |
| `/settings` | ProductSettingsPage |
| `/settings/categories` | CategorySettingsPage |
| `/lineworker` | LineWorkerProductsPage |
| `/meals` | MealsCatalogPage |
| `/meals/create` | CreateMealPage |
| `/login` | LoginPage |

### Backend (`Server/`)
- **app.py** — Flask entry point; registers Blueprints and calls `init_security`
- **security.py** — Global `before_request` guard: every `/api/*` call needs a JWT except `/api/status` and `/api/auth/login`; writes to products/upload/categories/sensitivities/textures/diets need `admin` or `dietitian`; `/api/system/*` and `/api/run-migrations` are admin-only. CORS origins come from `ALLOWED_ORIGINS` (comma-separated; empty = any)
- `JWT_SECRET` is mandatory on Vercel (the server refuses to start without it)
- **models.py** — SQLAlchemy models: `FoodItem`, `Meal`, `Category`, `Texture`, `Sensitivity`, `Diet`
- **routes/** — One Blueprint module per resource: `products`, `meals`, `categories`, `sensitivities`, `textures`, `diets`, `system`
- **routes/variable_usage.py** — Shared usage counting + guarded deletion for the four "variable" tables (categories, sensitivities, textures, diets). See *Variable deletion* below.
- **scripts/** — Utility scripts: `seed.py` (seed data), `alter_db.py` (schema changes)
- Database migrations run via `GET /api/run-migrations`
- Images are stored in **Supabase** cloud storage; `image_url` in `FoodItem` points there
- `FoodItem` has `nutrition_vector` (6D) and `openai_embedding` (1536D pgvector columns) for AI/ML features

### Key API Endpoints
| Resource | Prefix |
|----------|--------|
| Products / images | `/api/products`, `/api/upload` |
| Meals | `/api/meals` |
| Categories | `/api/categories` |
| Sensitivities | `/api/sensitivities` |
| Textures | `/api/texture` |
| Diets | `/api/diets` |
| Export / Import | `/api/system/export`, `/api/system/import` |
| Health | `/api/status` |

Export (`/api/system/export`) produces a ZIP with CSV files and an `images/` folder; import reverses this.

### Variable deletion (categories / sensitivities / textures / diets)

Deleting a "variable" that products or meals still reference used to orphan data (a deleted sensitivity left its name as a dangling string on products, unreachable by any filter). All four resources now share one policy in `Server/routes/variable_usage.py`:

- `GET /api/<resource>/usage` → `{ id: { products, meals } }` for every row; the settings tables render this as a "בשימוש" column.
- `DELETE /api/<resource>/<id>` deletes **only** when nothing references the variable. Otherwise it returns **409** with `{ error, usage, message }`.
- **Deletion never modifies products or meals.** There is no cascade or detach path — no nulling `category_id`/`texture_id`, no stripping names from `contains`/`may_contain`, no deleting products. The user must clear the references themselves first.
- `FoodItem.properties` is deliberately *not* counted as sensitivity usage: it uses a separate vocabulary (`vegan`, `sugar_free`) that no UI populates from the sensitivities list.

Frontend: `Client/src/hooks/useVariableUsage.ts` drives the flow, `components/settings/DeleteVariableDialog.tsx` is the confirmation modal, `components/settings/UsageBadge.tsx` is the table cell. A missing usage entry means *unknown*, never "not in use".

### Data Notes
- `Meal` saves a JSON array of `product_ids` and a nutritional snapshot (totals) at creation time
- `FoodItem.contains` and `may_contain` are stored as JSONB arrays of sensitivity names
- `FoodItem.properties` is a freeform JSONB field