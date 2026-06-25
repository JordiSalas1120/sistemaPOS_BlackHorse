# Sprint 4 — Catálogo Revista (PDF editorial, QR y ficha técnica)

> **Estado**: Implementado
> **Fecha**: 2026-06-25
> **Prerrequisito**: Sprint 3 completado (vitrina pública `/catalogo`, tabla `product_images`, endpoints `/api/v1/catalog/*`)

---

## 1. Objetivo y Alcance

### Objetivo

Convertir la vitrina pública del Sprint 3 en un **catálogo imprimible tipo revista** que el negocio puede descargar como PDF (una página A4 por producto), compartir por QR y enviar por WhatsApp. Cada producto se presenta como una **ficha de características** al estilo de las especificaciones de un celular o una computadora: la foto de la pieza junto a su modelo, ficha técnica (atributos), componentes, descripción y precio.

### Alcance del Sprint 4

**Incluido:**
- Ruta pública `/revista` — catálogo editorial A4, una página por producto, imprimible a PDF desde el navegador.
- Diseño editorial premium (tipografía serif Playfair Display, paleta cuero, portada y contraportada).
- **Ficha técnica por producto** (specs tipo celular/computadora) a partir de los atributos JSONB del producto.
- Helper compartido de atributos (`catalog-attributes.ts`): `getModelo`, `getComponentes`, `getSpecs`, `labelFor` + mapa de etiquetas legibles.
- Endpoint `GET /api/v1/catalog/qr` — genera un PNG con el QR del catálogo (o de una ruta puntual).
- **Marca de agua anti-plagio** "quemada" en las imágenes subidas (`watermark_text`).
- Card de **Catálogo público** en el dashboard (`CatalogShareCard`): URL copiable, QR descargable, accesos a catálogo/revista y compartir por WhatsApp.
- Botón **"Sugerir desde la receta"** en `ProductForm`: precarga los componentes del catálogo desde la receta (BOM) del producto.
- Variables de entorno nuevas: `watermark_text`, `catalog_public_base_url`.

**Excluido (Sprint 5+):**
- Generación de PDF en el servidor (hoy se usa la impresión del navegador → PDF).
- Carrito de compra público y pago en línea.
- Stock visible en el catálogo público.
- Plantillas de revista alternativas / personalización de marca por UI.

---

## 2. Decisiones de Arquitectura

### 2.1 PDF por impresión del navegador, no render en servidor

La ruta `/revista` está maquetada con CSS de impresión (`@media print`, `@page { size: A4; margin: 0 }`) de modo que cada `section.page` ocupa exactamente una hoja A4 (`page-break-after: always`). El usuario genera el PDF con **Descargar PDF → Imprimir → Guardar como PDF** (`window.print()` en `PrintButton`).

Ventajas frente a generar el PDF en el backend (WeasyPrint/ReportLab):
- Cero dependencias nuevas de render en el backend.
- El diseño es el mismo HTML/CSS que ya se ve en pantalla — un solo lugar que mantener.
- Las imágenes ya servidas desde `/media/` se reutilizan tal cual.

Trade-off: el resultado depende del navegador del usuario (se recomienda Chrome/Edge para fidelidad). Si en el futuro se necesita PDF determinístico (cron, email), se documenta migrar a render headless (Playwright) sobre la misma ruta `/revista`.

### 2.2 Ficha técnica derivada de `attributes` (JSONB), no columnas nuevas

Las características de cada producto (tipo de cuero, color, talla, peso, herrajes…) viven en el campo `products.attributes` (JSONB) ya existente. La ficha técnica se construye en el frontend a partir de esos pares clave/valor, sin migraciones ni columnas nuevas. Esto permite que cada categoría tenga specs distintas sin tocar el esquema.

El helper `labelFor()` traduce claves técnicas a etiquetas legibles (`leather_type` → "Tipo de cuero") y humaniza las claves desconocidas (`peso_kg` → "Peso Kg"), de modo que cualquier atributo cargado aparece presentable.

### 2.3 Helper de atributos único y compartido

