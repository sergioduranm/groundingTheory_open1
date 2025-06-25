# Sistema de Agentes para Análisis Cualitativo

## Descripción

Este proyecto implementa un sistema de agentes de IA para análisis cualitativo utilizando el ADK de Google Generative AI. El sistema está diseñado para procesar datos cualitativos y realizar codificación abierta de manera automatizada y eficiente.

## Instalación

### Prerrequisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. Clonar el repositorio:

```bash
git clone <url-del-repositorio>
cd groundingTheory_open1
```

2. Crear un entorno virtual:

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:

```bash
cp .env.example .env
# Editar .env con tus credenciales de Google AI
```

## Uso

### Ejecución básica

Para ejecutar el sistema de agentes:

```bash
python main.py
```

### Preprocesamiento de datos

Para convertir un archivo Excel a formato JSONL:

```bash
python preprocessor.py
```

## Estructura del Proyecto

````

## Configuración

### Variables de entorno

- `GOOGLE_API_KEY`: Clave de API de Google Generative AI
- `MODEL_NAME`: Nombre del modelo a utilizar (por defecto: gemini-pro)

## Desarrollo

### Ejecutar tests

```bash
pytest
````

### Formatear código

```bash
black .
```

### Verificar estilo de código

```bash
flake8
```

## Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## Contacto

- Autor: [Tu Nombre]
- Email: [tu-email@ejemplo.com]
- Proyecto: [URL del proyecto]
