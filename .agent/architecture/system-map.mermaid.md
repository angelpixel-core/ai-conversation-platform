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
    end

    subgraph Application ["Application Layer (CQRS & Ports)"]
        CreateConvCmd["CreateConversationCommand"]
        CreateConvHandler["CreateConversationHandler"]
        SendMessageCmd["SendMessageCommand"]
        SendMessageHandler["SendMessageHandler"]
        AppendAssistantCmd["AppendAssistantMessageCommand"]
        AppendAssistantHandler["AppendAssistantMessageHandler"]
        StreamConvQuery["StreamConversationQuery"]
        StreamConvHandler["StreamConversationQueryHandler"]
        UOWPort["UnitOfWork Port"]
        LLMClientPort["LlmClientPort"]
        EventPubPort["EventPublisherPort"]
        HTTPClientPort["HttpClientPort"]
        MsgBrokerPort["MessageBrokerPort (Port)"]
        EventConsumerPortNode["EventConsumerPort (Port)"]
        WorkerHandlerNode["LlmMessageProcessingWorker"]
        IdempotencyRepoPort["IdempotencyRepository (Port)"]
        StreamBufferRepoPort["StreamBufferRepository (Port)"]
        IdempotentExecutor["IdempotentCommandExecutor"]
        StreamRecoveryServiceNode["StreamRecoveryService"]
        ResumeStreamQueryNode["ResumeStreamQuery"]
        ResumeStreamHandlerNode["ResumeStreamQueryHandler"]
        TenantContextNode["TenantContext (src/application/shared/tenancy)"]
        ModelRouterServiceNode["ModelRouterService"]
        ReserveQuotaCmd["ReserveQuotaCommand"]
        ReserveQuotaHandler["ReserveQuotaCommandHandler"]
        SettleQuotaCmd["SettleQuotaCommand"]
        SettleQuotaHandler["SettleQuotaCommandHandler"]
        UploadDocCmd["UploadDocumentCommand"]
        UploadDocHandler["UploadDocumentHandler"]
        IndexChunksCmd["IndexDocumentChunksCommand"]
        IndexChunksHandler["IndexDocumentChunksHandler"]
        HybridRetrieverServiceNode["HybridRetrieverService"]
        ToolPolicyEvaluatorServiceNode["ToolPolicyEvaluatorService"]
        ApproveToolExecutionCmd["ApproveToolExecutionCommand"]
        ApproveToolExecutionHandlerNode["ApproveToolExecutionHandler"]
        RejectToolExecutionCmd["RejectToolExecutionCommand"]
        RejectToolExecutionHandlerNode["RejectToolExecutionHandler"]
        ExecuteSandboxedToolCmd["ExecuteSandboxedToolCommand"]
        ExecuteSandboxedToolHandlerNode["ExecuteSandboxedToolHandler"]
        StateReducerServiceNode["StateReducerService"]
        GraphExecutionEngineNode["GraphExecutionEngine"]
        SubAgentExecutorPortNode["SubAgentExecutorPort (Port)"]
        StartWorkflowCmd["StartWorkflowCommand"]
        StartWorkflowHandlerNode["StartWorkflowCommandHandler"]
        ResumeWorkflowCmd["ResumeWorkflowCommand"]
        ResumeWorkflowHandlerNode["ResumeWorkflowCommandHandler"]
    end

    subgraph Domain ["Domain Layer (Core Business)"]
        ConvAggregate["Conversation (AggregateRoot)"]
        MessageVO["Message (ValueObject)"]
        ConvCreatedEvent["ConversationCreatedDomainEvent"]
        MsgAppendedEvent["MessageAppendedDomainEvent"]
        AssistantCompletedEvent["AssistantResponseCompletedDomainEvent"]
        ConvRepoPort["ConversationRepository (Port)"]
        ConvNotFoundErr["ConversationNotFoundError"]
        DomainError["DomainError"]
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
    end

    subgraph Infrastructure ["Infrastructure (Driven Adapters)"]
        InMemoryUOW["InMemoryUnitOfWork"]
        InMemoryRepo["InMemoryConversationRepository"]
        InMemoryKnowledgeRepoNode["InMemoryKnowledgeRepositoryAdapter"]
        HttpxClient["HttpxClientAdapter"]
        InMemoryOutbox["InMemoryOutboxRepository"]
        OutboxDispatcher["OutboxDispatcher"]
        FakeLlmClient["FakeLlmClientAdapter"]
        HttpxLlmClient["HttpxLlmClientAdapter"]
        MssqlModels["MSSQL Models (SQLModel)"]
        ConversationMapper["ConversationDataMapper"]
        MssqlConnection["MSSQL Connection & SessionFactory"]
        MssqlRepo["MssqlConversationRepository"]
        MssqlOutbox["MssqlOutboxRepository"]
        MssqlUOW["MssqlUnitOfWork"]
        InMemoryMsgBroker["InMemoryMessageBroker"]
        RabbitMQConnManager["RabbitMQConnectionManager"]
        RabbitMQTopology["RabbitMQTopologyConfig"]
        RabbitMQPub["RabbitMQPublisherAdapter"]
        RabbitMQConsumer["RabbitMQConsumerAdapter"]
        OutboxRelay["OutboxRelayService"]
        InMemoryIdempotencyRepo["InMemoryIdempotencyRepositoryAdapter"]
        InMemoryAuditRepo["InMemoryAuditRepositoryAdapter"]
        MssqlIdempotencyRepo["MssqlIdempotencyRepository"]
        MssqlAuditRepo["MssqlAuditRepository"]
        MssqlStreamBufferRepo["MssqlStreamBufferRepository"]
        TenantDataMapperNode["TenantDataMapper"]
        MssqlTenantRepoNode["MssqlTenantRepository"]
        InMemoryTenantRepoNode["InMemoryTenantRepositoryAdapter"]
        InMemoryModelCatalogNode["InMemoryModelCatalogAdapter"]
        KnowledgeDataMapperNode["KnowledgeDataMapper"]
        MssqlKnowledgeRepoNode["MssqlKnowledgeRepository"]
        FakeEmbeddingClientNode["FakeEmbeddingClientAdapter"]
        HttpxEmbeddingClientNode["HttpxEmbeddingClientAdapter"]
        KnowledgeTopologyNode["KnowledgeTopologyConfig"]
        AnyioDocumentIndexerWorkerNode["AnyioDocumentIndexerWorker"]
        ToolApprovalDataMapperNode["ToolApprovalMapper"]
        MssqlToolApprovalRepoNode["MssqlToolApprovalRepository"]
        InMemoryToolApprovalRepoNode["InMemoryToolApprovalRepositoryAdapter"]
        AnyioSandboxedToolRunnerNode["AnyioSandboxedToolRunner"]
        ToolsTopologyNode["ToolsTopologyConfig"]
        AnyioToolExecutionWorkerNode["AnyioToolExecutionWorker"]
        WorkflowMapperNode["WorkflowMapper"]
        MssqlWorkflowCheckpointRepoNode["MssqlWorkflowCheckpointRepository"]
        InMemoryWorkflowCheckpointRepoNode["InMemoryWorkflowCheckpointRepositoryAdapter"]
        MultiAgentTopologyNode["MultiAgentTopologyConfig"]
        AnyioSubagentWorkerNode["AnyioSubagentWorker"]
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
    RouterFastAPI --> CreateConvHandler
    RouterFastAPI --> SendMessageHandler
    RouterFastAPI --> StreamConvHandler
    RouterFastAPI --> IdempotencyDep
    RouterFastAPI --> ResumableSSE
    RouterFastAPI --> IdempotentExecutor
    RouterFastAPI --> StreamRecoveryServiceNode
    ResumableSSE --> StreamRecoveryServiceNode
    RouterFastAPI --> AppSettings
    RouterFastAPI --> TenantContextMiddlewareNode
    RouterFastAPI --> TenantAdminRouterNode
    TenantContextMiddlewareNode --> TenantContextNode
    TenantDependencyNode --> TenantContextNode
    TenantAdminRouterNode --> UOWPort
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
```
