# System Map

```mermaid
graph TD

    subgraph Interfaces ["Interfaces (Driver Adapters)"]
        AppContainerNode["AppContainer (src/container.py)"]
        RouterFastAPI["FastAPI App (build_api)"]
        IdempotencyDep["Idempotency Header Dependency"]
        ResumableSSE["Resumable SSE Endpoint (messages_router)"]
        CLIExport["CLI export-openapi"]
        WorkerProcess["Worker Process (src/worker.py)"]
        WorkerContainerNode["WorkerContainer (src/worker_container.py)"]
        TenantContextMiddlewareNode["TenantContextMiddleware"]
        TenantDependencyNode["TenantDependency (get_current_tenant_id_dep)"]
        TenantAdminRouterNode["TenantAdminRouter (/admin/tenants)"]
        KnowledgeRouterNode["KnowledgeRouter (/tenants/{tenant_id}/documents)"]
        KnowledgeSchemasNode["KnowledgeSchemas (DTOs)"]
        CitationsSSENode["Streaming Citations (SSE: citation)"]
        ApprovalsRouterNode["ApprovalsRouter (/tenants/{tenant_id}/approvals)"]
        ToolsSchemasNode["ToolsSchemas (DTOs)"]
        ToolSSENode["Streaming Tool Events (SSE: tool_approval_required, tool_call_started)"]
        WorkflowsRouterNode["WorkflowsRouter (/tenants/{tenant_id}/workflows)"]
        AgentsSchemasNode["AgentsSchemas (DTOs)"]
        WorkflowSSENode["Streaming Workflow Events (SSE: agent_handoff, subagent_completed, checkpoint_saved)"]
        OpenTelemetryMiddlewareNode["OpenTelemetryMiddleware (W3C trace context, X-Trace-ID, X-Span-ID)"]
        GovernanceRouterNode["GovernanceRouter (/admin/tenants/{tenant_id}/incidents, /admin/governance/metrics)"]
        GovernanceSchemasNode["GovernanceSchemas (IncidentResponse, GovernanceMetricsResponse)"]
        SafetyViolationHandlerNode["SafetyPolicyViolation Handler (HTTP 400 Bad Request)"]
        ConversationsRouterNode["ConversationsRouter (src/interfaces/http/routers/conversations_router.py)"]
        ProblemDetailsNode["ProblemDetails & RFC 7807 (src/interfaces/http/problem_details.py)"]
    end



    subgraph Application ["Application Layer (CQRS & Ports)"]
        CQRSProtocols["CommandHandler / QueryHandler (Protocols)"]
        AppExceptionsNode["ApplicationError (src/application/shared/exceptions)"]
        CreateConvCmd["CreateConversationCommand"]
        CreateConvHandler["CreateConversationCommandHandler"]
        SendMessageCmd["SendMessageCommand"]
        SendMessageHandler["SendMessageCommandHandler"]
        AppendAssistantCmd["AppendAssistantMessageCommand"]
        AppendAssistantHandler["AppendAssistantMessageCommandHandler"]
        StreamConvQuery["StreamConversationQuery"]
        StreamConvHandler["StreamConversationQueryHandler"]
        UOWPort["UnitOfWorkPort (Port)"]
        LLMClientPort["LlmClientPort"]
        EventPubPort["EventPublisherPort (Port)"]
        HTTPClientPort["HttpClientPort (Port)"]
        MsgBrokerPort["MessageBrokerPort (Port)"]
        EventConsumerPortNode["EventConsumerPort (Port)"]
        WorkerHandlerNode["LlmMessageProcessingWorker"]
        IdempotencyRepoPort["IdempotencyRepositoryPort (Port)"]
        StreamBufferRepoPort["StreamBufferRepositoryPort (Port)"]
        IdempotentExecutor["IdempotentCommandExecutor"]
        StreamRecoveryServiceNode["StreamRecoveryService"]
        ResumeStreamQueryNode["ResumeStreamQuery"]
        ResumeStreamHandlerNode["ResumeStreamQueryHandler"]
        TenantContextNode["TenantContext (src/application/shared/tenancy)"]
        ModelRouterServiceNode["ModelRouterService"]
        ProvisionTenantCmd["ProvisionTenantCommand"]
        ProvisionTenantHandler["ProvisionTenantCommandHandler"]
        ReserveQuotaCmd["ReserveQuotaCommand"]
        ReserveQuotaHandler["ReserveQuotaCommandHandler"]
        SettleQuotaCmd["SettleQuotaCommand"]
        SettleQuotaHandler["SettleQuotaCommandHandler"]
        UploadDocCmd["UploadDocumentCommand"]
        UploadDocHandler["UploadDocumentCommandHandler"]
        IndexChunksCmd["IndexDocumentChunksCommand"]
        IndexChunksHandler["IndexDocumentChunksCommandHandler"]
        HybridRetrieverServiceNode["HybridRetrieverService"]
        ToolPolicyEvaluatorServiceNode["ToolPolicyEvaluatorService"]
        ApproveToolExecutionCmd["ApproveToolExecutionCommand"]
        ApproveToolExecutionHandlerNode["ApproveToolExecutionCommandHandler"]
        RejectToolExecutionCmd["RejectToolExecutionCommand"]
        RejectToolExecutionHandlerNode["RejectToolExecutionCommandHandler"]
        ExecuteSandboxedToolCmd["ExecuteSandboxedToolCommand"]
        ExecuteSandboxedToolHandlerNode["ExecuteSandboxedToolCommandHandler"]
        StateReducerServiceNode["StateReducerService"]
        GraphExecutionEngineNode["GraphExecutionEngine"]
        SubAgentExecutorPortNode["SubAgentExecutorPort (Port)"]
        StartWorkflowCmd["StartWorkflowCommand"]
        StartWorkflowHandlerNode["StartWorkflowCommandHandler"]
        ResumeWorkflowCmd["ResumeWorkflowCommand"]
        ResumeWorkflowHandlerNode["ResumeWorkflowCommandHandler"]
        SafetyGuardrailPipelineServiceNode["SafetyGuardrailPipelineService"]
        GuardedCommandExecutorNode["GuardedCommandExecutor"]
        TraceContextCarrierNode["TraceContextCarrier"]
        RecordSecurityIncidentCmd["RecordSecurityIncidentCommand"]
        RecordSecurityIncidentHandlerNode["RecordSecurityIncidentCommandHandler"]
        ListIncidentsQueryNode["ListIncidentsQuery"]
        ListIncidentsQueryHandlerNode["ListIncidentsQueryHandler"]
        GetGovernanceMetricsQueryNode["GetGovernanceMetricsQuery"]
        GetGovernanceMetricsQueryHandlerNode["GetGovernanceMetricsQueryHandler"]
    end

    subgraph Domain ["Domain Layer (Core Business)"]
        ConvAggregate["Conversation (AggregateRoot)"]
        MessageVO["Message (ValueObject)"]
        ConvCreatedEvent["ConversationCreatedDomainEvent"]
        MsgAppendedEvent["MessageAppendedDomainEvent"]
        AssistantCompletedEvent["AssistantResponseCompletedDomainEvent"]
        ConvRepoPort["ConversationRepository (Port)"]
        ConvNotFoundErr["ConversationNotFoundError"]
        ConvExceptionsNode["ConversationExceptions (InvalidConversationTitleError, ConsecutiveUserMessageError)"]
        DomainError["DomainError (DomainException)"]
        DomainExceptionsNode["DomainExceptions (DomainValidationError, EntityNotFoundError, InvariantViolationError)"]
        EventEnvelopeVO["EventEnvelope (ValueObject)"]
        IdempotencyKeyVO["IdempotencyKey (ValueObject)"]
        StreamChunkVO["StreamChunk (ValueObject)"]
        AuditLogEntity["AuditLogRecord (Entity)"]
        AuditRepoPort["AuditRepository (Port)"]
        TenantIdVO["TenantId (ValueObject)"]
        MonetaryBudgetVO["MonetaryBudget (ValueObject)"]
        ModelRouteVO["ModelRoute (ValueObject)"]
        TenantAggregate["Tenant (AggregateRoot)"]
        TenantPolicyEntity["TenantPolicy (Entity)"]
        TenantExceptionsNode["TenantExceptions (TenantNotFoundError, InsufficientBudgetError, TenantSuspendedError, ModelNotAllowedError)"]
        TenantBudgetReservedEvent["TenantBudgetReservedDomainEvent"]
        TenantBudgetSettledEvent["TenantBudgetSettledDomainEvent"]
        TenantQuotaExceededEvent["TenantQuotaExceededDomainEvent"]
        TenantSuspendedEvent["TenantSuspendedDomainEvent"]
        FallbackActivatedEvent["ModelRouteFallbackActivatedDomainEvent"]
        TenantRepoPort["TenantRepositoryPort (Port)"]
        ModelCatalogPortNode["ModelCatalogPort (Port)"]
        EmbeddingVectorVO["EmbeddingVector (ValueObject)"]
        CitationVO["Citation (ValueObject)"]
        DocumentAggregate["Document (AggregateRoot)"]
        DocumentChunkEntity["DocumentChunk (Entity)"]
        DocumentUploadedEvent["DocumentUploadedDomainEvent"]
        DocumentIndexedEvent["DocumentIndexedDomainEvent"]
        DocumentFailedEvent["DocumentIndexingFailedDomainEvent"]
        KnowledgeRetrievedEvent["KnowledgeContextRetrievedDomainEvent"]
        KnowledgeRepoPortNode["KnowledgeRepositoryPort (Port)"]
        EmbeddingClientPortNode["EmbeddingClientPort (Port)"]
        DocumentNotFoundErr["DocumentNotFoundError"]
        ToolDefinitionVO["ToolDefinition (ValueObject)"]
        ToolCallVO["ToolCall (ValueObject)"]
        ToolResultVO["ToolResult (ValueObject)"]
        ToolApprovalRequestAggregate["ToolApprovalRequest (AggregateRoot)"]
        ToolCallRequestedEvent["ToolCallRequestedDomainEvent"]
        ToolApprovalRequiredEvent["ToolApprovalRequiredDomainEvent"]
        ToolExecutionCompletedEvent["ToolExecutionCompletedDomainEvent"]
        ToolApprovalResolvedEvent["ToolApprovalResolvedDomainEvent"]
        ToolRegistryPortNode["ToolRegistryPort (Port)"]
        ToolApprovalRepoPortNode["ToolApprovalRepositoryPort (Port)"]
        SandboxedToolRunnerPortNode["SandboxedToolRunnerPort (Port)"]
        ToolNotFoundErr["ToolNotFoundError"]
        ToolExecutionErr["ToolExecutionError"]
        InvalidApprovalStateErr["InvalidApprovalStateError"]
        AgentRoleVO["AgentRole (ValueObject)"]
        GraphEdgeVO["GraphEdge (ValueObject)"]
        StateSnapshotVO["StateSnapshot (ValueObject)"]
        WorkflowIdVO["WorkflowId (ValueObject)"]
        CheckpointIdVO["CheckpointId (ValueObject)"]
        WorkflowGraphEntity["WorkflowGraph (Entity)"]
        WorkflowInstanceAggregate["WorkflowInstance (AggregateRoot)"]
        WorkflowStartedEvent["WorkflowStartedDomainEvent"]
        SubAgentDelegatedEvent["SubAgentTaskDelegatedDomainEvent"]
        CheckpointSavedEvent["CheckpointSavedDomainEvent"]
        WorkflowApprovalReqEvent["WorkflowApprovalRequiredDomainEvent"]
        WorkflowCompletedEvent["WorkflowCompletedDomainEvent"]
        WorkflowCheckpointRepoPortNode["WorkflowCheckpointRepositoryPort (Port)"]
        AgentCatalogPortNode["AgentCatalogPort (Port)"]
        WorkflowNotFoundErr["WorkflowNotFoundError"]
        InvalidGraphTransitionErr["InvalidGraphTransitionError"]
        GraphCycleDetectedErr["GraphCycleDetectedError"]
        SafetyVerdictVO["SafetyVerdict (ValueObject)"]
        PiiEntityMatchVO["PiiEntityMatch (ValueObject)"]
        TraceContextVO["TraceContext (ValueObject)"]
        IncidentSeverityVO["IncidentSeverity (ValueObject)"]
        SecurityIncidentAggregate["SecurityIncident (AggregateRoot)"]
        SafetyViolationBlockedEvent["SafetyViolationBlockedDomainEvent"]
        PromptInjectionDetectedEvent["PromptInjectionDetectedDomainEvent"]
        PiiRedactionAppliedEvent["PiiRedactionAppliedDomainEvent"]
        SafetyGuardrailPortNode["SafetyGuardrailPort (Port)"]
        PiiScannerPortNode["PiiScannerPort (Port)"]
        IncidentRepoPortNode["IncidentRepositoryPort (Port)"]
        SafetyPolicyViolationErr["SafetyPolicyViolationError"]
        PiiMaskingErr["PiiMaskingError"]
        IncidentNotFoundErr["IncidentNotFoundError"]
    end

    subgraph Infrastructure ["Infrastructure (Driven Adapters & Mappers)"]
        InMemoryUOW["InMemoryUnitOfWorkAdapter"]
        InMemoryRepo["InMemoryConversationRepositoryAdapter"]
        InMemoryKnowledgeRepoNode["InMemoryKnowledgeRepositoryAdapter"]
        HttpxClient["HttpxHttpClientAdapter"]
        InMemoryOutbox["InMemoryOutboxRepositoryAdapter"]
        OutboxDispatcher["OutboxDispatcherAdapter"]
        FakeLlmClient["FakeLlmClientAdapter"]
        HttpxLlmClient["HttpxLlmClientAdapter"]
        MssqlModels["MSSQL Models (SQLModel)"]
        ConversationMapper["ConversationMapper (DataMapper)"]
        MssqlConnection["MSSQL Connection & SessionFactory"]
        MssqlRepo["MssqlConversationRepositoryAdapter"]
        MssqlOutbox["MssqlOutboxRepositoryAdapter"]
        MssqlUOW["MssqlUnitOfWorkAdapter"]
        InMemoryMsgBroker["InMemoryMessageBrokerAdapter"]
        RabbitMQConnManager["RabbitMQConnectionManager"]
        RabbitMQTopology["RabbitMQTopologyConfig"]
        RabbitMQPub["RabbitMQPublisherAdapter"]
        RabbitMQConsumer["RabbitMQConsumerAdapter"]
        OutboxRelay["OutboxRelayService"]
        InMemoryIdempotencyRepo["InMemoryIdempotencyRepositoryAdapter"]
        InMemoryAuditRepo["InMemoryAuditRepositoryAdapter"]
        MssqlIdempotencyRepo["MssqlIdempotencyRepositoryAdapter"]
        MssqlAuditRepo["MssqlAuditRepositoryAdapter"]
        MssqlStreamBufferRepo["MssqlStreamBufferRepositoryAdapter"]
        TenantDataMapperNode["TenantMapper (DataMapper)"]
        MssqlTenantRepoNode["MssqlTenantRepositoryAdapter"]
        InMemoryTenantRepoNode["InMemoryTenantRepositoryAdapter"]
        InMemoryModelCatalogNode["InMemoryModelCatalogAdapter"]
        KnowledgeDataMapperNode["KnowledgeMapper (DataMapper)"]
        MssqlKnowledgeRepoNode["MssqlKnowledgeRepositoryAdapter"]
        FakeEmbeddingClientNode["FakeEmbeddingClientAdapter"]
        HttpxEmbeddingClientNode["HttpxEmbeddingClientAdapter"]
        KnowledgeTopologyNode["KnowledgeTopologyConfig"]
        AnyioDocumentIndexerWorkerNode["AnyioDocumentIndexerWorker"]
        ToolApprovalDataMapperNode["ToolApprovalMapper (DataMapper)"]
        MssqlToolApprovalRepoNode["MssqlToolApprovalRepositoryAdapter"]
        InMemoryToolApprovalRepoNode["InMemoryToolApprovalRepositoryAdapter"]
        AnyioSandboxedToolRunnerNode["AnyioSandboxedToolRunnerAdapter"]
        ToolsTopologyNode["ToolsTopologyConfig"]
        AnyioToolExecutionWorkerNode["AnyioToolExecutionWorker"]
        WorkflowMapperNode["WorkflowMapper (DataMapper)"]
        MssqlWorkflowCheckpointRepoNode["MssqlWorkflowCheckpointRepositoryAdapter"]
        InMemoryWorkflowCheckpointRepoNode["InMemoryWorkflowCheckpointRepositoryAdapter"]
        MultiAgentTopologyNode["MultiAgentTopologyConfig"]
        AnyioSubagentWorkerNode["AnyioSubagentWorker"]
        GovernanceMapperNode["GovernanceMapper (DataMapper)"]
        MssqlIncidentRepoNode["MssqlIncidentRepositoryAdapter"]
        InMemoryIncidentRepoNode["InMemoryIncidentRepositoryAdapter"]
        RegexPiiScannerAdapterNode["RegexPiiScannerAdapter"]
        HeuristicInjectionDetectorAdapterNode["HeuristicInjectionDetectorAdapter"]
        AnyioStreamGuardrailFilterNode["AnyioStreamGuardrailFilterAdapter"]
        OpenTelemetryConfigNode["OpenTelemetryConfig (W3C Propagator)"]
        AppSettings["Settings (Pydantic Settings)"]
    end

    %% Interfaces to Application
    CLIExport --> RouterFastAPI
    AppContainerNode --> RouterFastAPI
    AppContainerNode --> UOWPort
    AppContainerNode --> IdempotencyRepoPort
    AppContainerNode --> AuditRepoPort
    AppContainerNode --> StreamBufferRepoPort
    AppContainerNode --> StreamRecoveryServiceNode
    AppContainerNode --> IdempotentExecutor
    RouterFastAPI --> ConversationsRouterNode
    RouterFastAPI --> ProblemDetailsNode
    ConversationsRouterNode --> CreateConvHandler
    ConversationsRouterNode --> SendMessageHandler
    ConversationsRouterNode --> StreamConvHandler
    ConversationsRouterNode --> IdempotencyDep
    ConversationsRouterNode --> ResumableSSE
    ConversationsRouterNode --> IdempotentExecutor
    ConversationsRouterNode --> StreamRecoveryServiceNode
    ResumableSSE --> StreamRecoveryServiceNode

    RouterFastAPI --> AppSettings
    RouterFastAPI --> TenantContextMiddlewareNode
    RouterFastAPI --> TenantAdminRouterNode
    TenantContextMiddlewareNode --> TenantContextNode
    TenantDependencyNode --> TenantContextNode
    TenantAdminRouterNode --> UOWPort
    TenantAdminRouterNode --> ProvisionTenantHandler
    TenantAdminRouterNode --> ReserveQuotaHandler

    %% Application orchestration
    CreateConvHandler --> CreateConvCmd
    CreateConvHandler --> ConvAggregate
    CreateConvHandler --> UOWPort

    SendMessageHandler --> SendMessageCmd
    SendMessageHandler --> ConvAggregate
    SendMessageHandler --> ConvNotFoundErr
    SendMessageHandler --> UOWPort

    AppendAssistantHandler --> AppendAssistantCmd
    AppendAssistantHandler --> ConvAggregate
    AppendAssistantHandler --> ConvNotFoundErr
    AppendAssistantHandler --> UOWPort

    StreamConvHandler --> StreamConvQuery
    StreamConvHandler --> ConvRepoPort
    StreamConvHandler --> ConvNotFoundErr
    StreamConvHandler --> LLMClientPort
    IdempotentExecutor --> IdempotencyRepoPort
    StreamRecoveryServiceNode --> StreamBufferRepoPort
    StreamRecoveryServiceNode --> StreamChunkVO
    ResumeStreamHandlerNode --> ResumeStreamQueryNode
    ResumeStreamHandlerNode --> StreamRecoveryServiceNode
    ApproveToolExecutionHandlerNode --> ApproveToolExecutionCmd
    ApproveToolExecutionHandlerNode --> ToolApprovalRequestAggregate
    ApproveToolExecutionHandlerNode --> ToolApprovalRepoPortNode
    RejectToolExecutionHandlerNode --> RejectToolExecutionCmd
    RejectToolExecutionHandlerNode --> ToolApprovalRequestAggregate
    RejectToolExecutionHandlerNode --> ToolApprovalRepoPortNode
    ExecuteSandboxedToolHandlerNode --> ExecuteSandboxedToolCmd
    ExecuteSandboxedToolHandlerNode --> SandboxedToolRunnerPortNode
    ExecuteSandboxedToolHandlerNode --> ToolRegistryPortNode
    ToolPolicyEvaluatorServiceNode --> ToolDefinitionVO
    ToolPolicyEvaluatorServiceNode --> TenantAggregate

    %% Domain Relationships
    ConvAggregate --> MessageVO
    ConvAggregate -.-> ConvCreatedEvent
    ConvAggregate -.-> MsgAppendedEvent
    ConvAggregate -.-> AssistantCompletedEvent
    ConvNotFoundErr -- Deriva de --> DomainError
    DocumentAggregate --> DocumentChunkEntity
    DocumentAggregate -.-> DocumentUploadedEvent
    DocumentAggregate -.-> DocumentIndexedEvent
    DocumentChunkEntity --> EmbeddingVectorVO
    ToolApprovalRequestAggregate --> ToolCallVO
    ToolApprovalRequestAggregate -.-> ToolApprovalRequiredEvent
    ToolApprovalRequestAggregate -.-> ToolApprovalResolvedEvent
    ToolNotFoundErr -- Deriva de --> DomainError
    ToolExecutionErr -- Deriva de --> DomainError
    InvalidApprovalStateErr -- Deriva de --> DomainError

    %% Application to Domain Ports
    UOWPort --> ConvRepoPort

    %% Infrastructure Implementations
    AppSettings --> MssqlConnection
    AppSettings --> MssqlUOW
    AppSettings --> InMemoryUOW
    InMemoryUOW -- Implementa --> UOWPort
    InMemoryRepo -- Implementa --> ConvRepoPort
    InMemoryUOW --> InMemoryRepo
    InMemoryUOW --> InMemoryOutbox
    MssqlUOW -- Implementa --> UOWPort
    MssqlRepo -- Implementa --> ConvRepoPort
    MssqlUOW --> MssqlRepo
    MssqlUOW --> MssqlOutbox
    MssqlUOW --> MssqlConnection
    MssqlRepo --> ConversationMapper
    MssqlRepo --> MssqlModels
    MssqlOutbox --> MssqlModels
    OutboxDispatcher --> InMemoryOutbox
    OutboxDispatcher --> EventPubPort
    FakeLlmClient -- Implementa --> LLMClientPort
    HttpxLlmClient -- Implementa --> LLMClientPort
    HttpxClient -- Implementa --> HTTPClientPort
    InMemoryMsgBroker -- Implementa --> MsgBrokerPort
    InMemoryMsgBroker -- Implementa --> EventConsumerPortNode
    RabbitMQPub -- Implementa --> MsgBrokerPort
    RabbitMQConsumer -- Implementa --> EventConsumerPortNode
    RabbitMQPub --> RabbitMQConnManager
    RabbitMQConsumer --> RabbitMQConnManager
    OutboxRelay --> MssqlOutbox
    OutboxRelay --> MsgBrokerPort
    OutboxRelay --> EventEnvelopeVO
    ConversationMapper --> MssqlModels
    ConversationMapper --> ConvAggregate
    MssqlRepo --> EventEnvelopeVO
    WorkerProcess --> WorkerContainerNode
    WorkerContainerNode --> WorkerHandlerNode
    WorkerContainerNode --> RabbitMQConsumer
    WorkerContainerNode --> RabbitMQTopology
    WorkerContainerNode --> MssqlUOW
    WorkerContainerNode --> MssqlStreamBufferRepo
    WorkerContainerNode --> MssqlAuditRepo
    WorkerContainerNode --> MssqlIdempotencyRepo
    WorkerHandlerNode --> AppendAssistantHandler
    WorkerHandlerNode --> LLMClientPort
    WorkerHandlerNode --> UOWPort
    WorkerHandlerNode --> StreamBufferRepoPort
    WorkerHandlerNode --> AuditRepoPort
    WorkerHandlerNode --> IdempotencyRepoPort
    WorkerHandlerNode --> TenantContextNode
    WorkerHandlerNode --> SettleQuotaHandler
    AppSettings --> RabbitMQConnManager
    InMemoryIdempotencyRepo -- Implementa --> IdempotencyRepoPort
    InMemoryAuditRepo -- Implementa --> AuditRepoPort
    MssqlIdempotencyRepo -- Implementa --> IdempotencyRepoPort
    MssqlAuditRepo -- Implementa --> AuditRepoPort
    MssqlStreamBufferRepo -- Implementa --> StreamBufferRepoPort
    MssqlUOW --> MssqlIdempotencyRepo
    MssqlUOW --> MssqlAuditRepo
    MssqlUOW --> MssqlStreamBufferRepo
    MssqlIdempotencyRepo --> MssqlModels
    MssqlAuditRepo --> MssqlModels
    MssqlStreamBufferRepo --> MssqlModels
    ReserveQuotaHandler --> UOWPort
    ReserveQuotaHandler --> TenantAggregate
    ReserveQuotaHandler --> TenantRepoPort
    SettleQuotaHandler --> UOWPort
    SettleQuotaHandler --> TenantAggregate
    SettleQuotaHandler --> TenantRepoPort
    ModelRouterServiceNode --> ModelCatalogPortNode
    ModelRouterServiceNode --> TenantAggregate
    MssqlTenantRepoNode -- Implementa --> TenantRepoPort
    InMemoryTenantRepoNode -- Implementa --> TenantRepoPort
    MssqlTenantRepoNode --> TenantDataMapperNode
    MssqlTenantRepoNode --> MssqlModels
    TenantDataMapperNode --> TenantAggregate
    TenantDataMapperNode --> MssqlModels
    MssqlUOW --> MssqlTenantRepoNode
    InMemoryUOW --> InMemoryTenantRepoNode
    AppContainerNode --> ModelCatalogPortNode
    AppContainerNode --> ModelRouterServiceNode
    AppContainerNode --> ReserveQuotaHandler
    AppContainerNode --> SettleQuotaHandler
    AppContainerNode --> HybridRetrieverServiceNode
    AppContainerNode --> EmbeddingClientPortNode
    AppContainerNode --> ToolApprovalRepoPortNode
    AppContainerNode --> SandboxedToolRunnerPortNode
    AppContainerNode --> ToolPolicyEvaluatorServiceNode
    WorkerContainerNode --> ModelCatalogPortNode
    WorkerContainerNode --> ModelRouterServiceNode
    WorkerContainerNode --> SettleQuotaHandler
    WorkerContainerNode --> HybridRetrieverServiceNode
    WorkerContainerNode --> EmbeddingClientPortNode
    WorkerContainerNode --> ToolApprovalRepoPortNode
    WorkerContainerNode --> SandboxedToolRunnerPortNode
    WorkerContainerNode --> ToolPolicyEvaluatorServiceNode
    InMemoryModelCatalogNode -- Implementa --> ModelCatalogPortNode
    UploadDocHandler --> UploadDocCmd
    UploadDocHandler --> UOWPort
    UploadDocHandler --> DocumentAggregate
    IndexChunksHandler --> IndexChunksCmd
    IndexChunksHandler --> UOWPort
    IndexChunksHandler --> EmbeddingClientPortNode
    IndexChunksHandler --> DocumentAggregate
    IndexChunksHandler --> DocumentChunkEntity
    HybridRetrieverServiceNode --> EmbeddingClientPortNode
    HybridRetrieverServiceNode --> KnowledgeRepoPortNode
    HybridRetrieverServiceNode --> CitationVO
    DocumentNotFoundErr -- Deriva de --> DomainError
    UOWPort --> KnowledgeRepoPortNode
    InMemoryKnowledgeRepoNode -- Implementa --> KnowledgeRepoPortNode
    InMemoryUOW --> InMemoryKnowledgeRepoNode
    MssqlKnowledgeRepoNode -- Implementa --> KnowledgeRepoPortNode
    MssqlUOW --> MssqlKnowledgeRepoNode
    MssqlKnowledgeRepoNode --> KnowledgeDataMapperNode
    MssqlKnowledgeRepoNode --> MssqlModels
    KnowledgeDataMapperNode --> DocumentAggregate
    KnowledgeDataMapperNode --> DocumentChunkEntity
    KnowledgeDataMapperNode --> MssqlModels
    FakeEmbeddingClientNode -- Implementa --> EmbeddingClientPortNode
    HttpxEmbeddingClientNode -- Implementa --> EmbeddingClientPortNode
    AnyioDocumentIndexerWorkerNode --> UOWPort
    AnyioDocumentIndexerWorkerNode --> EmbeddingClientPortNode
    AnyioDocumentIndexerWorkerNode --> DocumentAggregate
    AnyioDocumentIndexerWorkerNode --> DocumentChunkEntity
    AnyioDocumentIndexerWorkerNode --> KnowledgeTopologyNode
    KnowledgeTopologyNode -- Extiende --> RabbitMQTopology
    RouterFastAPI --> KnowledgeRouterNode
    KnowledgeRouterNode --> KnowledgeSchemasNode
    KnowledgeRouterNode --> UOWPort
    RouterFastAPI --> CitationsSSENode
    CitationsSSENode --> HybridRetrieverServiceNode
    WorkerHandlerNode --> HybridRetrieverServiceNode
    MssqlToolApprovalRepoNode -- Implementa --> ToolApprovalRepoPortNode
    InMemoryToolApprovalRepoNode -- Implementa --> ToolApprovalRepoPortNode
    AnyioSandboxedToolRunnerNode -- Implementa --> SandboxedToolRunnerPortNode
    MssqlToolApprovalRepoNode --> ToolApprovalDataMapperNode
    MssqlToolApprovalRepoNode --> MssqlModels
    ToolApprovalDataMapperNode --> ToolApprovalRequestAggregate
    ToolApprovalDataMapperNode --> MssqlModels
    MssqlUOW --> MssqlToolApprovalRepoNode
    InMemoryUOW --> InMemoryToolApprovalRepoNode
    UOWPort --> ToolApprovalRepoPortNode
    ToolsTopologyNode -- Extiende --> RabbitMQTopology
    AnyioToolExecutionWorkerNode --> SandboxedToolRunnerPortNode
    AnyioToolExecutionWorkerNode --> ToolRegistryPortNode
    AnyioToolExecutionWorkerNode --> EventPubPort
    AnyioToolExecutionWorkerNode --> ToolsTopologyNode
    RouterFastAPI --> ApprovalsRouterNode
    ApprovalsRouterNode --> ToolsSchemasNode
    ApprovalsRouterNode --> UOWPort
    ApprovalsRouterNode --> ApproveToolExecutionHandlerNode
    ApprovalsRouterNode --> RejectToolExecutionHandlerNode
    RouterFastAPI --> ToolSSENode
    ToolSSENode --> UOWPort
    RouterFastAPI --> WorkflowsRouterNode
    WorkflowsRouterNode --> AgentsSchemasNode
    WorkflowsRouterNode --> StartWorkflowHandlerNode
    WorkflowsRouterNode --> ResumeWorkflowHandlerNode
    WorkflowsRouterNode --> WorkflowCheckpointRepoPortNode
    RouterFastAPI --> WorkflowSSENode
    WorkflowInstanceAggregate -.-> WorkflowStartedEvent
    WorkflowInstanceAggregate -.-> SubAgentDelegatedEvent
    WorkflowInstanceAggregate -.-> CheckpointSavedEvent
    WorkflowInstanceAggregate -.-> WorkflowApprovalReqEvent
    WorkflowInstanceAggregate -.-> WorkflowCompletedEvent
    WorkflowInstanceAggregate --> StateSnapshotVO
    WorkflowGraphEntity --> GraphEdgeVO
    WorkflowGraphEntity --> AgentRoleVO
    StartWorkflowHandlerNode --> GraphExecutionEngineNode
    StartWorkflowHandlerNode --> WorkflowCheckpointRepoPortNode
    ResumeWorkflowHandlerNode --> GraphExecutionEngineNode
    ResumeWorkflowHandlerNode --> WorkflowCheckpointRepoPortNode
    GraphExecutionEngineNode --> StateReducerServiceNode
    GraphExecutionEngineNode --> SubAgentExecutorPortNode
    GraphExecutionEngineNode --> WorkflowGraphEntity
    GraphExecutionEngineNode --> WorkflowInstanceAggregate
    MssqlWorkflowCheckpointRepoNode -- Implementa --> WorkflowCheckpointRepoPortNode
    InMemoryWorkflowCheckpointRepoNode -- Implementa --> WorkflowCheckpointRepoPortNode
    MssqlWorkflowCheckpointRepoNode --> WorkflowMapperNode
    MssqlWorkflowCheckpointRepoNode --> MssqlModels
    WorkflowMapperNode --> WorkflowInstanceAggregate
    WorkflowMapperNode --> StateSnapshotVO
    WorkflowMapperNode --> MssqlModels
    MultiAgentTopologyNode -- Extiende --> RabbitMQTopology
    AnyioSubagentWorkerNode --> SubAgentExecutorPortNode
    AnyioSubagentWorkerNode --> EventPubPort
    AnyioSubagentWorkerNode --> MultiAgentTopologyNode
    SecurityIncidentAggregate -.-> SafetyViolationBlockedEvent
    SecurityIncidentAggregate -.-> PromptInjectionDetectedEvent
    SecurityIncidentAggregate --> IncidentSeverityVO
    SecurityIncidentAggregate --> TenantIdVO
    SafetyGuardrailPipelineServiceNode --> SafetyGuardrailPortNode
    SafetyGuardrailPipelineServiceNode --> PiiScannerPortNode
    GuardedCommandExecutorNode --> SafetyGuardrailPipelineServiceNode
    GuardedCommandExecutorNode --> IncidentRepoPortNode
    GuardedCommandExecutorNode -.-> SafetyPolicyViolationErr
    RecordSecurityIncidentHandlerNode --> IncidentRepoPortNode
    RecordSecurityIncidentHandlerNode --> EventPubPort
    RecordSecurityIncidentHandlerNode --> SecurityIncidentAggregate
    ListIncidentsQueryHandlerNode --> IncidentRepoPortNode
    GetGovernanceMetricsQueryHandlerNode --> IncidentRepoPortNode
    TraceContextCarrierNode --> TraceContextVO
    MssqlIncidentRepoNode -- Implementa --> IncidentRepoPortNode
    InMemoryIncidentRepoNode -- Implementa --> IncidentRepoPortNode
    MssqlIncidentRepoNode --> GovernanceMapperNode
    MssqlIncidentRepoNode --> MssqlModels
    GovernanceMapperNode --> SecurityIncidentAggregate
    GovernanceMapperNode --> MssqlModels
    RegexPiiScannerAdapterNode -- Implementa --> PiiScannerPortNode
    HeuristicInjectionDetectorAdapterNode -- Implementa --> SafetyGuardrailPortNode
    AnyioStreamGuardrailFilterNode --> SafetyGuardrailPortNode
    AnyioStreamGuardrailFilterNode -.-> SafetyPolicyViolationErr
    RabbitMQPub --> TraceContextCarrierNode
    RabbitMQConsumer --> TraceContextCarrierNode
    RouterFastAPI --> OpenTelemetryMiddlewareNode
    RouterFastAPI --> SafetyViolationHandlerNode
    SafetyViolationHandlerNode -.-> SafetyPolicyViolationErr
    RouterFastAPI --> GuardedCommandExecutorNode
    RouterFastAPI --> GovernanceRouterNode
    GovernanceRouterNode --> GovernanceSchemasNode
    GovernanceRouterNode --> ListIncidentsQueryHandlerNode
    GovernanceRouterNode --> GetGovernanceMetricsQueryHandlerNode
    AppContainerNode --> IncidentRepoPortNode
    AppContainerNode --> SafetyGuardrailPortNode
    AppContainerNode --> PiiScannerPortNode
    AppContainerNode --> SafetyGuardrailPipelineServiceNode
    AppContainerNode --> GuardedCommandExecutorNode
    WorkerContainerNode --> IncidentRepoPortNode
    WorkerContainerNode --> SafetyGuardrailPortNode
    WorkerContainerNode --> PiiScannerPortNode
    WorkerContainerNode --> SafetyGuardrailPipelineServiceNode
```

