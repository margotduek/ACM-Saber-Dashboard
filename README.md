# Saber Legacy — Dashboard de pauta

Plataforma de análisis y acción de la cuenta Meta Ads de Saber Legacy, por Al Chile Media.

## Páginas

- [**Analíticas Cliente**](https://margotduek.github.io/ACM-Saber-Dashboard/) — vista limpia para Iván (ventas, ROAS, top productos, evolución)
- [**Analíticas Internas**](https://margotduek.github.io/ACM-Saber-Dashboard/internas.html) — dashboard operativo con filtros por período + YoY + ad-level
- [**Recomendaciones**](https://margotduek.github.io/ACM-Saber-Dashboard/recomendaciones.html) — checklist accionable (las marcas se guardan en tu navegador)

## 📊 [Datos en markdown](data/) — para copiar y pegar

Tablas listas para Notion / Excel / Google Sheets. **⭐ [Todos los datos en uno](data/00-todo-junto.md)** es el más fácil.

## Regenerar los datos

```bash
python3 fetch_data.py         # jala Meta Ads + Shopify a data.json
python3 build_report_data.py  # regenera las tablas de data/*.md desde data.json
```

Requiere un `.env` (no está en el repo) con `ACCESS_TOKEN`, `AD_ACCOUNT_ID`, `SHOPIFY_STORE`, `SHOPIFY_TOKEN`.

### Qué se regenera solo vs qué sigue siendo manual

| Archivo | ¿Automático? |
|---|---|
| `01-meta-mensual.md` | ✅ sí — gasto/clics/CPC/frecuencia por mes |
| `02-meta-campañas.md` | ✅ sí — mismo alcance, por campaña |
| `03-meta-fechas-clave.md` | ✅ sí — usa el calendario fijo `KEY_DATES` en `build_report_data.py`; agrega fechas nuevas ahí |
| `05-shopify-productos.md` | ✅ sí — top productos por revenue |
| `06-shopify-geo.md` | ✅ sí — distribución por estado |
| `07-shopify-promos.md` | ✅ sí — códigos de descuento usados |
| `08-shopify-clientes.md` | ✅ sí — LTV desde el objeto customer de Shopify (esto SÍ cubre el histórico completo, ver nota abajo) |
| `04-shopify-atribucion.md` | ❌ manual — requiere pedidos de Shopify de +60 días (ver nota) |
| `09-presupuesto.md` | ❌ manual a propósito — es una propuesta forward-looking, no un dato histórico |

### ⚠️ Dos hallazgos importantes al conectar las APIs (2026-07-06)

1. **El pixel de Meta no tiene ningún evento `purchase` configurado** — 0 conversiones de venta en los 3 años completos de la cuenta (`act_461452066012476`). El ROAS/Ventas que aparecían en reportes anteriores por mes/campaña no salían de atribución nativa de Meta; alguien los cruzó a mano contra Shopify. Vale la pena revisar si el Conversions API / Pixel del checkout está bien instalado — sin eso, Meta no puede optimizar la pauta hacia compras reales.
2. **El token de Shopify (`shpca_...`) solo puede leer pedidos (`orders.json`) de los últimos ~60 días** — es una restricción de Shopify para apps sin el scope `read_all_orders` (requiere aprobación de Shopify). Por eso `04-shopify-atribucion.md` (histórico completo, 542 transacciones) no se puede regenerar con este token; solo se pudo con un export manual o un token con ese scope aprobado. Los clientes (`08-shopify-clientes.md`) sí llegan completos porque Shopify guarda `total_spent`/`orders_count` ya agregado en el objeto customer, sin pasar por el límite de 60 días.

---

Generado con Meta Marketing API + Shopify Admin API.
