using Duplo.Ai.DataManagement.AccessControl;
using Duplo.Ai.DataManagement.Controllers.User.Resource;
using Duplo.Ai.Model;
using Duplo.Ai.Model.Interfaces;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;

namespace Duplo.Extension.ClinicalAlerts;

/// <summary>
/// Workspace-scoped REST controller for alert triages: full CRUD plus <c>POST {id}/status</c> and
/// <c>POST {id}/results</c>, which the triage-patient skill calls. Live at
/// <c>.../environment/extensions/alerttriages</c> once the extension is hot-loaded.
/// </summary>
[ApiController]
[Route("v1/aiservicedesk/user/data/workspaces/{workspaceId}/environment/extensions/alerttriages")]
// Sits under the Workspace in the permission tree: workspace-scoped CRUD, no named actions.
[AccessControl(Parent = typeof(Workspace), ParentIdProperty = "OwnerWorkspaceId")]
public class AlertTriagesController : ResourcesController<AlertTriage, AlertTriageSpec, AlertTriageResult>
{
    public AlertTriagesController(IEntityService<AlertTriage> service, ILogger<AlertTriagesController> logger)
        : base(service, logger)
    {
    }
}
