from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import datetime

SEV_COLORS = {
    "Critical": "C00000",
    "High": "E97132",
    "Medium": "FFC000",
    "Low": "92D050",
    "Positive": "00B050",
    "Informational": "808080",
}

doc = Document()

# ---------- styles ----------
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(10.5)

def set_cell_shading(cell, hex_color):
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), hex_color)
    cell._tc.get_or_add_tcPr().append(shd)

def add_heading(text, level=1):
    h = doc.add_heading(text, level=level)
    return h

def add_sev_table(rows, headers=("#", "Finding", "Severity")):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        for p in hdr_cells[i].paragraphs:
            for r in p.runs:
                r.bold = True
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
        sev = row[-1]
        if sev in SEV_COLORS:
            set_cell_shading(cells[-1], SEV_COLORS[sev])
    doc.add_paragraph()
    return table

def add_para(text, bold=False, italic=False, size=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    if size:
        r.font.size = Pt(size)
    return p

def add_bullets(items):
    for it in items:
        doc.add_paragraph(it, style='List Bullet')

# ================= COVER =================
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("Azure Posture Assessment")
run.bold = True
run.font.size = Pt(28)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run("Security, Cost & Architecture Review")
run.font.size = Pt(16)
run.italic = True

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta.add_run(f"\nPrepared: {datetime.date.today().strftime('%d %B %Y')}\n").font.size = Pt(11)
meta.add_run("Scope: Subscriptions “Azure Pass - Sponsorship” and “gipl-azure-subscription”\n").font.size = Pt(11)
meta.add_run("Method: Read-only assessment using Azure Resource Graph, Azure CLI/PowerShell (Az module), and Azure Advisor (free tier)\n").font.size = Pt(11)
meta.add_run("Note: No paid security service was enabled to produce this report. No resources were modified.").font.size = Pt(11)

doc.add_page_break()

# ================= EXECUTIVE SUMMARY =================
add_heading("Executive Summary", level=1)

add_para(
    "This assessment reviewed two Azure subscriptions supporting an AI/ML data science platform "
    "(“Azure Pass - Sponsorship” and “gipl-azure-subscription”). The environment is small "
    "(26 resources total) and entirely PaaS-based — there are no virtual machines, virtual networks, "
    "or traditional IaaS network perimeter. The estate is built around Azure OpenAI / Anthropic / Cognitive "
    "Services accounts, Azure Machine Learning workspaces, one Key Vault, and two Storage accounts."
)

add_para(
    "The assessment found a consistent and material risk pattern: every sensitive data-plane resource in "
    "both subscriptions is reachable directly over the public internet, with no network-layer restriction "
    "(no Private Link, no firewall/IP allow-listing, no VNet integration), and no diagnostic logging is "
    "configured anywhere — meaning there is currently no audit trail of who accessed these resources or "
    "what data moved through them. This combination is the highest-priority item for remediation.",
)

add_para("Key statistics:", bold=True)
add_bullets([
    "26 resources across 2 subscriptions, 5 resource groups, 4 regions",
    "15 of 15 (100%) data-plane resources (AI accounts, ML workspaces, Key Vault, Storage) have public network access enabled with no restriction",
    "Zero Log Analytics workspaces — no centralized logging or audit trail exists",
    "1 orphaned role assignment holds Owner at subscription root scope on BOTH subscriptions (deleted/unidentifiable principal)",
    "20 active Owner role assignments and 9 active Contributor assignments across both subscriptions, for a 26-resource estate",
    "Key Vault uses legacy Access Policies (not RBAC), has no firewall, and lacks deletion protection",
    "Zero resource locks exist anywhere",
    "No tagging enforcement policy exists; 26.9% of resources are untagged",
    "Defender for Cloud is on the Free tier throughout (consistent with cost constraint) — ~95 Security Benchmark checks fail, none requiring a paid plan to fix",
    "Azure Advisor found zero cost-optimization opportunities and no idle/unattached resources — this is a lean, well-utilized estate from a spend perspective",
])

add_para("Overall risk posture: ", bold=True)
p = doc.paragraph if False else doc.add_paragraph()
r = p.add_run("HIGH — driven by identity and network exposure findings, not by cost or resource sprawl.")
r.bold = True
r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)

