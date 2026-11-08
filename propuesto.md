# 🧪 Ejercicio Propuesto — Módulo 8, Sesión 1
## Observabilidad Serverless en AWS

| | |
|---|---|
| **Programa** | Arquitectura de Soluciones Multinube — UTEC Posgrado |
| **Docente** | Aldo Trucios |
| **Módulo** | 8 — Observabilidad y Optimización de Costos |
| **Sesión** | 1 — Fundamentos de Observabilidad |
| **Duración estimada** | 30 a 60 minutos |
| **Prerrequisito** | Laboratorio guiado local completado; para los entregables AWS, extensión B desplegada con permisos y presupuesto autorizados |

---

## 📖 Contexto

El equipo de negocio de **FinPago S.A.** reportó que los clientes con saldo insuficiente generan reintentos automáticos que están saturando el servicio de pagos. El área de operaciones necesita visibilidad específica sobre ese tipo de fallo para poder alertar antes de que impacte a otros usuarios.

Tu tarea es extender el sistema de observabilidad que construiste en el laboratorio guiado. Trabajen en equipos de tres: todos deben comprender y validar el resultado completo. Los datos y usuarios deben ser sintéticos.

La ruta local se puede completar sin AWS: implementen y prueben el endpoint en `lab/app.py`, registren el evento y analicen sus datos en `data/requests.jsonl`. Una alarma SNS y una consulta Logs Insights **requieren AWS real**; si no tienen acceso, documenten la consulta y el diseño de alarma como propuestas, sin afirmar que se ejecutaron.

---

## 🎯 Entregables

### 1. Nuevo endpoint `/insufficient-funds`

Agrega una ruta que simule el escenario de saldo insuficiente. Para la extensión AWS, modifiquen el código `Code.ZipFile` en `aws/template.yaml` y vuelvan a desplegar el mismo stack con el comando de B2 del laboratorio guiado. La API usa una ruta `$default`, por lo que la función debe reconocer explícitamente el nuevo path. El endpoint debe:

- Emitir un **log estructurado JSON** con los campos relevantes del evento de negocio.
- En AWS, publicar una **métrica custom** en `LabObservabilidad/${TEAM_ID}` con dimensión `AppName` igual a `LAMBDA_NAME`. Localmente, analizar los eventos desde los logs; no es una métrica CloudWatch.
- Retornar un **código HTTP apropiado** para este tipo de error.

### 2. Alarma CloudWatch

En AWS, crea una alarma que notifique vía el topic **SNS** del stack cuando los errores de saldo insuficiente superen un umbral razonable en una ventana de tiempo definida por ti. En local, documenten el umbral y la acción propuesta sin simular que existe SNS.

### 3. Consulta en Logs Insights

Escribe una consulta en **CloudWatch Logs Insights** que responda (ejecútenla solo si tienen acceso AWS):

> *¿Qué usuarios están generando más errores de saldo insuficiente y cuántos intentos hicieron?*

---

## 💡 Indicaciones

- Puedes usar **IA generativa** para escribir el código, pero debes ser capaz de explicar cada decisión que tomaste.
- Apóyate en `lab/app.py` y `aws/template.yaml` como referencia de estructura y patrones. La implementación AWS de la plantilla no registra `user_id` por defecto: si lo agregan, usen identificadores sintéticos y eviten datos sensibles.
- Una alarma añadida fuera de CloudFormation no forma parte del stack y deben eliminarla explícitamente al final.
- No hay una única solución correcta. Se evalúa que los tres entregables funcionen de forma coherente.

---

## 🤔 Pregunta de reflexión

Una vez que tengas todo funcionando, responde brevemente:

> Si usaras `user_id` como dimensión de la métrica custom en lugar de `AppName`, ¿qué problema generaría eso con el tiempo y cómo lo resolverías?

---

## ✅ Criterios de evaluación

| Criterio | Descripción |
|---|---|
| **Funcionalidad** | El endpoint responde correctamente y el log JSON contiene campos de negocio relevantes |
| **Observabilidad** | La métrica custom se publica y la alarma tiene un umbral justificable |
| **Análisis** | La consulta de Logs Insights identifica correctamente los usuarios con más errores |
| **Comprensión** | El estudiante puede explicar las decisiones tomadas en el código |

---

## 📚 Recursos de apoyo

- [Documentación AWS Lambda — Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [CloudWatch Logs Insights — Sintaxis de consultas](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [CloudWatch Custom Metrics — boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudwatch/client/put_metric_data.html)
- [CloudWatch Alarms — AWS CLI](https://docs.aws.amazon.com/cli/latest/reference/cloudwatch/put-metric-alarm.html)
- [Método RED — Tom Wilkie (Grafana)](https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/)

---

## 🧹 Recuerda limpiar tus recursos al finalizar

Eliminen primero las alarmas u otros recursos creados manualmente para este reto, y luego ejecuten la sección B7 del laboratorio guiado para eliminar el stack y comprobar la limpieza. Detengan el Codespace cuando terminen.

---

*Material elaborado por: **Aldo Trucios** — UTEC Posgrado, Módulo 8 Sesión 1*
