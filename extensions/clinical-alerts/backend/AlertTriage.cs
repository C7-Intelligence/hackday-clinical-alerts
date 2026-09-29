using Duplo.Ai.DataManagement.Interfaces;
using Duplo.Ai.DataManagement.Services;
using Duplo.Ai.Model.Attributes;
using Duplo.Ai.Model.Interfaces;
using Duplo.Ai.Model.Resource;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using MongoDB.Bson.Serialization.Attributes;

namespace Duplo.Extension.ClinicalAlerts;

// An AlertTriage is one run of the clinical alert rules for one synthetic member. The triage-patient skill
// runs the deterministic engine, writes the graph, has the LLM explain, and posts the TriageResult back.
// Spec and Result mirror team-plan/CONTRACT.md §2 and §3; change them there first.

/// <summary>User-supplied inputs (CONTRACT §2).</summary>
[BsonIgnoreExtraElements]
public class AlertTriageSpec : BaseSpec
{
    /// <summary>Synthetic member id, SYN-001…SYN-007.</summary>
    public string? PatientId { get; set; }

    /// <summary>When false the skill passes --no-informational to the engine.</summary>
    public bool IncludeInformational { get; set; } = true;

    /// <summary>When true the agent fills each alert's rationale and the patient summary.</summary>
    public bool Explain { get; set; } = true;
}

/// <summary>The TriageResult the skill posts back (CONTRACT §3).</summary>
[BsonIgnoreExtraElements]
public class AlertTriageResult : BaseResult
{
    public string? PatientId { get; set; }
    public string? PatientName { get; set; }
    public int? Age { get; set; }
    public string? Sex { get; set; }
    public string? MemberSince { get; set; }
    public string? AsOf { get; set; }
    public string? EngineVersion { get; set; }
    public bool Synthetic { get; set; } = true;
    public TriageCounts? Counts { get; set; }
    public List<TriageAlert> Alerts { get; set; } = new();
    public string? Summary { get; set; }

    /// <summary>Extension-side extra: "written" or "skipped" for the Neo4j step. Not produced by the engine.</summary>
    public string? GraphStatus { get; set; }
}

[BsonIgnoreExtraElements]
public class TriageCounts
{
    public int Clinical { get; set; }
    public int Nudge { get; set; }
    public int Informational { get; set; }
}

[BsonIgnoreExtraElements]
public class TriageAlert
{
    public string? Id { get; set; }
    public string? RuleId { get; set; }

    /// <summary>clinical | nudge | informational</summary>
    public string? Tier { get; set; }

    /// <summary>1 clinical, 2 nudge, 3 informational.</summary>
    public int Priority { get; set; }

    public string? Title { get; set; }
    public string? Detail { get; set; }
    public string? RecommendedAction { get; set; }
    public List<TriageEvidence> Evidence { get; set; } = new();
    public string? Rationale { get; set; }
}

[BsonIgnoreExtraElements]
public class TriageEvidence
{
    /// <summary>lab | vital | medication | condition | immunization | screening | appointment | demographic</summary>
    public string? Kind { get; set; }
    public string? Code { get; set; }
    public string? Display { get; set; }

    /// <summary>Numeric by contract; omitted for non-measurement evidence (medications, appointments).</summary>
    public double? Value { get; set; }

    public string? Unit { get; set; }
    public string? Date { get; set; }
}

/// <summary>The entity: its own Mongo collection. Origin type/sub-type select the triage-patient skill.</summary>
[BsonCollection("extension_alerttriage")]
[BsonIgnoreExtraElements]
public class AlertTriage : ResourceBase<AlertTriageSpec, AlertTriageResult>
{
    public override string GetTicketOriginType() => "AlertTriage";
    public override string GetTicketOriginSubType() => "alert-triage";
}

/// <summary>No-op hooks (framework default base). See reference/04-hooks.md.</summary>
public class AlertTriageHooks : DefaultEntityHooks<AlertTriage>
{
}

/// <summary>Standard CRUD + the agent provisioning lifecycle, all from the base.</summary>
public class AlertTriageService : ResourceServiceBase<AlertTriage, AlertTriageSpec, AlertTriageResult>
{
    public AlertTriageService(
        IRepository<AlertTriage> repository,
        ILogger<AlertTriageService> logger,
        IServiceScopeFactory scopeFactory,
        IHttpContextAccessor httpContextAccessor)
        : base(repository, logger, scopeFactory, httpContextAccessor)
    {
    }
}