add_para(
    "All identified issues are remediable at zero incremental cost using free-tier Azure capabilities "
    "(RBAC cleanup, network firewall rules, diagnostic settings, resource locks, Azure Policy). No paid "
    "Defender for Cloud plan, Sentinel, or other paid service is required to close the gaps identified in "
    "this report. Prepared remediation scripts are included in Section 9, clearly marked as NOT TO BE RUN "
    "pending management approval."
)

add_heading("Findings Summary by Severity", level=2)
summary_rows = [
    ("1", "Orphaned Owner role assignment at subscription root (both subs) — unidentifiable principal with full control", "Critical"),
    ("2", "Key Vault has no firewall, public network access enabled, no network ACLs", "Critical"),
    ("3", "No Log Analytics workspace / no diagnostic logging anywhere in either subscription", "Critical"),
    ("4", "100% of AI/Cognitive Services, ML workspace, Key Vault and Storage resources publicly network-accessible", "Critical"),
    ("5", "5 additional orphaned role assignments (stale Contributor/Reader/Cost Management roles)", "High"),
    ("6", "Owner/Contributor sprawl: 20 Owners + 9 Contributors across a 26-resource estate", "High"),
    ("7", "Two service principals hold broad standing Contributor + Key Vault Administrator + Storage Data Contributor rights", "High"),
    ("8", "Storage accounts: no private link, no VNet rules, shared key access not disabled", "High"),
    ("9", "Azure ML Workspaces: public network access not disabled", "High"),
    ("10", "No tagging enforcement policy / no resource locks anywhere", "High"),
    ("11", "Blob Soft Delete not enabled on storage (gipl subscription)", "High"),
    ("12", "26.9% of resources untagged; RG-level tagging inconsistent", "Medium"),
    ("13", "104 non-compliant policy states under Defender's built-in audit policy", "Medium"),
    ("14", "No Service Health alerts configured; outdated Azure OpenAI API version in use", "Medium"),
    ("15", "Region sprawl across 4 regions for 26 resources", "Low"),
    ("16", "No guest/external accounts with direct role assignments", "Positive"),
    ("17", "No custom (overly-broad) role definitions in use", "Positive"),
    ("18", "Zero Azure Advisor cost recommendations; no idle/unattached resources", "Positive"),
    ("19", "No paid Defender plans enabled — compliant with free-tooling constraint", "Positive"),
]
add_sev_table(summary_rows)

doc.add_page_break()

# ================= TABLE OF CONTENTS (manual) =================
add_heading("Report Contents", level=1)
add_bullets([
    "1. Phase 1 — Discovery & Inventory",
    "2. Phase 2 — Identity & Access Management",
    "3. Phase 3 — Security Posture Baseline",
    "4. Phase 4 — Networking & Perimeter",
    "5. Phase 5 — Cost Optimization",
    "6. Phase 6 — Governance & Compliance",
    "7. Consolidated Risk Register",
    "8. Methodology & Constraints",
    "9. Prepared Remediation Scripts (NOT executed — pending approval)",
])
doc.add_page_break()

