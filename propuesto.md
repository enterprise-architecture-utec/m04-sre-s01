# 🧪 Ejercicio Propuesto — Módulo 8, Sesión 1
## Observabilidad Serverless en AWS

| | |
|---|---|
| **Programa** | Arquitectura de Soluciones Multinube — UTEC Posgrado |
| **Docente** | Aldo Trucios |
| **Módulo** | 8 — Observabilidad y Optimización de Costos |
| **Sesión** | 1 — Fundamentos de Observabilidad |
| **Duración estimada** | 30 a 60 minutos |
| **Prerrequisito** | Laboratorio guiado completado (Lambda + API Gateway + CloudWatch funcionando) |

---

## 📖 Contexto

El equipo de negocio de **FinPago S.A.** reportó que los clientes con saldo insuficiente generan reintentos automáticos que están saturando el servicio de pagos. El área de operaciones necesita visibilidad específica sobre ese tipo de fallo para poder alertar antes de que impacte a otros usuarios.

Tu tarea es extender el sistema de observabilidad que construiste en el laboratorio guiado.

---

## 🎯 Entregables

### 1. Nuevo endpoint `/insufficient-funds`

Agrega un nuevo handler a tu función Lambda que simule el escenario de saldo insuficiente. El endpoint debe:

- Emitir un **log estructurado JSON** con los campos relevantes del evento de negocio.
- Publicar una **métrica custom** en tu namespace `LabObservabilidad/alumno-XX` en CloudWatch.
- Retornar un **código HTTP apropiado** para este tipo de error.

### 2. Alarma CloudWatch

Crea una alarma que notifique vía **SNS** cuando los errores de saldo insuficiente superen un umbral razonable en una ventana de tiempo definida por ti.

### 3. Consulta en Logs Insights

Escribe una consulta en **CloudWatch Logs Insights** que responda:

> *¿Qué usuarios están generando más errores de saldo insuficiente y cuántos intentos hicieron?*

---

## 💡 Indicaciones

- Puedes usar **IA generativa** para escribir el código, pero debes ser capaz de explicar cada decisión que tomaste.
- Apóyate en el código del laboratorio guiado como referencia de estructura y patrones.
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

Ejecuta el bloque de limpieza del laboratorio guiado para eliminar todos los recursos creados y evitar costos innecesarios en la cuenta AWS.

---

*Material elaborado por: **Aldo Trucios** — UTEC Posgrado, Módulo 8 Sesión 1*
