# 🔭 Laboratorio Guiado — Módulo 8, Sesión 1
## Observabilidad Serverless: Lambda · API Gateway · CloudWatch · X-Ray · SNS

**Programa:** Arquitectura de Soluciones Multinube — UTEC Posgrado  
**Docente:** Aldo Trucios  
**Duración estimada:** 2 horas  
**Nivel:** Intermedio

---

## 📋 Índice

1. [Objetivo del laboratorio](#1-objetivo-del-laboratorio)
2. [Prerrequisitos](#2-prerrequisitos)
3. [Variables de configuración personal](#3-variables-de-configuración-personal)
4. [Arquitectura del laboratorio](#4-arquitectura-del-laboratorio)
5. [Fase 1 — Infraestructura base: IAM Role + Lambda + API Gateway (35 min)](#5-fase-1--infraestructura-base-iam-role--lambda--api-gateway)
6. [Fase 2 — Explorar logs y métricas en CloudWatch (25 min)](#6-fase-2--explorar-logs-y-métricas-en-cloudwatch)
7. [Fase 3 — Alarmas CloudWatch + notificaciones SNS (20 min)](#7-fase-3--alarmas-cloudwatch--notificaciones-sns)
8. [Fase 4 — Dashboard de salud (20 min)](#8-fase-4--dashboard-de-salud)
9. [Validación y pruebas de carga](#9-validación-y-pruebas-de-carga)
10. [Limpieza de recursos](#10-limpieza-de-recursos)
11. [Preguntas de reflexión](#11-preguntas-de-reflexión)

---

## 1. Objetivo del laboratorio

Al finalizar este laboratorio, el alumno será capaz de:

- Desplegar una **función AWS Lambda** en Python con logs estructurados JSON y trazas **AWS X-Ray** nativas.
- Exponer la Lambda mediante **Amazon API Gateway** (HTTP API) simulando una API de pagos.
- Usar **CloudWatch Logs Insights** para consultar y analizar eventos de la función.
- Crear **métricas personalizadas** y **filtros de métrica** a partir de logs Lambda.
- Configurar **alarmas CloudWatch** con notificaciones vía **Amazon SNS**.
- Construir un **dashboard de salud** aplicando los métodos RED y USE sobre una arquitectura serverless.

> **¿Por qué Lambda y no Flask local?**  
> Lambda es el escenario real de observabilidad serverless: no hay servidor que hacer SSH, los logs se envían automáticamente a CloudWatch, el contexto de ejecución es efímero (el contenedor puede destruirse entre invocaciones) y AWS X-Ray se integra de forma nativa. Es exactamente el caso de uso que describen las diapositivas sobre infraestructura efímera y el fin de los monolitos.

---

## 2. Prerrequisitos

| Requisito | Detalle |
|-----------|---------|
| Cuenta AWS | Con permisos: `LambdaFullAccess`, `APIGatewayAdministrator`, `CloudWatchFullAccess`, `SNSFullAccess`, `AWSXRayFullAccess`, `IAMFullAccess` |
| Python | 3.11 o superior instalado localmente |
| AWS CLI | v2 instalado y configurado con `aws configure` |
| zip | Disponible en terminal (`zip --version`) |
| Editor | VS Code u otro editor de texto |

### Verificar AWS CLI

```bash
aws sts get-caller-identity
```

Debes ver tu `Account`, `UserId` y `Arn`. Si ves error, ejecuta `aws configure` primero.

### Verificar zip

```bash
zip --version
# En Windows (PowerShell) usa: Compress-Archive o instala 7-zip
```

---

## 3. Variables de configuración personal

> ⚠️ **IMPORTANTE:** Cada alumno debe definir su propio número para aislar los recursos en la cuenta AWS compartida. Todos los recursos llevan el prefijo `alumno-XX`.

Reemplaza `XX` con **tu número de alumno** (01 al 30):

```bash
# ── Ejecuta este bloque completo en tu terminal ──────────────────────────────
export ALUMNO_ID="alumno-XX"                        # ← cambia XX (ej: alumno-07)
export AWS_REGION="us-east-1"                       # ← región asignada por el docente
export EMAIL_ALERTA="tu-email@dominio.com"          # ← tu email real

# Derivados (no modificar)
export APP_NAME="payment-api-${ALUMNO_ID}"
export LAMBDA_NAME="payment-lambda-${ALUMNO_ID}"
export LOG_GROUP="/aws/lambda/${LAMBDA_NAME}"
export ROLE_NAME="lambda-obs-role-${ALUMNO_ID}"
export SNS_TOPIC_NAME="alertas-infra-${ALUMNO_ID}"
export DASHBOARD_NAME="salud-infra-${ALUMNO_ID}"
export API_NAME="payment-api-gw-${ALUMNO_ID}"
export METRIC_NAMESPACE="LabObservabilidad/${ALUMNO_ID}"

# Verificar
echo "──────────────────────────────────────"
echo "Alumno ID  : $ALUMNO_ID"
echo "Lambda     : $LAMBDA_NAME"
echo "Log Group  : $LOG_GROUP"
echo "Namespace  : $METRIC_NAMESPACE"
echo "API Gateway: $API_NAME"
echo "──────────────────────────────────────"
```

---

## 4. Arquitectura del laboratorio

```
                         ┌──────────────────────────────────────────┐
  Tu terminal / curl     │              AWS Cloud                    │
  (invocaciones)         │                                           │
       │                 │   ┌─────────────────┐                    │
       │  HTTPS          │   │  API Gateway     │                    │
       └────────────────►│   │  (HTTP API)      │                    │
                         │   │                  │                    │
                         │   │ /health  POST /pay│                   │
                         │   │ /slow    /error   │                   │
                         │   │ /simulate-load    │                   │
                         │   └────────┬─────────┘                   │
                         │            │ invoke                       │
                         │   ┌────────▼─────────────────────────┐   │
                         │   │       Lambda Function             │   │
                         │   │   payment-lambda-alumno-XX        │   │
                         │   │                                   │   │
                         │   │  • Logs JSON estructurados ──────►│──►│ CloudWatch Logs
                         │   │  • Trazas X-Ray ─────────────────│──►│ AWS X-Ray
                         │   │  • Métricas custom (boto3) ──────►│──►│ CloudWatch Metrics
                         │   └───────────────────────────────────┘   │
                         │                                           │
                         │   CloudWatch Logs                         │
                         │   └── /aws/lambda/payment-lambda-XX      │
                         │       ├── Metric Filter → PaymentErrors   │
                         │       └── Logs Insights (queries)         │
                         │                                           │
                         │   CloudWatch Alarms                       │
                         │   ├── PaymentErrors-High-XX               │
                         │   ├── HighLatency-XX (Duration p99)       │
                         │   └── LambdaErrors-XX (built-in)         │
                         │       └────► SNS Topic ──► Email         │
                         │                                           │
                         │   CloudWatch Dashboard                    │
                         │   └── salud-infra-XX (RED + USE)         │
                         └──────────────────────────────────────────┘
```

**¿Por qué Lambda resuelve el problema de la infraestructura efímera?**  
Lambda destruye el contenedor de ejecución después de un período de inactividad. Si dependen de logs locales, esos logs desaparecen. Con CloudWatch Logs integrado de forma nativa, **cada `print()` o `logger.info()` se persiste automáticamente** antes de que el contenedor muera.

---

## 5. Fase 1 — Infraestructura base: IAM Role + Lambda + API Gateway

### 5.1 Crear directorio de trabajo

```bash
mkdir lab-obs-${ALUMNO_ID}
cd lab-obs-${ALUMNO_ID}
mkdir lambda_package
```

### 5.2 Crear el código de la función Lambda

Crea el archivo `lambda_package/lambda_function.py` con el siguiente contenido completo. **No necesitas modificar nada**: las variables se leen desde el entorno de Lambda que configurarás en el paso 5.5.

```python
"""
Lab M08S01 — Función Lambda de pagos simulada.
Observabilidad nativa con:
  • CloudWatch Logs (logs estructurados JSON via print/logging)
  • AWS X-Ray (trazas distribuidas, integración nativa Lambda)
  • CloudWatch Custom Metrics (via boto3)

Endpoints simulados (vía API Gateway path):
  GET  /health          → health check
  POST /pay             → pago con 20% prob. de error
  GET  /slow            → respuesta lenta (500-2000ms)
  GET  /error           → error forzado
  GET  /simulate-load   → 15 transacciones internas simuladas
"""

import os
import json
import time
import random
import logging

import boto3
from aws_xray_sdk.core import xray_recorder, patch_all

# ── X-Ray: parchear boto3 automáticamente ─────────────────────────────────────
# patch_all() intercepta boto3, urllib3, etc. para generar Spans automáticamente
patch_all()

# ── Logging estructurado ───────────────────────────────────────────────────────
# En Lambda, print() y logging van directo a CloudWatch Logs.
# Usamos logging con formato JSON manual para que Logs Insights pueda indexarlo.
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ── Configuración desde variables de entorno Lambda ────────────────────────────
ALUMNO_ID        = os.environ.get("ALUMNO_ID", "alumno-XX")
AWS_REGION       = os.environ.get("AWS_REGION", "us-east-1")
APP_NAME         = os.environ.get("APP_NAME", f"payment-lambda-{ALUMNO_ID}")
METRIC_NAMESPACE = os.environ.get("METRIC_NAMESPACE", f"LabObservabilidad/{ALUMNO_ID}")

# ── CloudWatch Metrics (cliente reutilizable entre invocaciones tibias) ────────
cw_client = boto3.client("cloudwatch", region_name=AWS_REGION)


def log_json(level: str, message: str, **kwargs):
    """
    Emite un log estructurado en JSON.
    Lambda captura stdout y lo envía a CloudWatch Logs automáticamente.
    Usamos JSON para que Logs Insights pueda filtrar por campos como
    event_type, user_id, latency_ms, etc.
    """
    record = {
        "level": level,
        "message": message,
        "alumno_id": ALUMNO_ID,
        "app_name": APP_NAME,
    }
    record.update(kwargs)
    print(json.dumps(record))


def put_metric(metric_name: str, value: float, unit: str = "Count"):
    """Publica una métrica personalizada en CloudWatch Metrics."""
    try:
        cw_client.put_metric_data(
            Namespace=METRIC_NAMESPACE,
            MetricData=[{
                "MetricName": metric_name,
                "Dimensions": [{"Name": "AppName", "Value": APP_NAME}],
                "Value": value,
                "Unit": unit,
            }]
        )
    except Exception as exc:
        log_json("ERROR", "Error publicando métrica",
                 metric=metric_name, error=str(exc))


# ── Handlers por ruta ──────────────────────────────────────────────────────────

def handle_health(event: dict) -> dict:
    log_json("INFO", "Health check OK", event_type="health_check")
    put_metric("HealthCheck", 1)
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "ok",
            "service": APP_NAME,
            "alumno": ALUMNO_ID,
        })
    }


def handle_pay(event: dict) -> dict:
    start = time.time()

    # Parsear body del request
    body = {}
    if event.get("body"):
        try:
            body = json.loads(event["body"])
        except json.JSONDecodeError:
            pass

    amount  = body.get("amount", 0)
    user_id = body.get("user_id", "anonymous")

    # Sub-segmento X-Ray: simular consulta a base de datos
    with xray_recorder.in_subsegment("db-payment-query") as subseg:
        subseg.put_annotation("table", "payments")
        subseg.put_annotation("user_id", user_id)
        db_latency = random.uniform(0.05, 0.15)
        time.sleep(db_latency)

    # 20% de probabilidad de fallo (gateway timeout simulado)
    if random.random() < 0.20:
        elapsed_ms = (time.time() - start) * 1000
        log_json("ERROR", "Pago fallido — gateway timeout",
                 event_type="payment_failed",
                 user_id=user_id,
                 amount=amount,
                 gateway_error=504,
                 latency_ms=round(elapsed_ms, 2))
        put_metric("PaymentErrors", 1)
        put_metric("RequestLatency", elapsed_ms, unit="Milliseconds")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "code": "GATEWAY_TIMEOUT",
                "message": "El servicio de pagos no responde",
            })
        }

    elapsed_ms = (time.time() - start) * 1000
    txn_id = f"TXN-{random.randint(10000, 99999)}"
    log_json("INFO", "Pago procesado exitosamente",
             event_type="payment_success",
             user_id=user_id,
             amount=amount,
             transaction_id=txn_id,
             latency_ms=round(elapsed_ms, 2))
    put_metric("PaymentSuccess", 1)
    put_metric("RequestLatency", elapsed_ms, unit="Milliseconds")
    return {
        "statusCode": 200,
        "body": json.dumps({
            "status": "ok",
            "transaction_id": txn_id,
            "amount": amount,
        })
    }


def handle_slow(event: dict) -> dict:
    start  = time.time()
    delay  = random.uniform(0.5, 2.0)
    time.sleep(delay)
    elapsed_ms = (time.time() - start) * 1000

    log_json("WARNING", "Respuesta lenta detectada",
             event_type="slow_response",
             endpoint="/slow",
             latency_ms=round(elapsed_ms, 2))
    put_metric("RequestLatency", elapsed_ms, unit="Milliseconds")
    put_metric("SlowRequests", 1)
    return {
        "statusCode": 200,
        "body": json.dumps({"status": "ok", "latency_ms": round(elapsed_ms, 2)})
    }


def handle_error(event: dict) -> dict:
    log_json("ERROR", "Error forzado para prueba de alarma",
             event_type="forced_error",
             error_code="INTERNAL_500")
    put_metric("ApplicationErrors", 1)
    put_metric("PaymentErrors", 1)
    return {
        "statusCode": 500,
        "body": json.dumps({"error": "Error forzado para prueba de alarma"})
    }


def handle_simulate_load(event: dict) -> dict:
    """
    Genera 15 transacciones simuladas internamente dentro de la misma invocación.
    Útil para poblar métricas y trazas rápidamente sin llamadas externas.
    """
    results = {"success": 0, "errors": 0}

    for i in range(15):
        with xray_recorder.in_subsegment(f"simulated-payment-{i}") as subseg:
            subseg.put_annotation("simulation", "true")
            latency = random.uniform(0.02, 0.3)
            time.sleep(latency)
            if random.random() < 0.25:
                results["errors"] += 1
                put_metric("PaymentErrors", 1)
                put_metric("RequestLatency", latency * 1000, unit="Milliseconds")
            else:
                results["success"] += 1
                put_metric("PaymentSuccess", 1)
                put_metric("RequestLatency", latency * 1000, unit="Milliseconds")

    log_json("INFO", "Simulación de carga completada",
             event_type="load_simulation",
             success=results["success"],
             errors=results["errors"])
    return {
        "statusCode": 200,
        "body": json.dumps({"simulation": "complete", "results": results})
    }


# ── Handler principal de Lambda ────────────────────────────────────────────────

# Tabla de ruteo: path HTTP → función handler
ROUTES = {
    "/health":        handle_health,
    "/pay":           handle_pay,
    "/slow":          handle_slow,
    "/error":         handle_error,
    "/simulate-load": handle_simulate_load,
}


def lambda_handler(event: dict, context):
    """
    Punto de entrada principal de la Lambda.
    Recibe el evento de API Gateway (HTTP API payload v2) y
    enruta al handler correspondiente según el path.
    """
    path   = event.get("rawPath", "/health")
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")

    log_json("INFO", "Petición recibida",
             event_type="request_start",
             path=path,
             method=method,
             lambda_request_id=context.aws_request_id,
             remaining_ms=context.get_remaining_time_in_millis())

    # Anotaciones X-Ray a nivel de segmento raíz
    xray_recorder.current_segment().put_annotation("alumno_id", ALUMNO_ID)
    xray_recorder.current_segment().put_annotation("path", path)

    handler_fn = ROUTES.get(path, handle_health)

    try:
        response = handler_fn(event)
    except Exception as exc:
        log_json("ERROR", "Excepción no controlada en handler",
                 event_type="unhandled_exception",
                 path=path,
                 error=str(exc))
        put_metric("ApplicationErrors", 1)
        response = {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }

    # Asegurar headers de respuesta para API Gateway
    response.setdefault("headers", {"Content-Type": "application/json"})
    return response
```

### 5.3 Instalar dependencia de X-Ray en el paquete

Lambda no incluye `aws-xray-sdk` en su runtime de Python 3.11. Debes empaquetarlo junto con el código:

```bash
# Desde el directorio lab-obs-${ALUMNO_ID}
pip install aws-xray-sdk -t lambda_package/
echo "✅ Dependencias instaladas en lambda_package/"
```

### 5.4 Empaquetar la función en un ZIP

```bash
cd lambda_package
zip -r ../function.zip . -q
cd ..
echo "✅ Paquete creado: $(du -sh function.zip | cut -f1) — function.zip"
```

### 5.5 Crear el IAM Role para Lambda

Lambda necesita un rol con permisos para escribir en CloudWatch Logs, publicar métricas, enviar trazas a X-Ray y publicar en SNS.

```bash
# 1 — Crear el rol con trust policy para Lambda
aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' \
    --region $AWS_REGION

echo "✅ Rol IAM creado: $ROLE_NAME"

# 2 — Adjuntar políticas gestionadas necesarias
aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess

aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess

echo "✅ Políticas adjuntadas al rol"

# 3 — Obtener ARN del rol
ROLE_ARN=$(aws iam get-role \
    --role-name "$ROLE_NAME" \
    --query "Role.Arn" \
    --output text)

echo "Role ARN: $ROLE_ARN"
export ROLE_ARN

# Esperar propagación de IAM (necesario antes de crear la Lambda)
echo "⏳ Esperando propagación de IAM (15 segundos)..."
sleep 15
```

### 5.6 Crear la función Lambda

```bash
LAMBDA_ARN=$(aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --runtime python3.11 \
    --role "$ROLE_ARN" \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://function.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment "Variables={
        ALUMNO_ID=${ALUMNO_ID},
        APP_NAME=${LAMBDA_NAME},
        METRIC_NAMESPACE=LabObservabilidad/${ALUMNO_ID}
    }" \
    --tracing-config Mode=Active \
    --region $AWS_REGION \
    --query "FunctionArn" \
    --output text)

echo "✅ Lambda creada:"
echo "   ARN: $LAMBDA_ARN"
export LAMBDA_ARN

aws lambda wait function-active \
    --function-name "$LAMBDA_NAME" \
    --region $AWS_REGION
echo "✅ Lambda en estado Active"
```

> **`--tracing-config Mode=Active`** activa X-Ray automáticamente: Lambda inyecta el Trace ID en cada invocación y el daemon de X-Ray está integrado en el entorno de ejecución. No necesitas correr nada extra.

### 5.7 Probar la Lambda directamente (sin API Gateway aún)

```bash
# Invocar /health
aws lambda invoke \
    --function-name "$LAMBDA_NAME" \
    --payload '{"rawPath": "/health", "requestContext": {"http": {"method": "GET"}}}' \
    --cli-binary-format raw-in-base64-out \
    --region $AWS_REGION \
    response.json && cat response.json

echo ""

# Invocar /pay con body JSON
aws lambda invoke \
    --function-name "$LAMBDA_NAME" \
    --payload '{"rawPath": "/pay", "requestContext": {"http": {"method": "POST"}}, "body": "{\"amount\": 200, \"user_id\": \"user-test\"}"}' \
    --cli-binary-format raw-in-base64-out \
    --region $AWS_REGION \
    response.json && cat response.json
```

Si ves `{"status": "ok", ...}` o `{"status": "error", ...}` (20% prob), la Lambda funciona. ✅

### 5.8 Crear API Gateway (HTTP API)

```bash
# 1 — Crear la HTTP API
API_ID=$(aws apigatewayv2 create-api \
    --name "$API_NAME" \
    --protocol-type HTTP \
    --region $AWS_REGION \
    --query "ApiId" \
    --output text)

echo "API Gateway ID: $API_ID"
export API_ID

# 2 — Crear integración Lambda → API Gateway
INTEGRATION_ID=$(aws apigatewayv2 create-integration \
    --api-id "$API_ID" \
    --integration-type AWS_PROXY \
    --integration-uri "arn:aws:apigateway:${AWS_REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations" \
    --payload-format-version "2.0" \
    --region $AWS_REGION \
    --query "IntegrationId" \
    --output text)

echo "Integration ID: $INTEGRATION_ID"

# 3 — Crear rutas para cada endpoint
for ROUTE in "GET /health" "POST /pay" "GET /slow" "GET /error" "GET /simulate-load"; do
    aws apigatewayv2 create-route \
        --api-id "$API_ID" \
        --route-key "$ROUTE" \
        --target "integrations/${INTEGRATION_ID}" \
        --region $AWS_REGION \
        --query "RouteId" \
        --output text | xargs echo "  Ruta creada: $ROUTE → RouteId:"
done

# 4 — Crear stage de despliegue ($default)
aws apigatewayv2 create-stage \
    --api-id "$API_ID" \
    --stage-name '$default' \
    --auto-deploy \
    --region $AWS_REGION > /dev/null

echo "✅ Stage \$default creado con auto-deploy"

# 5 — Permiso para que API Gateway invoque la Lambda
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws lambda add-permission \
    --function-name "$LAMBDA_NAME" \
    --statement-id "apigateway-invoke-${ALUMNO_ID}" \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${AWS_REGION}:${ACCOUNT_ID}:${API_ID}/*" \
    --region $AWS_REGION > /dev/null

echo "✅ Permiso de invocación concedido a API Gateway"

# 6 — Obtener la URL pública de la API
API_URL=$(aws apigatewayv2 get-api \
    --api-id "$API_ID" \
    --region $AWS_REGION \
    --query "ApiEndpoint" \
    --output text)

echo ""
echo "══════════════════════════════════════════"
echo "  🌐 URL de tu API:"
echo "  $API_URL"
echo "══════════════════════════════════════════"
export API_URL
```

### 5.9 Verificar la API desde el navegador o curl

```bash
# Health check
curl "${API_URL}/health"

# Pago (puede devolver error 500 el ~20% de las veces, es normal)
curl -X POST "${API_URL}/pay" \
     -H "Content-Type: application/json" \
     -d '{"amount": 350, "user_id": "user-lab-01"}'

# Endpoint lento
curl "${API_URL}/slow"

# Simulación de carga (15 transacciones internas)
curl "${API_URL}/simulate-load"
```

---

## 6. Fase 2 — Explorar logs y métricas en CloudWatch

### 6.1 Ver logs de la Lambda en la consola

1. Abre **AWS Console** → **CloudWatch** → **Log groups**
2. Busca `/aws/lambda/payment-lambda-${ALUMNO_ID}`
3. Abre el Log Stream más reciente
4. Deberías ver entradas JSON como:

```json
{
  "level": "INFO",
  "message": "Petición recibida",
  "event_type": "request_start",
  "path": "/pay",
  "method": "POST",
  "alumno_id": "alumno-07",
  "app_name": "payment-lambda-alumno-07"
}
```

### 6.2 Generar datos para analizar

```bash
# Ejecuta este bloque para generar ~50 invocaciones variadas
echo "🚀 Generando tráfico de prueba..."
for i in $(seq 1 20); do
    curl -s -X POST "${API_URL}/pay" \
         -H "Content-Type: application/json" \
         -d "{\"amount\": $((RANDOM % 1000 + 10)), \"user_id\": \"user-$((RANDOM % 15 + 1))\"}" \
         > /dev/null
    
    # Cada 4 iteraciones, endpoint lento
    [ $((i % 4)) -eq 0 ] && curl -s "${API_URL}/slow" > /dev/null
    
    # Cada 7 iteraciones, error forzado
    [ $((i % 7)) -eq 0 ] && curl -s "${API_URL}/error" > /dev/null
    
    printf "."
done
curl -s "${API_URL}/simulate-load" > /dev/null
echo ""
echo "✅ Tráfico generado. Espera 30 segundos para que los logs lleguen a CloudWatch."
sleep 30
```

### 6.3 Consultas con CloudWatch Logs Insights

Ve a **CloudWatch** → **Logs Insights** → selecciona el log group `/aws/lambda/payment-lambda-${ALUMNO_ID}` y ejecuta estas consultas:

---

**Consulta 1 — Todos los errores recientes (diagnóstico rápido):**
```sql
fields @timestamp, level, message, user_id, latency_ms, error_code
| filter level = "ERROR"
| sort @timestamp desc
| limit 25
```

---

**Consulta 2 — Tasa de transacciones por tipo (método RED → Rate):**
```sql
fields event_type
| filter ispresent(event_type)
| stats count(*) as total by event_type
| sort total desc
```

---

**Consulta 3 — Latencia P50, P90 y P99 (método RED → Duration):**
```sql
fields latency_ms
| filter ispresent(latency_ms)
| stats
    avg(latency_ms)        as avg_ms,
    pct(latency_ms, 50)    as p50_ms,
    pct(latency_ms, 90)    as p90_ms,
    pct(latency_ms, 99)    as p99_ms,
    max(latency_ms)        as max_ms
```

---

**Consulta 4 — Usuarios con más pagos fallidos:**
```sql
fields user_id, amount
| filter event_type = "payment_failed"
| stats count(*) as failures, avg(latency_ms) as avg_latency by user_id
| sort failures desc
| limit 10
```

---

**Consulta 5 — Duración Lambda por invocación (métrica nativa):**
```sql
filter @type = "REPORT"
| parse @message "Duration: * ms\tBilled Duration: * ms\tMemory Size: * MB\tMax Memory Used: * MB"
    as duration, billed, memSize, memUsed
| stats
    avg(duration)    as avg_duration_ms,
    max(duration)    as max_duration_ms,
    avg(memUsed)     as avg_mem_mb
```

> 💡 **Nota:** Los logs con `@type = "REPORT"` son generados automáticamente por Lambda para cada invocación e incluyen duración, memoria usada y costo estimado.

---

### 6.4 Crear filtros de métricas desde logs

Los filtros de métrica convierten patrones en logs en métricas CloudWatch consultables y alertables.

```bash
# Filtro 1: Contar errores de pago desde logs JSON
aws logs put-metric-filter \
    --log-group-name "$LOG_GROUP" \
    --filter-name "PaymentErrorsFilter-${ALUMNO_ID}" \
    --filter-pattern '{ $.event_type = "payment_failed" }' \
    --metric-transformations \
        metricName=PaymentErrorsFromLogs,\
metricNamespace="LabObservabilidad/${ALUMNO_ID}",\
metricValue=1,\
defaultValue=0 \
    --region $AWS_REGION

echo "✅ Filtro de errores de pago creado"

# Filtro 2: Contar respuestas lentas desde logs JSON
aws logs put-metric-filter \
    --log-group-name "$LOG_GROUP" \
    --filter-name "SlowResponseFilter-${ALUMNO_ID}" \
    --filter-pattern '{ $.event_type = "slow_response" }' \
    --metric-transformations \
        metricName=SlowResponsesFromLogs,\
metricNamespace="LabObservabilidad/${ALUMNO_ID}",\
metricValue=1,\
defaultValue=0 \
    --region $AWS_REGION

echo "✅ Filtro de respuestas lentas creado"

# Verificar que los filtros existen
aws logs describe-metric-filters \
    --log-group-name "$LOG_GROUP" \
    --region $AWS_REGION \
    --query "metricFilters[*].{Filtro:filterName, Patron:filterPattern}" \
    --output table
```

---

## 7. Fase 3 — Alarmas CloudWatch + notificaciones SNS

### 7.1 Crear el topic SNS y suscribir tu email

```bash
# Crear topic
SNS_ARN=$(aws sns create-topic \
    --name "$SNS_TOPIC_NAME" \
    --region $AWS_REGION \
    --query "TopicArn" \
    --output text)

echo "SNS Topic ARN: $SNS_ARN"
export SNS_ARN

# Suscribir email
aws sns subscribe \
    --topic-arn "$SNS_ARN" \
    --protocol email \
    --notification-endpoint "$EMAIL_ALERTA" \
    --region $AWS_REGION

echo ""
echo "⚠️  ACCIÓN REQUERIDA: Revisa tu bandeja de entrada ($EMAIL_ALERTA)"
echo "   y haz clic en 'Confirm subscription' antes de continuar."
echo "   (Revisa también la carpeta de spam)"
```

### 7.2 Alarma 1 — Errores de pago (desde métricas custom)

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "PaymentErrors-High-${ALUMNO_ID}" \
    --alarm-description "[${ALUMNO_ID}] ALERTA: Errores de pago superaron 5 en 5 minutos" \
    --namespace "LabObservabilidad/${ALUMNO_ID}" \
    --metric-name "PaymentErrors" \
    --dimensions Name=AppName,Value="${LAMBDA_NAME}" \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 5 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --alarm-actions "$SNS_ARN" \
    --ok-actions "$SNS_ARN" \
    --treat-missing-data notBreaching \
    --region $AWS_REGION

echo "✅ Alarma 1: PaymentErrors-High"
```

### 7.3 Alarma 2 — Latencia alta P99 (desde métricas custom)

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "HighLatency-${ALUMNO_ID}" \
    --alarm-description "[${ALUMNO_ID}] ALERTA: Latencia P99 superó 1500ms" \
    --namespace "LabObservabilidad/${ALUMNO_ID}" \
    --metric-name "RequestLatency" \
    --dimensions Name=AppName,Value="${LAMBDA_NAME}" \
    --extended-statistic p99 \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1500 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --alarm-actions "$SNS_ARN" \
    --ok-actions "$SNS_ARN" \
    --treat-missing-data notBreaching \
    --region $AWS_REGION

echo "✅ Alarma 2: HighLatency"
```

### 7.4 Alarma 3 — Errores nativos de Lambda (métrica built-in)

Lambda publica automáticamente la métrica `Errors` en el namespace `AWS/Lambda`. Esta alarma usa esa métrica nativa.

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "LambdaErrors-${ALUMNO_ID}" \
    --alarm-description "[${ALUMNO_ID}] ALERTA: Lambda retornó errores (HTTP 5xx)" \
    --namespace "AWS/Lambda" \
    --metric-name "Errors" \
    --dimensions Name=FunctionName,Value="${LAMBDA_NAME}" \
    --statistic Sum \
    --period 60 \
    --evaluation-periods 2 \
    --threshold 3 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --alarm-actions "$SNS_ARN" \
    --ok-actions "$SNS_ARN" \
    --treat-missing-data notBreaching \
    --region $AWS_REGION

echo "✅ Alarma 3: LambdaErrors (built-in)"
```

### 7.5 Alarma 4 — Throttles de Lambda (USE → Saturación)

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "LambdaThrottles-${ALUMNO_ID}" \
    --alarm-description "[${ALUMNO_ID}] ALERTA: Lambda está siendo throttleada (saturación)" \
    --namespace "AWS/Lambda" \
    --metric-name "Throttles" \
    --dimensions Name=FunctionName,Value="${LAMBDA_NAME}" \
    --statistic Sum \
    --period 60 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --alarm-actions "$SNS_ARN" \
    --treat-missing-data notBreaching \
    --region $AWS_REGION

echo "✅ Alarma 4: LambdaThrottles (saturación USE)"
```

### 7.6 Ver estado de las alarmas

```bash
aws cloudwatch describe-alarms \
    --alarm-name-prefix "${ALUMNO_ID}" \
    --region $AWS_REGION \
    --query "MetricAlarms[*].{Alarma:AlarmName, Estado:StateValue, Umbral:Threshold}" \
    --output table
```

### 7.7 Disparar las alarmas (prueba)

```bash
echo "🔥 Generando errores para disparar alarmas..."
for i in $(seq 1 15); do
    curl -s "${API_URL}/error" > /dev/null
    printf "."
    sleep 1
done
echo ""
echo "⏳ Las alarmas tardan ~2 minutos en evaluarse. Revisa tu email y la consola CloudWatch."
```

---

## 8. Fase 4 — Dashboard de salud

### 8.1 Obtener el Account ID (necesario para los ARNs de alarmas)

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ACCOUNT_ID
echo "Account ID: $ACCOUNT_ID"
```

### 8.2 Crear el dashboard

```bash
DASHBOARD_JSON=$(cat << DASHBOARD_EOF
{
  "widgets": [
    {
      "type": "text",
      "x": 0, "y": 0, "width": 24, "height": 2,
      "properties": {
        "markdown": "# 🔭 Dashboard Observabilidad Serverless — ${ALUMNO_ID}\n**Lambda:** \`${LAMBDA_NAME}\` · **API Gateway:** \`${API_ID}\` · **Metodologías:** RED (Rate · Errors · Duration) + USE (Utilization · Saturation · Errors)"
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 2, "width": 8, "height": 6,
      "properties": {
        "title": "📊 RED — Rate: Invocaciones totales",
        "view": "timeSeries",
        "metrics": [
          ["LabObservabilidad/${ALUMNO_ID}", "PaymentSuccess", "AppName", "${LAMBDA_NAME}", {"label": "Pagos exitosos", "color": "#2ca02c"}],
          ["LabObservabilidad/${ALUMNO_ID}", "PaymentErrors",  "AppName", "${LAMBDA_NAME}", {"label": "Pagos fallidos", "color": "#d62728"}],
          ["AWS/Lambda", "Invocations", "FunctionName", "${LAMBDA_NAME}", {"label": "Invocaciones Lambda", "color": "#1f77b4"}]
        ],
        "period": 60,
        "stat": "Sum",
        "region": "${AWS_REGION}",
        "yAxis": {"left": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "x": 8, "y": 2, "width": 8, "height": 6,
      "properties": {
        "title": "❌ RED — Errors: Tasa de error Lambda (%)",
        "view": "timeSeries",
        "metrics": [
          ["AWS/Lambda", "Errors",       "FunctionName", "${LAMBDA_NAME}", {"id": "e1", "visible": false}],
          ["AWS/Lambda", "Invocations",  "FunctionName", "${LAMBDA_NAME}", {"id": "i1", "visible": false}],
          [{"expression": "(e1/(i1+0.001))*100", "label": "Error Rate %", "color": "#ff7f0e"}]
        ],
        "period": 60,
        "stat": "Sum",
        "region": "${AWS_REGION}",
        "yAxis": {"left": {"min": 0, "max": 100}}
      }
    },
    {
      "type": "metric",
      "x": 16, "y": 2, "width": 8, "height": 6,
      "properties": {
        "title": "⏱️ RED — Duration: Latencia Lambda (ms)",
        "view": "timeSeries",
        "metrics": [
          ["AWS/Lambda", "Duration", "FunctionName", "${LAMBDA_NAME}", {"stat": "p50",  "label": "p50"}],
          ["AWS/Lambda", "Duration", "FunctionName", "${LAMBDA_NAME}", {"stat": "p90",  "label": "p90"}],
          ["AWS/Lambda", "Duration", "FunctionName", "${LAMBDA_NAME}", {"stat": "p99",  "label": "p99 ⚠️", "color": "#d62728"}],
          ["AWS/Lambda", "Duration", "FunctionName", "${LAMBDA_NAME}", {"stat": "Maximum", "label": "Max", "color": "#9467bd"}]
        ],
        "period": 60,
        "region": "${AWS_REGION}"
      }
    },
    {
      "type": "metric",
      "x": 0, "y": 8, "width": 8, "height": 6,
      "properties": {
        "title": "🧠 USE — Utilization: Memoria Lambda",
        "view": "timeSeries",
        "metrics": [
          ["AWS/Lambda", "Duration", "FunctionName", "${LAMBDA_NAME}", {"stat": "Average", "label": "Duración promedio (ms)"}]
        ],
        "period": 60,
        "stat": "Average",
        "region": "${AWS_REGION}"
      }
    },
    {
      "type": "metric",
      "x": 8, "y": 8, "width": 8, "height": 6,
      "properties": {
        "title": "⛔ USE — Saturation: Throttles Lambda",
        "view": "timeSeries",
        "metrics": [
          ["AWS/Lambda", "Throttles",          "FunctionName", "${LAMBDA_NAME}", {"label": "Throttles",          "color": "#d62728"}],
          ["AWS/Lambda", "ConcurrentExecutions","FunctionName", "${LAMBDA_NAME}", {"label": "Ejecuciones concurrentes", "color": "#ff7f0e"}]
        ],
        "period": 60,
        "stat": "Sum",
        "region": "${AWS_REGION}",
        "yAxis": {"left": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "x": 16, "y": 8, "width": 8, "height": 6,
      "properties": {
        "title": "🏥 Health Checks & Latencia custom",
        "view": "timeSeries",
        "metrics": [
          ["LabObservabilidad/${ALUMNO_ID}", "HealthCheck",    "AppName", "${LAMBDA_NAME}", {"label": "Health Checks", "color": "#2ca02c"}],
          ["LabObservabilidad/${ALUMNO_ID}", "SlowRequests",   "AppName", "${LAMBDA_NAME}", {"label": "Respuestas lentas", "color": "#ff7f0e"}]
        ],
        "period": 60,
        "stat": "Sum",
        "region": "${AWS_REGION}"
      }
    },
    {
      "type": "alarm",
      "x": 0, "y": 14, "width": 24, "height": 4,
      "properties": {
        "title": "🚨 Estado de Alarmas",
        "alarms": [
          "arn:aws:cloudwatch:${AWS_REGION}:${ACCOUNT_ID}:alarm:PaymentErrors-High-${ALUMNO_ID}",
          "arn:aws:cloudwatch:${AWS_REGION}:${ACCOUNT_ID}:alarm:HighLatency-${ALUMNO_ID}",
          "arn:aws:cloudwatch:${AWS_REGION}:${ACCOUNT_ID}:alarm:LambdaErrors-${ALUMNO_ID}",
          "arn:aws:cloudwatch:${AWS_REGION}:${ACCOUNT_ID}:alarm:LambdaThrottles-${ALUMNO_ID}"
        ]
      }
    },
    {
      "type": "log",
      "x": 0, "y": 18, "width": 24, "height": 6,
      "properties": {
        "title": "📋 Logs recientes — Errores de pago",
        "query": "SOURCE '${LOG_GROUP}' | fields @timestamp, level, message, user_id, amount, latency_ms | filter event_type = \"payment_failed\" | sort @timestamp desc | limit 15",
        "region": "${AWS_REGION}",
        "view": "table"
      }
    }
  ]
}
DASHBOARD_EOF
)

aws cloudwatch put-dashboard \
    --dashboard-name "$DASHBOARD_NAME" \
    --dashboard-body "$DASHBOARD_JSON" \
    --region $AWS_REGION

echo "✅ Dashboard creado: $DASHBOARD_NAME"
echo ""
echo "🔗 URL del dashboard:"
echo "   https://${AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region=${AWS_REGION}#dashboards:name=${DASHBOARD_NAME}"
```

### 8.3 Ver las trazas en X-Ray

```bash
# Resumen de trazas de los últimos 5 minutos
END_TIME=$(date +%s)
START_TIME=$((END_TIME - 300))

aws xray get-trace-summaries \
    --start-time $START_TIME \
    --end-time $END_TIME \
    --region $AWS_REGION \
    --query "TraceSummaries[0:5].{ID:Id, Duracion_seg:Duration, Tiene_Error:HasError, Tiene_Fault:HasFault}" \
    --output table
```

Para el mapa de servicios visual:  
**CloudWatch console** → **X-Ray traces** → **Service map**

Verás nodos para: `payment-lambda-alumno-XX` → `cloudwatch` (métricas custom via boto3)

---

## 9. Validación y pruebas de carga

### 9.1 Script de carga completa

Crea el archivo `load_test.sh`:

```bash
#!/bin/bash
# ── Prueba de carga para lab-obs-${ALUMNO_ID} ──────────────────────────────
# Requiere que API_URL esté exportada en el entorno.

if [ -z "$API_URL" ]; then
    echo "❌ La variable API_URL no está definida. Vuelve a la Fase 1 y exporta API_URL."
    exit 1
fi

echo "🚀 Iniciando prueba de carga: $API_URL"
echo "   Duración aprox: 60 segundos"
echo ""

SUCCESS=0
ERRORS=0
SLOW=0

for i in $(seq 1 40); do
    # Pago normal (endpoint principal)
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "${API_URL}/pay" \
             -H "Content-Type: application/json" \
             -d "{\"amount\": $((RANDOM % 800 + 50)), \"user_id\": \"user-$((RANDOM % 20 + 1))\"}")
    
    if [ "$STATUS" = "200" ]; then
        SUCCESS=$((SUCCESS + 1))
    else
        ERRORS=$((ERRORS + 1))
    fi

    # Endpoint lento cada 5 iteraciones
    if [ $((i % 5)) -eq 0 ]; then
        curl -s "${API_URL}/slow" > /dev/null
        SLOW=$((SLOW + 1))
        printf "S"
    fi

    # Error forzado cada 8 iteraciones
    if [ $((i % 8)) -eq 0 ]; then
        curl -s "${API_URL}/error" > /dev/null
        printf "E"
    fi

    # Simulación de carga cada 10 iteraciones
    if [ $((i % 10)) -eq 0 ]; then
        curl -s "${API_URL}/simulate-load" > /dev/null
        printf "L"
    fi

    printf "."
    sleep 1
done

echo ""
echo ""
echo "══════════════════════════════════════"
echo "  📊 Resultado de la prueba:"
echo "  Pagos exitosos : $SUCCESS"
echo "  Pagos fallidos : $ERRORS"
echo "  Endpoints lentos: $SLOW"
echo "  Error rate     : $(echo "scale=1; $ERRORS * 100 / ($SUCCESS + $ERRORS)" | bc)%"
echo "══════════════════════════════════════"
echo ""
echo "✅ Prueba completada."
echo "   Espera 2-3 minutos y refresca el dashboard en CloudWatch."
```

```bash
chmod +x load_test.sh
./load_test.sh
```

### 9.2 Verificar métricas custom desde CLI

```bash
# Métricas de PaymentErrors en los últimos 15 minutos
aws cloudwatch get-metric-statistics \
    --namespace "LabObservabilidad/${ALUMNO_ID}" \
    --metric-name "PaymentErrors" \
    --dimensions Name=AppName,Value="${LAMBDA_NAME}" \
    --start-time $(date -u -d '-15 minutes' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
                  || date -u -v-15M +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Sum \
    --region $AWS_REGION \
    --output table
```

### 9.3 Listar todas las métricas de tu namespace

```bash
aws cloudwatch list-metrics \
    --namespace "LabObservabilidad/${ALUMNO_ID}" \
    --region $AWS_REGION \
    --query "Metrics[*].MetricName" \
    --output table
```

---

## 10. Limpieza de recursos

> ⚠️ **Ejecuta todo este bloque al finalizar la clase** para evitar costos.

```bash
echo "🧹 Eliminando recursos de ${ALUMNO_ID}..."

# 1 — Alarmas CloudWatch
aws cloudwatch delete-alarms \
    --alarm-names \
        "PaymentErrors-High-${ALUMNO_ID}" \
        "HighLatency-${ALUMNO_ID}" \
        "LambdaErrors-${ALUMNO_ID}" \
        "LambdaThrottles-${ALUMNO_ID}" \
    --region $AWS_REGION
echo "✅ Alarmas eliminadas"

# 2 — Dashboard
aws cloudwatch delete-dashboards \
    --dashboard-names "$DASHBOARD_NAME" \
    --region $AWS_REGION
echo "✅ Dashboard eliminado"

# 3 — Filtros de métricas
aws logs delete-metric-filter \
    --log-group-name "$LOG_GROUP" \
    --filter-name "PaymentErrorsFilter-${ALUMNO_ID}" \
    --region $AWS_REGION

aws logs delete-metric-filter \
    --log-group-name "$LOG_GROUP" \
    --filter-name "SlowResponseFilter-${ALUMNO_ID}" \
    --region $AWS_REGION
echo "✅ Filtros de métricas eliminados"

# 4 — API Gateway
aws apigatewayv2 delete-api \
    --api-id "$API_ID" \
    --region $AWS_REGION
echo "✅ API Gateway eliminado"

# 5 — Lambda
aws lambda delete-function \
    --function-name "$LAMBDA_NAME" \
    --region $AWS_REGION
echo "✅ Lambda eliminada"

# 6 — Log Group (Lambda lo crea automáticamente, lo eliminamos manual)
aws logs delete-log-group \
    --log-group-name "$LOG_GROUP" \
    --region $AWS_REGION
echo "✅ Log group eliminado"

# 7 — SNS Topic
aws sns delete-topic \
    --topic-arn "$SNS_ARN" \
    --region $AWS_REGION
echo "✅ SNS Topic eliminado"

# 8 — IAM Role (primero desadjuntar políticas)
aws iam detach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam detach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess

aws iam detach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchFullAccess

aws iam delete-role \
    --role-name "$ROLE_NAME"
echo "✅ IAM Role eliminado"

echo ""
echo "🎉 Limpieza completa. Todos los recursos de ${ALUMNO_ID} han sido eliminados."
```

---

## 11. Preguntas de reflexión

Responde estas preguntas en base a tu experiencia en el laboratorio:

1. **Lambda vs servidor:** En el lab anterior (Flask local), el log vivía en el proceso. En Lambda, ¿qué sucede con el log si el contenedor de ejecución es destruido entre invocaciones? ¿Qué resuelve CloudWatch Logs Nativo?

2. **Infraestructura efímera:** La diapositiva dice *"el contenedor donde ocurrió el error probablemente ya fue destruido"*. ¿Pudiste ver logs de invocaciones anteriores en CloudWatch Logs? ¿Qué garantiza eso?

3. **Método RED en Lambda:** Las métricas nativas de Lambda (`Invocations`, `Errors`, `Duration`) ya implementan RED sin código adicional. ¿Para qué sirven entonces las métricas custom (`PaymentErrors`, `RequestLatency`) que publicaste con boto3?

4. **USE en serverless:** Lambda no tiene CPU ni RAM "fija". ¿Qué miden `Throttles` y `ConcurrentExecutions` en términos de Saturación (S del método USE)?

5. **Alert Fatigue:** Si el umbral de la alarma `LambdaErrors` fuera 1 invocación con error (en vez de 3), ¿qué problema generaría durante el pico de tráfico del mediodía?

6. **Cardinalidad:** En las métricas custom usaste `AppName` como dimensión. ¿Qué pasaría si en cambio usaras `user_id` como dimensión con miles de usuarios distintos?

7. **Vendor lock-in:** La Lambda usa `aws-xray-sdk` directamente. Si mañana quisieras migrar a GCP Cloud Run, ¿qué tendrías que cambiar? ¿Cómo resolvería esto OpenTelemetry (OTel)?

---

## 📎 Referencia rápida de recursos creados

| Recurso | Nombre |
|---------|--------|
| IAM Role | `lambda-obs-role-alumno-XX` |
| Lambda Function | `payment-lambda-alumno-XX` |
| API Gateway (HTTP) | `payment-api-gw-alumno-XX` |
| Log Group | `/aws/lambda/payment-lambda-alumno-XX` |
| Metric Namespace | `LabObservabilidad/alumno-XX` |
| SNS Topic | `alertas-infra-alumno-XX` |
| Alarma 1 | `PaymentErrors-High-alumno-XX` |
| Alarma 2 | `HighLatency-alumno-XX` |
| Alarma 3 | `LambdaErrors-alumno-XX` |
| Alarma 4 | `LambdaThrottles-alumno-XX` |
| Dashboard | `salud-infra-alumno-XX` |

---

## 📚 Recursos adicionales

- [Lambda con X-Ray — documentación oficial AWS](https://docs.aws.amazon.com/lambda/latest/dg/services-xray.html)
- [CloudWatch Logs Insights — referencia de sintaxis](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [Métricas nativas de Lambda en CloudWatch](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics.html)
- [API Gateway HTTP APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html)
- [OpenTelemetry con AWS Distro (ADOT)](https://aws-otel.github.io/docs/introduction)
- [Método RED — Tom Wilkie (Grafana)](https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/)
- [SRE Book Google — SLIs/SLOs/SLAs](https://sre.google/sre-book/service-level-objectives/)

---

*Material elaborado por: **Aldo Trucios** — UTEC Posgrado, Módulo 8 Sesión 1*