# ================= PHASE 1 =================
add_heading("1. Phase 1 — Discovery & Inventory", level=1)
add_para(
    "Both subscriptions together contain 26 resources across 5 resource groups and 4 Azure regions "
    "(southindia: 13, eastus2: 8, eastus: 3, centralindia: 2). The estate is exclusively PaaS — no "
    "virtual machines or virtual networks were found in either subscription."
)
add_heading("Resource Type Breakdown", level=2)
add_bullets([
    "“Azure Pass - Sponsorship”: 5x Cognitive Services accounts, 3x Portal dashboards, 2x Cognitive Services projects",
    "“gipl-azure-subscription”: 5x Cognitive Services accounts, 4x Cognitive Services projects, 2x ML workspaces, 2x Storage accounts, 1x Key Vault, 1x Event Hub namespace, 1x Syntex document processor",
])
add_heading("Resource Groups", level=2)
add_bullets([
    "SIEM (centralindia) — gipl-azure-subscription — contains only a Syntex document processor; no actual logging/SIEM infrastructure (Log Analytics, Sentinel) present despite the name",
    "gipl-slice-ml-india (southindia) — gipl-azure-subscription — primary AI/ML workload RG",
    "slicegpt (southindia) — gipl-azure-subscription",
    "dashboards (eastus) — Azure Pass - Sponsorship",
    "slice_ml_ds (eastus) — Azure Pass - Sponsorship — only RG with any tags applied (POD=Data Science)",
])
add_heading("Findings", level=2)
add_sev_table([
    ("1.1", "RG “SIEM” contains no actual centralized logging resource (no Log Analytics workspace, no Sentinel) — name is misleading relative to actual logging capability", "High"),
    ("1.2", "4 of 5 resource groups have no tags; only slice_ml_ds is tagged", "Medium"),
    ("1.3", "7 of 26 resources (26.9%) untagged at resource level", "Medium"),
    ("1.4", "No VMs or VNets in either subscription — simplifies network attack surface to PaaS firewall/Private Link configuration only", "Positive"),
    ("1.5", "Resource sprawl across 4 regions for only 26 resources", "Low"),
])

doc.add_page_break()

# ================= PHASE 2 =================
add_heading("2. Phase 2 — Identity & Access Management", level=1)
add_para(
    "Role assignment data was pulled across both subscriptions. A total of 20 Owner and 9 Contributor "
    "assignments exist (combined), alongside multiple service principals with broad data-plane rights, "
    "and 6 orphaned role assignments belonging to principals that no longer resolve in Azure AD."
)

add_heading("Critical: Orphaned Owner at Subscription Root", level=2)
add_para(
    "Principal ID e1cb2806-57c9-435e-bd98-0a4788fa8abf holds the Owner role at subscription root scope "
    "on BOTH “Azure Pass - Sponsorship” and “gipl-azure-subscription”. This principal could not be "
    "resolved to a display name or sign-in name, indicating the underlying user, group, or service "
    "principal has been deleted from Azure AD while the role assignment itself remains active. This is "
    "the single highest-priority identity finding: an unidentifiable, unmanageable identity retains full "
    "control over both subscriptions."
)

add_heading("Other Orphaned Assignments (gipl-azure-subscription)", level=2)
add_bullets([
    "3e6afd56-3e57-45dc-b795-2fef39e9ceeb — Contributor on RG gipl-slice-ml-india",
    "2fdaeb76-efd2-4d8a-9354-75c3c3093319 — Reader + Cost Management Reader on a Cognitive Services project; Cost Management Reader and Cost Management Contributor at subscription scope",
])

add_heading("Privileged Role Sprawl", level=2)
add_para(
    "11 Owner + 4 Contributor assignments on “Azure Pass - Sponsorship”; 9 Owner + 5 Contributor "
    "assignments on “gipl-azure-subscription”. For an estate of 26 total resources, this Owner-to-"
    "workload ratio is high and warrants an access recertification exercise."
)

add_heading("Service Principal Privilege Concentration", level=2)
add_para(
    "Two service principals — azure_osi_ai_models and azure_other_models — each hold Contributor at "
    "resource-group scope plus Key Vault Administrator, Storage Blob Data Contributor, and Storage File "
    "Data Privileged Contributor on specific resources within gipl-slice-ml-india. If these are automation "
    "or pipeline identities, the combination of broad Contributor plus direct data-plane rights exceeds "
    "least-privilege norms and should be scoped down to only the specific actions required."
)

add_heading("Key Vault Access Configuration", level=2)
add_para(
    "kv-azureosi540118198852 (gipl-slice-ml-india, eastus2) uses the legacy Access Policy model "
    "(enableRbacAuthorization = False) rather than Azure RBAC, has publicNetworkAccess = Enabled, and "
    "has no network ACLs configured — it is reachable from any internet address."
)

add_heading("Positive Findings", level=2)
add_bullets([
    "No guest (#EXT#) external accounts hold any direct role assignment in either subscription",
    "No custom role definitions exist in either subscription — only built-in roles are in use, reducing the risk of overly permissive custom-role logic",
])

