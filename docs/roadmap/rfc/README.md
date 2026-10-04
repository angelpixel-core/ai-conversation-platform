# Requests for Comments (RFCs) Técnicos

Este directorio centraliza las especificaciones técnicas profundas, análisis de impacto y planes de ejecución transversal que complementan el roadmap funcional del producto.

---

## Índice de RFCs

| RFC | Título | Ámbitos | ADRs Asociados | Estado | Documento |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **01** | **Estandarización de Infraestructura, Pipelines, Secretos y Especificación Cloud** | Docker Compose, Redes, Settings/Pydantic, CI/CD Actions, AWS Terraform | [ADR 0010](../../../.agent/architecture/decisions/0010-monorepo-compose-and-local-infrastructure-standardization.md) a [ADR 0013](../../../.agent/architecture/decisions/0013-cloud-infrastructure-requirements-and-provisioning-matrix.md) | ✅ Implementado | [rfc_infra_pipelines_and_provisioning_spec.md](rfc_infra_pipelines_and_provisioning_spec.md) |
| **02** | **Refactor y Estandarización de Código Fuente: Clean Architecture, DDD, Tipado Estricto y Convenciones** | Dominio, Value Objects, CQRS Handlers, Driven Ports, Mappers Bidireccionales, Problem Details RFC 7807, Tipado Python 3.12+ | [ADR 0014](../../../.agent/architecture/decisions/0014-domain-layer-standardization-and-clean-arch-polish.md) a [ADR 0018](../../../.agent/architecture/decisions/0018-strict-typing-and-google-docstrings.md) | ✅ Implementado | [rfc_source_code_refactors_and_clean_arch_polish.md](rfc_source_code_refactors_and_clean_arch_polish.md) |

---

## Ciclo de Vida de un RFC

1. **Draft / Propuesto:** Redacción de problemática, alternativas consideradas y contratos arquitectónicos.
2. **Review:** Discusión técnica, pruebas de concepto y validación de invariantes de Clean Architecture.
3. **Aceptado / En Ejecución:** Se desglosan ADRs formales en `.agent/architecture/decisions/` y se ejecuta mediante commits convencionales guiados por el execution loop.
4. **Implementado:** Validación completa en el Quality Gate (`make check-all`) y fusión a la rama `development`.
