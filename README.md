# Saber Legacy — Dashboard de pauta

Plataforma de análisis y acción de la cuenta Meta Ads de Saber Legacy, por Al Chile Media.

**Corte de datos actual: 23 de agosto de 2026.**

## Páginas

- [**Analíticas Cliente**](https://margotduek.github.io/ACM-Saber-Dashboard/) — vista limpia para Juan (ventas, ROAS, top productos, evolución)
- [**Analíticas Internas**](https://margotduek.github.io/ACM-Saber-Dashboard/internas.html) — dashboard operativo con filtros por período + YoY + ad-level
- [**Recomendaciones**](https://margotduek.github.io/ACM-Saber-Dashboard/recomendaciones.html) — checklist accionable (las marcas se guardan en tu navegador)
- [**Explicaciones**](https://margotduek.github.io/ACM-Saber-Dashboard/explicaciones.html) — guía de qué está pasando y cómo leer las métricas

## 📊 [Datos en markdown](data/) — para copiar y pegar

Tablas listas para Notion / Excel / Google Sheets. **⭐ [Todos los datos en uno](data/00-todo-junto.md)** es el más fácil.

## Regenerar

```bash
python3 fetch_data.py         # jala Meta Ads + Shopify a data.json
python3 build_report_data.py  # regenera data/*.md (incluye 00-todo-junto.md)
```

Requiere un `.env` (no está en el repo) con `ACCESS_TOKEN`, `AD_ACCOUNT_ID`, `SHOPIFY_STORE`, `SHOPIFY_TOKEN`.

Las cuatro páginas HTML se generan aparte, con el builder que vive en la carpeta de trabajo local
(`Cuentas/saber legacy/scripts/build_all.py`). Lee sus rutas de variables de entorno:

```bash
SABER_DATA=/ruta/a/los/json SABER_OUT=/ruta/al/repo SABER_END=2026-08-23 python3 build_all.py
```

### Qué se regenera solo vs qué sigue siendo manual

| Archivo | ¿Automático? |
|---|---|
| `00-todo-junto.md` | ✅ sí — concatena 01–09 en un solo documento |
| `01-meta-mensual.md` | ✅ sí — gasto/clics/CPC/frecuencia por mes |
| `02-meta-campañas.md` | ✅ sí — mismo alcance, por campaña |
| `03-meta-fechas-clave.md` | ✅ sí — usa el calendario fijo `KEY_DATES` en `build_report_data.py`; agrega fechas nuevas ahí |
| `05-shopify-productos.md` | ✅ sí — top productos por revenue |
| `06-shopify-geo.md` | ✅ sí — distribución por estado |
| `07-shopify-promos.md` | ✅ sí — códigos de descuento (se derivan de las órdenes, no de `price_rules`) |
| `08-shopify-clientes.md` | ✅ sí — LTV desde el objeto customer de Shopify (cubre el histórico completo, ver nota abajo) |
| `04-shopify-atribucion.md` | ❌ manual — requiere pedidos de Shopify de +60 días (ver nota) |
| `09-presupuesto.md` | ❌ manual a propósito — es una propuesta forward-looking, no un dato histórico |

## ⚠️ Estado real de los datos (actualizado 2026-08-24)

### Corrección a los hallazgos de julio

El README anterior afirmaba dos cosas que, al revisar la API con el histórico completo, **resultaron incorrectas**:

1. ~~"El pixel de Meta no tiene ningún evento `purchase` configurado — 0 conversiones en 3 años."~~
   **Falso.** Hay eventos `purchase` continuos desde agosto 2024: **689 compras lifetime** por $3,367,119 MXN
   atribuidos. El pixel funciona.
2. ~~"Meta infla los números x3 — dice 10 ventas cuando Shopify tiene 3."~~
   **Falso.** Las variantes del evento (`purchase`, `omni_purchase`, `web_in_store_purchase`,
   `onsite_web_purchase`…) reportan todas el **mismo** número (689 / 699 / 689), no se suman entre sí.
   Meta no duplica.

Hoy ocurre lo contrario: **Meta atribuye menos que Shopify** (julio: 8 vs 10; agosto: 5 vs 8), que es el
comportamiento esperado — Shopify cuenta también las ventas orgánicas que ninguna campaña reclama.

### Limitaciones vigentes

- **Shopify solo devuelve ~60 días de pedidos.** El token (`shpca_...`) no tiene el scope `read_all_orders`
  (requiere aprobación de Shopify). Por eso `04-shopify-atribucion.md` no se puede regenerar. Los clientes sí
  llegan completos porque Shopify guarda `total_spent`/`orders_count` agregados en el objeto customer.
- **`price_rules.json` devuelve 403** con el token actual. No afecta a `07-shopify-promos.md`, que deriva los
  códigos de las órdenes.
- `AD_ACCOUNT_ID` puede ir con o sin el prefijo `act_`; `fetch_data.py` lo normaliza.

---

Generado con Meta Marketing API (v23.0) + Shopify Admin API (2024-10).
