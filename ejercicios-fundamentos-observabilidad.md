# Ejercicios prácticos: Fundamentos de Observabilidad en AWS

**Nivel:** Inicial  
**Duración sugerida:** 30–40 minutos  
**Modalidad:** Individual o en grupos pequeños

## Objetivo

Practicar cómo usar las señales principales de observabilidad para responder preguntas sobre una aplicación:

- **Logs:** eventos detallados que ayudan a investigar qué ocurrió.
- **Métricas:** valores numéricos agregados en el tiempo que ayudan a detectar cuándo y cuánto ocurre.
- **Trazas:** recorrido de una solicitud entre componentes que ayuda a identificar dónde se consume el tiempo o dónde ocurre un fallo.

Estos ejercicios reutilizan la función Lambda creada en [guiado.md](guiado.md). Completa primero el despliegue de la Lambda del laboratorio principal.

## Prerrequisitos

Necesitas AWS CLI v2 instalado, credenciales configuradas y acceso a la región donde desplegaste el laboratorio. En tu terminal define los valores correspondientes a tu alumno:

    export ALUMNO_ID="alumno-XX"
    export AWS_REGION="us-east-1"
    export LAMBDA_NAME="payment-lambda-$ALUMNO_ID"
    export LOG_GROUP="/aws/lambda/$LAMBDA_NAME"

    aws --version
    aws sts get-caller-identity

Cambia alumno-XX y la región por los valores que usaste en guiado.md. No publiques ni compartas credenciales.

---

## Ejercicio 1 — ¿Qué está pasando con mi función Lambda?

**Conceptos:** logs y métricas.  
**Tiempo:** 15–20 minutos.

### Situación

La API de pagos parece responder, pero el equipo quiere saber si la función se ejecuta correctamente, cuántas solicitudes procesa y cuánto tarda.

### Paso 1. Genera tráfico

Invoca la API Gateway que creaste en el laboratorio principal. Sustituye la URL de ejemplo por la URL real de tu API y usa el método y el cuerpo válidos indicados en el laboratorio:

    curl -i "PEGA_AQUI_LA_URL_DE_TU_API"

Envía unas tres solicitudes válidas.

### Paso 2. Revisa los logs

Consulta los eventos recientes de Lambda:

    aws logs tail "$LOG_GROUP" --since 10m --region "$AWS_REGION"

Busca mensajes de ejecución, errores y detalles de duración. Si no aparece ningún log, revisa que el nombre de la función y la región sean correctos y que hayas invocado la Lambda.

### Paso 3. Consulta métricas

CloudWatch publica métricas de Lambda en el namespace AWS/Lambda. Para evitar diferencias entre macOS y Linux, genera las fechas con Python:

    START_TIME=$(python3 -c 'from datetime import datetime, timedelta, timezone; print((datetime.now(timezone.utc)-timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"))')
    END_TIME=$(python3 -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))')

Consulta las invocaciones:

    aws cloudwatch get-metric-statistics \
      --namespace AWS/Lambda \
      --metric-name Invocations \
      --dimensions Name=FunctionName,Value="$LAMBDA_NAME" \
      --start-time "$START_TIME" \
      --end-time "$END_TIME" \
      --period 60 \
      --statistics Sum \
      --region "$AWS_REGION"

Repite el comando cambiando Invocations por Errors y luego por Duration. Para Duration, usa --statistics Average; su unidad es milisegundos.

Las métricas pueden tardar unos minutos en aparecer. Si no ves datos, vuelve a invocar la función y amplía el intervalo de tiempo.

### Paso 4. Analiza los resultados

Responde:

1. ¿Cuántas invocaciones aparecen? ¿Coinciden aproximadamente con las solicitudes que enviaste?
2. ¿Qué información viste en los logs que no aparece en las métricas?
3. ¿Por qué la métrica Errors no siempre explica la causa de un error?
4. Si la duración promedio aumenta, ¿qué revisarías a continuación?

**Resultado esperado:** entender que las métricas permiten detectar y dimensionar una anomalía, mientras que los logs aportan detalles para investigar qué ocurrió.

---

## Ejercicio 2 — Detectar errores con una alarma

**Conceptos:** métricas, umbrales y alertas.  
**Tiempo:** 15–20 minutos.

### Situación

El equipo quiere detectar errores sin tener que revisar manualmente los logs de manera constante. Crearás una alarma de CloudWatch para la métrica Errors de tu Lambda.

### Paso 1. Crea la alarma

El comando configura una alarma que se activa si se registra al menos un error durante un período de un minuto:

    aws cloudwatch put-metric-alarm \
      --alarm-name "errores-$LAMBDA_NAME" \
      --alarm-description "Detecta errores en la Lambda del laboratorio" \
      --namespace AWS/Lambda \
      --metric-name Errors \
      --dimensions Name=FunctionName,Value="$LAMBDA_NAME" \
      --statistic Sum \
      --period 60 \
      --evaluation-periods 1 \
      --datapoints-to-alarm 1 \
      --threshold 1 \
      --comparison-operator GreaterThanOrEqualToThreshold \
      --treat-missing-data notBreaching \
      --region "$AWS_REGION"

Consulta el estado:

    aws cloudwatch describe-alarms \
      --alarm-names "errores-$LAMBDA_NAME" \
      --region "$AWS_REGION"

El estado inicial puede ser INSUFFICIENT_DATA mientras CloudWatch reúne y evalúa datos.

### Paso 2. Observa la alarma

1. En la consola de AWS, abre **CloudWatch → Alarms** y busca la alarma que creaste.
2. Invoca la API con una solicitud válida.
3. Si el código del laboratorio incluye una entrada de error controlado, ejecútala siguiendo las instrucciones del docente. No inventes rutas ni provoques fallos en otros sistemas.
4. Espera a que CloudWatch publique y evalúe las métricas, y vuelve a consultar el estado.

Si no tienes una manera segura de generar un error, no es necesario forzarlo: explica qué debería pasar si Errors alcanza el umbral configurado.

### Paso 3. Interpreta

Responde:

1. ¿Qué significan los estados OK y ALARM?
2. ¿Por qué una alarma es más útil que revisar logs manualmente todo el tiempo?
3. ¿Qué riesgo tiene configurar un umbral demasiado sensible?
4. ¿Qué métrica adicional te ayudaría a detectar degradación aunque no haya errores?

**Extensión opcional — trazas:** si AWS X-Ray está habilitado en el laboratorio, abre la consola de X-Ray y busca una solicitud reciente. Identifica los componentes del recorrido y compara el tiempo total con el tiempo de cada segmento. Las trazas muestran relaciones y latencias entre componentes que una métrica agregada o un log aislado no muestran por sí solos.

### Limpieza

Elimina la alarma al terminar:

    aws cloudwatch delete-alarms \
      --alarm-names "errores-$LAMBDA_NAME" \
      --region "$AWS_REGION"

---

## Cierre: ¿qué señal consultarías?

| Pregunta | Señal inicial |
|---|---|
| ¿Cuántas veces se invocó la función? | Métrica Invocations |
| ¿Qué mensaje de error registró una ejecución? | Logs de CloudWatch |
| ¿En qué parte del recorrido se concentra la latencia? | Trazas de AWS X-Ray, si están habilitadas |
| ¿Cuándo debe avisarse al equipo si aumentan los errores? | Alarma de CloudWatch sobre Errors |

**Idea clave:** la observabilidad no consiste solo en tener dashboards. Consiste en poder formular preguntas sobre un sistema y usar sus señales para responderlas, incluso ante situaciones que no anticipaste.