`frontend/src/lib/catalog-attributes.ts` es la **única fuente** de cómo se interpretan los atributos del catálogo. Tanto el detalle público (`/catalogo/[sku]`) como la revista (`/revista`) consumen los mismos `getSpecs`/`labelFor`, evitando que las etiquetas se desincronicen (antes el mapeo estaba duplicado dentro de la página de detalle).

### 2.4 Marca de agua en subida, no al servir

La marca de agua se "quema" en el binario **una sola vez, al subir la imagen** (`apply_watermark` en el endpoint de subida), no en cada request de servido. Así nginx/StaticFiles sirve el archivo final sin coste de procesamiento por descarga, y la imagen protegida es la misma en catálogo, revista y al compartir.

---

## 3. Backend

### 3.1 Configuración — variables nuevas (`backend/src/config.py`)

```python
# ── Catálogo revista (Sprint 4) ──────────────────────────────────────────
# Texto de la marca de agua que se "quema" en las imágenes subidas (anti-plagio).
watermark_text: str = "BLACK HORSE"
# URL pública del sitio (frontend) que codifica el QR para compartir.
catalog_public_base_url: str = "http://localhost:3000"
```

`.env.example` (agregar):
```ini
# Catálogo revista (Sprint 4)
WATERMARK_TEXT=BLACK HORSE
CATALOG_PUBLIC_BASE_URL=http://localhost:3000
```

> El QR codifica `CATALOG_PUBLIC_BASE_URL + path`. Para compartir fuera de la máquina local hay que poner la IP/dominio real del servidor frontend.

### 3.2 Endpoint QR — `GET /api/v1/catalog/qr`

Archivo: `backend/src/infrastructure/api/v1/endpoints/catalog.py`

Genera un PNG con el QR que apunta a una ruta pública del catálogo (por defecto `/catalogo`; admite `?path=/catalogo/EQU-00001` para un producto puntual). Usa la librería `qrcode`. Respuesta `image/png` con `Cache-Control: public, max-age=3600`.

```python
@router.get("/qr", summary="Código QR para compartir el catálogo")
async def catalog_qr(path: str = Query("/catalogo")):
    if not path.startswith("/"):
        path = "/" + path
    url = f"{settings.catalog_public_base_url.rstrip('/')}{path}"
    img = qrcode.make(url)
    buf = io.BytesIO(); img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=3600"})
```

Dependencia nueva en `requirements.txt`: `qrcode[pil]`.

### 3.3 Marca de agua — `apply_watermark`

Archivo: `backend/src/infrastructure/media/watermark.py`, invocado desde el endpoint de subida de imágenes (`product_images.py`):

```python
# Marca de agua anti-plagio "quemada" en el archivo servido.
contents = apply_watermark(contents, extension, settings.watermark_text)
```

La marca se aplica sobre el binario antes de guardarlo en `/media/{product_id}/`. Dependencia: `Pillow`.

---

## 4. Frontend

### 4.1 Ruta `/revista` — catálogo editorial imprimible

```
frontend/src/app/revista/
  layout.tsx            — carga la fuente Playfair Display (serif editorial)
  page.tsx              — portada + un spread por producto + contraportada
  revista.module.css    — diseño A4, paleta cuero, reglas @media print
```

- `page.tsx` es **Server Component** (`dynamic = "force-dynamic"`): trae hasta 100 productos del catálogo con `catalogService.listProducts`.
- Cada producto se renderiza como un **spread** (foto a un lado, columna de datos al otro; alternando lado en páginas pares/impares).
- La columna muestra, en orden: folio, categoría, nombre, modelo, **Ficha técnica**, **Componentes**, descripción y fila de precio + SKU.
- La portada y la contraportada incluyen el **QR** (`/api/v1/catalog/qr`).
- `PrintButton` (`window.print()`) dispara la generación del PDF; la barra de herramientas se oculta en impresión.

### 4.2 Ficha técnica (specs tipo celular/computadora)