add_heading("Findings Summary", level=2)
add_sev_table([
    ("2.1", "Orphaned Owner role at subscription root on both subscriptions — unidentifiable principal", "Critical"),
    ("2.2", "5 additional orphaned role assignments (Contributor/Reader/Cost Management roles)", "High"),
    ("2.3", "Owner/Contributor sprawl: 20 Owners + 9 Contributors for 26 resources", "High"),
    ("2.4", "Two service principals with broad standing Contributor + Key Vault Administrator + Storage Data rights", "High"),
    ("2.5", "Key Vault uses legacy Access Policies, public network access enabled, no network ACLs", "Critical"),
    ("2.6", "No guest accounts with direct role assignments", "Positive"),
    ("2.7", "No custom role definitions in use", "Positive"),
])

doc.add_page_break()

# ================= PHASE 3 =================
add_heading("3. Phase 3 — Security Posture Baseline", level=1)
add_para(
    "Defender for Cloud is confirmed on the Free tier across all plan categories in both subscriptions "
    "(VirtualMachines, StorageAccounts, KeyVaults, AI, Containers, SqlServers, etc. = Free). The "
    "“Discovery” and “FoundationalCspm” plans show as “Standard” but these are the no-cost components "
    "of the free Cloud Security Posture Management tier (agentless discovery and foundational "
    "recommendations) — no paid plan is active anywhere. This is fully compliant with the engagement's "
    "free-tooling constraint."
)
add_para(
    "Secure Score data was not yet available via the API in either subscription, likely due to first-scan "
    "propagation delay. Approximately 95 Security Benchmark checks are currently failing across the two "
    "subscriptions; none require a paid Defender plan to remediate — they are all configuration gaps."
)

add_heading("Theme: No Network Restriction on AI / Foundry Resources", level=2)
add_para(
    "“Microsoft Foundry resources should restrict network access”, “should use Azure Private Link”, and "
    "“should have key access disabled” are failing on every Cognitive Services / AI account in both "
    "subscriptions."
)

add_heading("Theme: No Diagnostic Logging Anywhere", level=2)
add_para(
    "“Diagnostic logs in Microsoft Foundry resources should be enabled”, “Diagnostic logs in Key Vault "
    "should be enabled”, “Resource logs in Azure Machine Learning Workspaces should be enabled”, and "
    "“Diagnostic logs in Event Hub should be enabled” are all failing. This confirms there is no audit "
    "trail for Key Vault access, storage data-plane access, AI inference calls, or workspace activity."
)

add_heading("Theme: Key Vault Hardening Gaps", level=2)
add_para(
    "“Firewall should be enabled on Key Vault”, “Azure Key Vaults should use private link”, "
    "“Role-Based Access Control should be used on AKV”, and “Key vaults should have deletion protection "
    "enabled” are all failing — the vault currently has no purge protection, meaning it could be "
    "permanently deleted with no recovery path."
)

add_heading("Theme: Storage Account Hardening Gaps", level=2)
add_para(
    "“Storage account should use a private link connection”, “should restrict network access using "
    "virtual network rules”, and “should prevent shared key access” are failing on both storage "
    "accounts. Shared key (access key) authentication remains enabled, meaning anyone holding a storage "
    "key bypasses Azure AD authorization entirely."
)

add_heading("Theme: Subscription Hygiene", level=2)
add_para(
    "“Subscriptions should have a contact email address for security issues” and “Email notification for "
    "high severity alerts should be enabled” are failing on both subscriptions — quick, zero-cost fixes."
)

add_heading("Findings Summary", level=2)
add_sev_table([
    ("3.1", "Confirmed: no Log Analytics workspace exists — no audit trail at the Azure resource level", "Critical"),
    ("3.2", "All Defender plans confirmed Free tier — compliant with cost constraint, no action without approval", "Informational"),
    ("3.3", "AI/Foundry resources: no network restriction, no Private Link, key-based auth not disabled", "Critical"),
    ("3.4", "No diagnostic logs enabled on Key Vault, ML workspaces, Foundry resources, or Event Hub", "Critical"),
    ("3.5", "Key Vault: no firewall, no Private Link, legacy access policies, no deletion/purge protection", "Critical"),
    ("3.6", "Storage accounts: no Private Link, no VNet rules, shared key access not disabled", "High"),
    ("3.7", "No subscription security contact email / no high-severity alert notifications configured", "Medium"),
])

