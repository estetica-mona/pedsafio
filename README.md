# GoFile Converter API

Pequeña API en Python + Flask que convierte enlaces normales de GoFile (`https://gofile.io/d/<id>`) a enlaces de descarga directa.

Requisitos

- Windows PowerShell (ejemplos abajo)
- Python 3.8+

Instalación

```powershell
# crear entorno (opcional)
python -m venv venv; .\venv\Scripts\Activate
pip install -r requirements.txt
```

Ejecutar

```powershell
# desde la carpeta del proyecto
python app.py
```

Uso

POST /convert

Body JSON:

```json
{ "urls": ["https://gofile.io/d/ABC123", "https://gofile.io/d/DEF456" ] }
```

Ejemplo PowerShell (Invoke-RestMethod):

```powershell
$body = @{ urls = @('https://gofile.io/d/ABC123','https://gofile.io/d/DEF456') } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:5000/convert -Body $body -ContentType 'application/json'
```

La respuesta contendrá el listado de `direct_links` por cada `input`.

Notas

- El endpoint acepta hasta 3 URLs por petición.
- Si un enlace es una carpeta, la API listará los archivos dentro y devolverá los enlaces directos encontrados (puede devolver varios por input).
- Si los archivos están protegidos por contraseña, pasar `"password": "tu_password"` en el mismo JSON.

Endpoint fijo de 3 enlaces

También hay un endpoint fijo que convierte exactamente las 3 URLs solicitadas y devuelve 3 enlaces directos enumerados:

- `GET|POST /convert_fixed`

URLs fijas devueltas (labels):

- Standard: `https://gofile.io/d/en4HXu`
- Enhanced: `https://gofile.io/d/YbiRbg`
- Potato:   `https://gofile.io/d/Bm11pI`

Ejemplo (GET):

```powershell
Invoke-RestMethod -Method Get -Uri http://localhost:5000/convert_fixed
```

Ejemplo (POST con password):

```powershell
$body = @{ password = 'tu_password' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:5000/convert_fixed -Body $body -ContentType 'application/json'
```