En `page.tsx`:
```tsx
const specs = getSpecs(p);  // [["Tipo de cuero","Vaqueta"], ["Color","Natural"], ...]
...
{specs.length > 0 && (
  <>
    <div className={styles.compTitle}>Ficha técnica</div>
    <dl className={styles.specs}>
      {specs.map(([label, value]) => (
        <div key={label} className={styles.specRow}>
          <dt className={styles.specKey}>{label}</dt>
          <dd className={styles.specVal}>{value}</dd>
        </div>
      ))}
    </dl>
  </>
)}
```

Estilo (en `revista.module.css`): filas clave/valor con línea separadora — clave en mayúsculas a la izquierda, valor en negrita a la derecha (look de hoja de especificaciones).

### 4.3 Helper de atributos — `src/lib/catalog-attributes.ts`

| Función | Qué hace |
|---------|----------|
| `getModelo(p)` | Devuelve `attributes.modelo` (ej. "Montura Beniana") o `null`. |
| `getComponentes(p)` | Lista de componentes desde `attributes.componentes` (array o texto separado por coma/salto). |
| `getExtraAttributes(p)` | Resto de atributos como `[clave, valor]`, excluyendo `modelo`/`componentes` y vacíos. |
| `labelFor(key)` | Etiqueta legible: usa `ATTRIBUTE_LABELS` o humaniza la clave. |
| `getSpecs(p)` | Ficha técnica: `[etiqueta, valor]` lista para mostrar (usa `getExtraAttributes` + `labelFor`). |
| `ATTRIBUTE_LABELS` | Mapa de claves conocidas: tipo de cuero, material, color, talla/medidas, peso, acabado, herrajes, costura, relleno, forro, origen, garantía, uso. |

### 4.4 Card de catálogo en el dashboard — `CatalogShareCard`

Archivo: `frontend/src/components/dashboard/CatalogShareCard.tsx`. Muestra el QR (descargable como PNG), el enlace del catálogo (copiable), y botones para **Abrir catálogo**, **Ver revista** y **compartir por WhatsApp**.

### 4.5 "Sugerir desde la receta" — `ProductForm`

Botón que precarga los componentes del catálogo a partir de la receta (BOM) del producto: llama a `workshopService.getBOM(product.id)`, toma los nombres de los materiales y los carga en el campo de componentes para que el usuario los edite. Si el producto no tiene BOM, avisa para crearla en el Taller o cargar los componentes a mano.

---

## 5. Cómo generar el PDF del catálogo

1. Cargar productos con `show_in_catalog = true` y, en cada uno, sus **atributos** (tipo de cuero, color, talla, peso, etc.) y **componentes** en el campo de atributos.
2. Subir al menos una imagen por producto (se marca primary automáticamente la primera).
3. Abrir `http://localhost:3000/revista` (o desde el dashboard → card "Catálogo público" → **Ver revista**).
4. Pulsar **Descargar PDF** → en el diálogo de impresión elegir **Guardar como PDF**, tamaño **A4**, márgenes **Ninguno**, activar **Gráficos de fondo**.

> Recomendado Chrome/Edge para máxima fidelidad del diseño.

---

## 6. Estado de archivos del Sprint 4

**Backend**
- `src/config.py` — vars `watermark_text`, `catalog_public_base_url`.
- `src/infrastructure/api/v1/endpoints/catalog.py` — endpoint `/qr`.
- `src/infrastructure/media/watermark.py` + integración en `product_images.py`.

**Frontend**
- `src/app/revista/{layout.tsx,page.tsx,revista.module.css}` — catálogo revista.
- `src/components/catalog/PrintButton.tsx` — botón imprimir/PDF.
- `src/lib/catalog-attributes.ts` — helper compartido (`getSpecs`, `labelFor`, `ATTRIBUTE_LABELS`).
- `src/app/catalogo/[sku]/page.tsx` — detalle público usando `labelFor` compartido.
- `src/components/dashboard/CatalogShareCard.tsx` — card de compartir.
- `src/components/products/ProductForm.tsx` — "Sugerir desde la receta".