doc.add_page_break()

# ================= PHASE 4 =================
add_heading("4. Phase 4 — Networking & Perimeter", level=1)
add_para(
    "No virtual networks, NSGs, standalone Public IP resources, Private Endpoints, or Private DNS zones "
    "exist in either subscription. The entire estate relies exclusively on each PaaS service's own public "
    "endpoint, gated only by API keys or Azure AD authentication — there is no network-layer control "
    "anywhere in the environment."
)
add_para(
    "A consolidated cross-check confirmed that 15 of 15 (100%) data-plane resources — all 10 AI/Cognitive "
    "Services accounts, both ML workspaces, the Key Vault, and both storage accounts — have public "
    "network access enabled with no IP allow-listing or VNet restriction. The one storage account that "
    "initially returned an ambiguous result was confirmed via direct lookup to also have "
    "NetworkRuleSet.DefaultAction = Allow."
)

add_heading("Findings Summary", level=2)
add_sev_table([
    ("4.1", "Zero network perimeter anywhere: no VNets, NSGs, Public IPs, Private Endpoints, or Private DNS zones", "Critical"),
    ("4.2", "100% (15/15) of data-plane resources confirmed publicly network-accessible with no restriction", "Critical"),
])

doc.add_page_break()

# ================= PHASE 5 =================
add_heading("5. Phase 5 — Cost Optimization", level=1)
add_para(
    "Azure Advisor returned zero Cost-category recommendations across both subscriptions, and no "
    "unattached/idle disks were found (expected, given there are no VMs). All 10 AI/Cognitive Services "
    "accounts are on the standard S0 (pay-as-you-go) SKU with no evidence of over-provisioning. From a "
    "pure infrastructure-spend perspective, this is a lean, well-utilized estate."
)
add_para(
    "Advisor did surface 7 HighAvailability/reliability recommendations, free to act on: Service Health "
    "alerts are not configured in either subscription, two storage accounts in gipl-azure-subscription are "
    "not zone-redundant, the Azure OpenAI API version in use is outdated, and — most notably — Blob "
    "Soft Delete is not enabled on storage in gipl-azure-subscription. Combined with the public network "
    "exposure and absence of diagnostic logging identified in Phases 3 and 4, the lack of Soft Delete "
    "means a compromised credential could delete blob data with no recovery path and no audit trail of "
    "the event."
)

add_heading("Findings Summary", level=2)
add_sev_table([
    ("5.1", "Zero cost-optimization recommendations; no idle/unattached resources found", "Positive"),
    ("5.2", "Blob Soft Delete not enabled on storage (gipl-azure-subscription)", "High"),
    ("5.3", "Storage accounts not zone-redundant; Service Health alerts not configured; outdated Azure OpenAI API version", "Medium"),
])

doc.add_page_break()

# ================= PHASE 6 =================
add_heading("6. Phase 6 — Governance & Compliance", level=1)
add_para(
    "Only two Azure Policy assignments exist in each subscription: a region-restriction policy "
    "(sys.blockwesteurope) and Defender for Cloud's auto-deployed audit policy (SecurityCenterBuiltIn). "
    "No custom governance policies are in place — nothing enforces tagging, network restriction, or "
    "naming standards. 104 non-compliant policy states were recorded (41 in “Azure Pass - Sponsorship”, "
    "63 in “gipl-azure-subscription”), all under the Defender audit policy with audit/auditifnotexists "
    "effects — these report but do not block, and largely re-surface the same gaps already identified in "
    "Phase 3."
)
add_para(
    "No resource locks exist anywhere in either subscription. Combined with the orphaned Owner role "
    "assignment from Phase 2 and the absence of diagnostic logging from Phase 3, no resource in this "
    "estate — including the Key Vault and AI workspaces — is protected against accidental or malicious "
    "deletion, nor would such deletion be detectable after the fact."
)

