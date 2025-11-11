## Diagrama de flujo del núcleo del simulador de celda H

El siguiente diagrama resume la arquitectura y el flujo de cálculo del paquete `simulador/` (sin considerar la GUI). Está orientado a perfiles técnicos familiarizados con procesos electroquímicos, de modo que puedan validar las hipótesis del modelo y detectar oportunidades de mejora.

```mermaid
flowchart TD
    Start([Inicio: Definir escenario experimental]):::start

    subgraph Arquitectura del simulador
        direction TB
        C1[constants.py\nConstantes físicas\n(F, R, e, kB...)]:::module
        C2[models.py\nEstructuras de datos:\nOperatingConditions,\nElectrodeKinetics,\nOhmicModel...]:::module
        C3[data.py\nValores de referencia y\ncatálogo de catalizadores]:::module
        C4[electrochemistry.py\nEcuaciones de Nernst,\nTafel, Ohm y concentración]:::module
        C5[detail.py\nTrazabilidad punto a punto\n(EquationStep, PointDetail)]:::module
        C6[orr.py\nEvaluación energética de\nintermedios O*, OH*, O2*]:::module
        C7[simulation.py\nInterfaces de alto nivel\nElectrolyzerSimulator,\nCatalystAnalyzer]:::module
        C1 --> C2 --> C3
        C2 --> C4
        C4 --> C5
        C3 --> C6
        C5 --> C7
        C6 --> C7
    end

    Start --> I1[Seleccionar condiciones de operación\n(temperatura en K, pH, presiones)]:::process
    I1 --> I2[Escoger parámetros eléctricos\n(p. ej. densidades de corriente a barrer,\nmaterial del catalizador, corrientes de referencia)]:::process
    I2 --> I3[Construir `ElectrolyzerConfig`\ncombina las estructuras de models.py\ncon los datos base de data.py]:::process

    I3 --> L1{¿Qué salida se necesita?}
    L1 -->|Curva de polarización| P1[Generar lista de corrientes\ny evaluar `detail.detailed_curve`]
    L1 -->|Actividad catalítica| P0[Usar `CatalystAnalyzer`\ny `orr.py` para perfilar ΔG(U)]

    P1 --> P1a[Para cada densidad de corriente:\n1. Calcular voltaje ideal (Nernst)\n2. Resolver Tafel ánodo/cátodo\n3. Obtener pérdidas óhmicas\n4. Evaluar sobrepotencial de concentración\n5. Sumar contribuciones]:::process
    P1a --> P1b[Registrar `EquationStep`\ncon ecuación, valores y resultado\n(PointDetail para cada punto)]:::process
    P1b --> P1c[Emitir tabla de resultados\n(V_total, V_ideal, η_act, η_ohm, η_conc)\ny detalle completo por punto]:::terminus

    P0 --> P0a[Consultas a `orr.py`:\n- Energías O*, OH*\n- Barreras disociativa y asociativa\n- Medida A ∝ exp(-ΔG*/kT)]:::process
    P0a --> P0b[Identificar paso limitante\ny curva volcán para el catalizador]:::terminus

    classDef start fill:#006d77,stroke:#004e57,color:#fff;
    classDef module fill:#f5f5f5,stroke:#a8a8a8,color:#333;
    classDef process fill:#ffffff,stroke:#006d77,color:#333;
    classDef terminus fill:#ffb703,stroke:#c17000,color:#222;
```

### Cómo leer el flujo

1. **Arquitectura**: la parte superior resume los módulos principales y cómo se alimentan entre sí. Las constantes y los modelos definen el marco matemático; `data.py` aporta valores de referencia; `electrochemistry.py` encapsula las ecuaciones; `detail.py` construye el desglose paso a paso; `orr.py` analiza los intermediarios de la ORR; `simulation.py` expone interfaces de uso sencillo.
2. **Escenario de simulación**: el químico fija condiciones de operación y corrientes de interés. Con esa información se construye un `ElectrolyzerConfig` que mezcla datos termodinámicos, cinéticos y resistivos.
3. **Curva de polarización**: `detail.detailed_curve` recorre cada corriente, aplica las ecuaciones (Nernst, Tafel, Ohm, transporte) y guarda el detalle de cada cálculo para auditoría científica.
4. **Actividad catalítica**: `orr.py` relaciona las energías de adsorción (obtenidas por DFT) con la barrera limitante y la actividad teórica, lo que permite comparar materiales sin repetir toda la simulación electroquímica.
5. **Salidas**: se generan tablas con los valores de voltaje y sobrepotenciales, y un registro de ecuaciones evaluadas; o bien, se entrega un perfil de actividad y la vía cinética dominante.

Este diagrama permite a un experto en electroquímica verificar dónde se introducen hipótesis (por ejemplo, leyes tipo Arrhenius para i₀ o κ, independencia del pH en ciertos términos, etc.) y proponer mejoras (nuevos modelos de transporte, parámetros experimentales actualizados o mecanismos adicionales en `orr.py`).
