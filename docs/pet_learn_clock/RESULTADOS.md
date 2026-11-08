# Resultado: terminación de learn por tiempo

Diagnóstico de desarrollo ejecutado el 2 de noviembre de 2026. Base: `2e663cde3f3b3b94295e18d92a26aab7d963c77e`.

**La hipótesis recibe apoyo en desarrollo. Ninguna condición reúne todos los requisitos de adopción. El producto sigue en v5.**

## Contraste principal fijado antes de simular

Con el cierre por conteo ausente en ambos brazos, ampliar el plazo de `learn` de dos a tres días debía reducir R1 al menos 0,5 puntos porcentuales y tener el extremo superior del IC95 % por debajo de cero. La salida por cambio natural y estancamiento permanece; los cierres temporales usan la memoria y saciedad originales de `done`.

Se utilizaron 20 semillas de nacimiento de desarrollo ya usadas: 3001–3010 y 6001–6010. Cuatro celdas de historia y seis continuaciones por nacimiento; la unidad estadística es el nacimiento, N=20. Intervención desde copias idénticas del día común 30, ventanas keep/read_change de 30 días.

| Condición | R1, puntos porcentuales [IC95 %] | Lectura keep | Lectura / control |
|---|---:|---:|---:|
| `count12` | -0.439 [-0.683, -0.155] | 5.06 % | 1.000 |
| `clock2` | -1.281 [-1.696, -0.895] | 6.18 % | 1.221 |
| `clock3` | -2.428 [-2.942, -1.903] | 8.28 % | 1.635 |
| `no_count` | -2.473 [-3.272, -1.739] | 9.76 % | 1.929 |

**Contraste clock3 − clock2: -1.147 pp; IC95 % [-1.638, -0.671].** Cumple el umbral; 16/20 contrastes por nacimiento son negativos.

La manipulación de duración también cumple el criterio en ambas ramas. La medida incluye la parte observada de los planes entrantes y de los todavía abiertos; no es una estimación sin censura de su vida completa. Diferencia clock3 − clock2:

- keep: +0.515 días; IC95 % [0.468, 0.560]; 20/20 diferencias positivas.
- read_change: +0.516 días; IC95 % [0.469, 0.564]; 20/20 diferencias positivas.

Interpretación: se identifica un efecto de ampliar el plazo permitido dentro de una política sin conteo. No se identifica un efecto mediado exclusivamente por la duración realizada ni se reparte la mejora histórica de la ronda 13 entre causas independientes. La fecha de saciedad, la exposición y otros estados pueden cambiar como consecuencias del plazo. No se hizo una prueba de equivalencia entre clock3 y no_count.

## Evaluación estándar y seguridad

Se ejecutó por separado el diseño original completo de la ronda 11 con las políticas activas desde nacimiento, sus controles de memoria congelada y la referencia original. Estos resultados no se mezclan con el contraste principal desde el día 30. Se reutilizaron sin cambios `CRITERIA` y `evaluate`.

El catálogo incluye todas las rutas, vidas emparejadas, plasticidad, estados equiparados y 60 casos de hogar seguro (5 condiciones × 6 semillas × 2 conjuntos de objetos). Se añadieron las vidas del diagnóstico a la unión de seguridad. Se deduplicó por trayectoria y se unieron las comprobaciones de fase.

| Condición | Criterios originales | Presupuesto ≤ 1,5× | Vidas completas seguras / únicas | Trayectorias con fallo por fase | Elegible |
|---|---|---|---:|---:|---|
| `count12` | No | Sí | 1675/1675 | 4 | No |
| `clock2` | No | Sí | 2543/2543 | 4 | No |
| `clock3` | Sí | No | 2633/2633 | 4 | No |
| `no_count` | No | No | 2650/2650 | 8 | No |

- `count12` reproduce el fallo previo de B2 en P3, R1 y R2.
- `clock2` falla el criterio original R2 de adaptación social.
- `clock3` pasa todos los criterios originales y mantiene cuatro trayectorias con fallo por fase, pero aumenta la lectura keep un 63,5 %, por encima del incremento máximo del 50 % fijado en este protocolo.
- `no_count` aumenta la lectura keep un 92,9 % y presenta ocho trayectorias con fallo por fase frente a cuatro en el control; falla H2 y el presupuesto. No hay fallos de vida completa. La seguridad del tramo diagnóstico por sí sola habría sido insuficiente para detectarlo.

No se han relajado umbrales ni ajustado parámetros después de observar los resultados. El límite de 1,5× es una decisión nueva de presupuesto de este protocolo; no se presenta como un estándar histórico del proyecto.

## Verificación e integridad

- 391 pruebas pasaron antes de simular; las 26 pruebas nuevas se volvieron a ejecutar sobre el código final antes del sello.
- Compatibilidad v1–v6: 95/95 casos idénticos.
- Los 320 archivos originales conservan sus SHA256. El protocolo, los dos módulos nuevos y sus pruebas conservan los hashes sellados antes de la primera trayectoria.
- Los R1 por semilla de count12 y no_count reproducen exactamente la ronda 13. Los efectos estándar de ref, none y count12 reproducen exactamente ref, none y B2 de la ronda 12.
- La instrumentación no modifica la huella de trayectoria ni el estado del generador aleatorio en ninguna vida diagnóstica. Crecimiento equiparado en todas las semillas.
- Comprobación aritmética adicional del contraste principal directamente desde los datos: coincide. Sin semillas perdidas ni sustituidas.
- Etapas guardadas: 20 diagnósticos, 200 combinaciones estándar, 100 combinaciones de catálogo y 60 hogares seguros.
- No se ejecutaron confirmatorios, replay de la publicación ni bloques reservados 7001–7060 o 7061+. Los bloques FINAL de 025/027/028/029 y sus locks permanecen intactos.

## Archivos para revisar

- `PROTOCOL.md`: hipótesis, diseño, criterio, límites e interpretación fijados antes de ejecutar.
- `run/STARTED.lock`: sello previo, hashes, semillas y entorno. No eliminar.
- `run/result.json`: resultado completo, criterios individuales, reproducción, seguridad y compatibilidad.
- `run/*_raw.json.gz`: registros de las cuatro etapas, sin sobrescribir resultados históricos.
- `run/verification.json`: verificaciones posteriores de recuentos, hashes y aritmética.
- `pet/learn_clock.py`: extensión experimental; `pet/diag_learn_clock.py`: lanzador sin modo final, sin semillas arbitrarias y sin sobrescritura.
- `tests/test_pet_learn_clock.py`: pruebas de mecanismo, conservación del resto de la actualización matinal, pureza y guardas.

El parche se aplicó y comprobó en un checkout limpio del commit base. No se publicó en GitHub: la conexión disponible tiene permiso de lectura, sin permiso de escritura.