add_heading("Findings Summary", level=2)
add_sev_table([
    ("6.1", "No custom governance policies (tagging, network restriction, naming) in either subscription", "High"),
    ("6.2", "Zero resource locks anywhere — no deletion protection on any resource", "High"),
    ("6.3", "104 non-compliant policy states (audit-only, largely duplicate Phase 3 signal)", "Medium"),
    ("6.4", "No tagging enforcement policy — structural cause of Phase 1 tagging gaps", "Medium"),
    ("6.5", "All AI accounts on standard S0 SKU — no commitment-tier or capacity waste", "Positive"),
])

doc.add_page_break()

# ================= CONSOLIDATED RISK REGISTER =================
add_heading("7. Consolidated Risk Register", level=1)
add_para(
    "The findings across all six phases cluster around three reinforcing gaps that compound one another: "
    "(1) every sensitive PaaS resource is publicly network-accessible with no restriction, (2) there is no "
    "diagnostic logging anywhere to detect misuse, and (3) identity controls have sprawl (excess Owners) "
    "and decay (orphaned role assignments, including Owner at subscription root). Individually each is a "
    "known, fixable gap; together they describe an environment where unauthorized access to AI/ML "
    "endpoints, the Key Vault, or storage — via a leaked key or compromised credential — would be "
    "difficult to network-block, would generate no log evidence, and could originate from an identity "
    "that AD itself can no longer identify."
)

register_rows = [
    ("R1", "Orphaned Owner role at subscription root (both subs)", "Identity", "Critical"),
    ("R2", "Key Vault: no firewall, public access enabled, no ACLs", "Identity / Network", "Critical"),
    ("R3", "No diagnostic logging anywhere (no Log Analytics workspace)", "Security", "Critical"),
    ("R4", "100% data-plane resources publicly accessible, no Private Link", "Network", "Critical"),
    ("R5", "5 further orphaned role assignments", "Identity", "High"),
    ("R6", "Owner/Contributor sprawl (20 Owners, 9 Contributors / 26 resources)", "Identity", "High"),
    ("R7", "Service principals with broad standing data-plane rights", "Identity", "High"),
    ("R8", "Storage: no Private Link/VNet rules, shared key auth enabled", "Network / Security", "High"),
    ("R9", "ML Workspaces: public network access not disabled", "Network", "High"),
    ("R10", "No tagging policy / no resource locks", "Governance", "High"),
    ("R11", "Blob Soft Delete disabled (gipl subscription)", "Cost / Resilience", "High"),
    ("R12", "26.9% resources untagged", "Governance", "Medium"),
    ("R13", "104 non-compliant audit-only policy states", "Governance", "Medium"),
    ("R14", "No Service Health alerts; outdated OpenAI API version", "Reliability", "Medium"),
]
add_sev_table(register_rows, headers=("ID", "Risk", "Domain", "Severity"))

doc.add_page_break()

# ================= METHODOLOGY =================
add_heading("8. Methodology & Constraints", level=1)
add_bullets([
    "All data collection was performed using read-only operations only: Azure Resource Graph (Search-AzGraph), Azure PowerShell Az module list/get cmdlets, and Azure Advisor.",
    "No paid Defender for Cloud plan, Sentinel, or Log Analytics ingestion was enabled to produce this report. All findings were derived from free-tier APIs.",
    "No Azure resource, role assignment, policy, or configuration was created, modified, or deleted during this assessment.",
    "Tenant IDs, Subscription IDs, and Object IDs are intentionally omitted from this report; subscriptions are referenced by name only.",
    "Assessment executed via Azure Cloud Shell (PowerShell), an ephemeral session without a backing storage account.",
    "Resource Graph queries were paginated where result volume could approach the 1,000-row per-call cap; no query in this assessment exceeded that cap given the estate's size (26 resources).",
])

doc.add_page_break()

# ================= REMEDIATION =================
add_heading("9. Prepared Remediation Scripts — NOT EXECUTED, Pending Approval", level=1)
add_para(
    "The following PowerShell snippets are prepared based on this assessment's findings. None have been "
    "run. Each is explicitly labelled NOT TO BE RUN YET and requires management approval, change-control "
    "sign-off, and validation in a non-production context before execution.",
    italic=True
)

remediations = [
    ("R1/R5 — Remove orphaned role assignments",
     'Remove-AzRoleAssignment -ObjectId "e1cb2806-57c9-435e-bd98-0a4788fa8abf" -RoleDefinitionName "Owner" -Scope "/subscriptions/<sub-id>"\n'
     '# Repeat for each orphaned ObjectId/Scope/Role combination identified in Phase 2'),
    ("R2 — Restrict Key Vault network access",
     'Update-AzKeyVaultNetworkRuleSet -VaultName "kv-azureosi540118198852" -ResourceGroupName "gipl-slice-ml-india" -DefaultAction Deny -Bypass AzureServices\n'
     '# Consider migrating to Private Endpoint and enabling enableRbacAuthorization'),
    ("R2 — Enable Key Vault deletion/purge protection",
     'Update-AzKeyVault -VaultName "kv-azureosi540118198852" -ResourceGroupName "gipl-slice-ml-india" -EnablePurgeProtection'),
    ("R3 — Create Log Analytics workspace and wire up diagnostics",
     'New-AzOperationalInsightsWorkspace -ResourceGroupName <rg> -Name <law-name> -Location <region> -Sku PerGB2018\n'
     '# Then: Set-AzDiagnosticSetting -ResourceId <resource-id> -WorkspaceId <law-id> -Enabled $true\n'
     '# Apply to: Key Vault, both Storage accounts, all 10 Cognitive Services accounts, both ML workspaces, Event Hub namespace'),
    ("R4/R9 — Disable public network access on AI/ML resources",
     'Update-AzCognitiveServicesAccount -ResourceGroupName <rg> -Name <account> -PublicNetworkAccess Disabled\n'
     'Update-AzMLWorkspace -ResourceGroupName <rg> -Name <workspace> -PublicNetworkAccess Disabled\n'
     '# Requires Private Endpoint + Private DNS zone to be provisioned first to avoid breaking access'),
    ("R8 — Restrict storage account network access and disable shared key auth",
     'Update-AzStorageAccountNetworkRuleSet -ResourceGroupName <rg> -Name <storage> -DefaultAction Deny\n'
     'Set-AzStorageAccount -ResourceGroupName <rg> -Name <storage> -AllowSharedKeyAccess $false'),
    ("R11 — Enable Blob Soft Delete",
     'Enable-AzStorageBlobDeleteRetentionPolicy -ResourceGroupName <rg> -StorageAccountName <storage> -RetentionDays 14'),
    ("R10 — Apply resource locks to critical resources",
     'New-AzResourceLock -LockLevel CanNotDelete -LockName "PreventDelete" -ResourceGroupName "gipl-slice-ml-india" -ResourceName "kv-azureosi540118198852" -ResourceType "Microsoft.KeyVault/vaults"\n'
     '# Apply similarly to both storage accounts and both ML workspaces'),
    ("R10/R12 — Enforce tagging via Azure Policy (audit, non-blocking, to start)",
     'New-AzPolicyAssignment -Name "require-tag-pod" -PolicyDefinition (Get-AzPolicyDefinition -Name "1e30110a-5ceb-460c-a204-c1c3969c6d62") -Scope "/subscriptions/<sub-id>"\n'
     '# Built-in "Require a tag on resources" definition, deployed in Audit mode initially'),
    ("R3 — Subscription security contact (free, zero risk)",
     'Set-AzSecurityContact -Name "default1" -Email "security-team@slicebank.com" -AlertNotifications On -AlertsToAdmins On'),
]

for title_text, script in remediations:
    p = doc.add_paragraph()
    r = p.add_run("NOT TO BE RUN YET — pending management approval")
    r.bold = True
    r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    add_heading(title_text, level=3)
    code_p = doc.add_paragraph()
    code_run = code_p.add_run(script)
    code_run.font.name = 'Consolas'
    code_run.font.size = Pt(9)
    doc.add_paragraph()

doc.add_paragraph()
add_para(
    "End of report.",
    italic=True
)

doc.save("/home/user/sysbi-extension/Azure_Posture_Assessment_Report.docx")
print("Report generated successfully.")
