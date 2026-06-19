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
    return doc.add_heading(text, level=level)

def add_table(rows, headers, sev_col_index=None, col_widths=None, font_size=9):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        for p in hdr_cells[i].paragraphs:
            p.runs[0].bold = True
            p.runs[0].font.size = Pt(font_size)
    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
            for p in cells[i].paragraphs:
                for r in p.runs:
                    r.font.size = Pt(font_size)
        if sev_col_index is not None:
            sev = row[sev_col_index]
            if sev in SEV_COLORS:
                set_cell_shading(cells[sev_col_index], SEV_COLORS[sev])
    doc.add_paragraph()
    return table

def add_sev_table(rows, headers=("#", "Finding", "Severity")):
    return add_table(rows, headers, sev_col_index=len(headers) - 1, font_size=10)

def add_para(text, bold=False, italic=False, size=None, color=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color
    return p

def add_bullets(items):
    for it in items:
        doc.add_paragraph(it, style='List Bullet')

SUB1 = "Azure Pass - Sponsorship"
SUB2 = "gipl-azure-subscription"

# ================= COVER =================
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("Azure Posture Assessment")
run.bold = True
run.font.size = Pt(28)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run("Security, Cost & Architecture Review — Detailed Edition")
run.font.size = Pt(16)
run.italic = True

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta.add_run(f"\nPrepared: {datetime.date.today().strftime('%d %B %Y')}\n").font.size = Pt(11)
meta.add_run(f"Scope: Subscriptions “{SUB1}” and “{SUB2}”\n").font.size = Pt(11)
meta.add_run("Method: Read-only assessment using Azure Resource Graph, Azure CLI/PowerShell (Az module), and Azure Advisor (free tier)\n").font.size = Pt(11)
meta.add_run("Note: No paid security service was enabled to produce this report. No resources were modified. Tenant/Subscription/Object GUIDs are shown only where required to identify orphaned or unnamed principals; all other identifiers are referenced by display name.").font.size = Pt(11)

doc.add_page_break()

# ================= EXECUTIVE SUMMARY =================
add_heading("Executive Summary", level=1)

add_para(
    "This assessment reviewed two Azure subscriptions supporting an AI/ML data science platform "
    f"(“{SUB1}” and “{SUB2}”). The environment is small (26 resources total) and entirely "
    "PaaS-based — there are no virtual machines, virtual networks, or traditional IaaS network perimeter. "
    "The estate is built around Azure OpenAI / Anthropic / Cognitive Services accounts, Azure Machine "
    "Learning workspaces, one Key Vault, and two Storage accounts."
)

add_para(
    "The assessment found a consistent and material risk pattern: every sensitive data-plane resource in "
    "both subscriptions is reachable directly over the public internet, with no network-layer restriction, "
    "and no diagnostic logging is configured anywhere. This report names every affected resource, every "
    "principal holding privileged access, and every orphaned role assignment found, so each item can be "
    "individually tracked to remediation."
)

add_para("Key statistics:", bold=True)
add_bullets([
    "26 resources across 2 subscriptions, 5 resource groups, 4 regions",
    "15 of 15 (100%) data-plane resources (AI accounts, ML workspaces, Key Vault, Storage) have public network access enabled with no restriction",
    "Zero Log Analytics workspaces — no centralized logging or audit trail exists",
    "1 orphaned principal (Object ID e1cb2806-57c9-435e-bd98-0a4788fa8abf) holds Owner at subscription root scope on BOTH subscriptions",
    "20 active Owner role assignments and 9 active Contributor assignments across both subscriptions, held by 16 distinct named individuals/identities",
    "Key Vault kv-azureosi540118198852 uses legacy Access Policies (not RBAC), has no firewall, and lacks deletion protection",
    "Zero resource locks exist anywhere",
    "No tagging enforcement policy exists; 7 named resources are untagged",
    "Defender for Cloud is Free tier throughout — ~95 Security Benchmark checks fail, none requiring a paid plan to fix",
    "Azure Advisor found zero cost-optimization opportunities and no idle/unattached resources",
])

p = doc.add_paragraph()
r = p.add_run("Overall risk posture: ")
r.bold = True
r2 = p.add_run("HIGH — driven by identity and network exposure findings, not by cost or resource sprawl.")
r2.bold = True
r2.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)

add_para(
    "All identified issues are remediable at zero incremental cost using free-tier Azure capabilities. No "
    "paid Defender for Cloud plan, Sentinel, or other paid service is required. Prepared remediation "
    "scripts are included in Section 10, marked NOT TO BE RUN pending management approval."
)

add_heading("Findings Summary by Severity", level=2)
summary_rows = [
    ("1", "Orphaned principal e1cb2806-... holds Owner at subscription root on both subscriptions", "Critical"),
    ("2", "Key Vault kv-azureosi540118198852 has no firewall, public access enabled, no network ACLs", "Critical"),
    ("3", "No Log Analytics workspace / no diagnostic logging anywhere in either subscription", "Critical"),
    ("4", "All 15 named AI/Storage/Key Vault/ML data-plane resources publicly network-accessible", "Critical"),
    ("5", "5 additional orphaned role assignments (named Object IDs below)", "High"),
    ("6", "Owner/Contributor sprawl: 20 Owner + 9 Contributor assignments across 16 named identities", "High"),
    ("7", "Service principals azure_osi_ai_models and azure_other_models hold broad standing rights", "High"),
    ("8", "Storage accounts siemstorageaccount1 and stazureosiai540118198852: no private link, shared key access enabled", "High"),
    ("9", "ML Workspaces azure_osi_ai_models and azure_other_models: public network access not disabled", "High"),
    ("10", "No tagging enforcement policy / no resource locks anywhere", "High"),
    ("11", "Blob Soft Delete not enabled on storage (gipl-azure-subscription)", "High"),
    ("12", "7 named resources untagged", "Medium"),
    ("13", "104 non-compliant policy states under Defender's built-in audit policy", "Medium"),
    ("14", "No Service Health alerts configured; outdated Azure OpenAI API version in use", "Medium"),
    ("15", "Region sprawl across 4 regions for 26 resources", "Low"),
    ("16", "No guest/external accounts with direct role assignments", "Positive"),
    ("17", "No custom role definitions in use", "Positive"),
    ("18", "Zero Azure Advisor cost recommendations; no idle/unattached resources", "Positive"),
    ("19", "No paid Defender plans enabled — compliant with free-tooling constraint", "Positive"),
]
add_sev_table(summary_rows)

doc.add_page_break()

# ================= TOC =================
add_heading("Report Contents", level=1)
add_bullets([
    "1. Phase 1 — Discovery & Inventory (named resources)",
    "2. Phase 2 — Identity & Access Management (named principals, full role assignment register)",
    "3. Phase 3 — Security Posture Baseline (named failing resources)",
    "4. Phase 4 — Networking & Perimeter (named exposed resources)",
    "5. Phase 5 — Cost Optimization (named SKUs and recommendations)",
    "6. Phase 6 — Governance & Compliance (named policy assignments)",
    "7. Consolidated Risk Register",
    "8. Asset Register — All Named Resources",
    "9. Methodology & Constraints",
    "10. Prepared Remediation Scripts (NOT executed — pending approval)",
])
doc.add_page_break()

# ================= PHASE 1 =================
add_heading("1. Phase 1 — Discovery & Inventory", level=1)
add_para(
    "26 resources across 5 resource groups and 4 regions (southindia: 13, eastus2: 8, eastus: 3, "
    "centralindia: 2). No virtual machines or virtual networks exist in either subscription."
)

add_heading("Resource Groups (named)", level=2)
add_table(
    [
        ("SIEM", SUB2, "centralindia", "None — contains only a Syntex document processor; no Log Analytics/Sentinel despite the name"),
        ("gipl-slice-ml-india", SUB2, "southindia", "None"),
        ("slicegpt", SUB2, "southindia", "None"),
        ("dashboards", SUB1, "eastus", "None"),
        ("slice_ml_ds", SUB1, "eastus", "POD = Data Science"),
    ],
    headers=("Resource Group", "Subscription", "Location", "Tags"),
)

add_heading("Untagged Resources (named)", level=2)
add_table(
    [
        ("Syntex", "siem", SUB2, "microsoft.syntex/documentprocessors"),
        ("da-ml-openai-api/default", "gipl-slice-ml-india", SUB2, "microsoft.cognitiveservices/accounts/projects"),
        ("de-ml-anthropic-resource", "gipl-slice-ml-india", SUB2, "microsoft.cognitiveservices/accounts"),
        ("de-ml-openai-api/default", "gipl-slice-ml-india", SUB2, "microsoft.cognitiveservices/accounts/projects"),
        ("engg-ml-openai-api/default", "gipl-slice-ml-india", SUB2, "microsoft.cognitiveservices/accounts/projects"),
        ("hardi-mp2f37l6-eastus2", "slice_ml_ds", SUB1, "microsoft.cognitiveservices/accounts"),
        ("hardi-mp2f37l6-eastus2/hardi-mp2f37l6-eastus2_project", "slice_ml_ds", SUB1, "microsoft.cognitiveservices/accounts/projects"),
    ],
    headers=("Resource Name", "Resource Group", "Subscription", "Type"),
)

add_heading("Findings", level=2)
add_sev_table([
    ("1.1", "RG “SIEM” contains no actual centralized logging resource — name is misleading relative to actual capability", "High"),
    ("1.2", "4 of 5 resource groups have no tags; only slice_ml_ds is tagged", "Medium"),
    ("1.3", "7 named resources (26.9%) untagged — listed above", "Medium"),
    ("1.4", "No VMs or VNets in either subscription", "Positive"),
    ("1.5", "Resource sprawl across 4 regions for only 26 resources", "Low"),
])

doc.add_page_break()

# ================= PHASE 2 =================
add_heading("2. Phase 2 — Identity & Access Management", level=1)
add_para(
    "Full role assignment data was captured for both subscriptions. The tables below name every "
    "principal holding a role assignment, the role held, and the scope. Email/sign-in names are included "
    "as captured directly from Azure AD; Object IDs are shown only for principals that could not be "
    "resolved to a name (orphaned assignments) and for service principals."
)

add_heading("2.1 Critical: Orphaned Owner at Subscription Root", level=2)
add_para(
    "Object ID e1cb2806-57c9-435e-bd98-0a4788fa8abf holds Owner at subscription root scope on BOTH "
    f"“{SUB1}” and “{SUB2}”. This principal does not resolve to a display name or sign-in "
    "name in Azure AD, indicating the underlying user, group, or service principal has been deleted while "
    "the role assignment remains active."
)

add_heading("2.2 All Orphaned Role Assignments (named by Object ID)", level=2)
add_table(
    [
        ("e1cb2806-57c9-435e-bd98-0a4788fa8abf", "Owner", "Subscription root", SUB1),
        ("e1cb2806-57c9-435e-bd98-0a4788fa8abf", "Owner", "Subscription root", SUB2),
        ("3e6afd56-3e57-45dc-b795-2fef39e9ceeb", "Contributor", "RG: gipl-slice-ml-india", SUB2),
        ("2fdaeb76-efd2-4d8a-9354-75c3c3093319", "Reader", "Cognitive Services project: da-ml-openai-api", SUB2),
        ("2fdaeb76-efd2-4d8a-9354-75c3c3093319", "Cost Management Reader", "Cognitive Services project: da-ml-openai-api", SUB2),
        ("2fdaeb76-efd2-4d8a-9354-75c3c3093319", "Cost Management Reader", "Subscription", SUB2),
        ("2fdaeb76-efd2-4d8a-9354-75c3c3093319", "Cost Management Contributor", "Subscription", SUB2),
    ],
    headers=("Orphaned Object ID", "Role", "Scope", "Subscription"),
)

add_heading("2.3 Owner Role Assignments — Full Register", level=2)
owners_sub1 = [
    ("Hardikkumar Patel", "hardik.patel@slicebank.com", "Subscription root"),
    ("Dev Kudtharkar", "dev.k@slicebank.com", "Subscription root"),
    ("Rajat Verma", "rajat.verma@slicebank.com", "Subscription root"),
    ("Upendra Singh | slice", "upendra@slicebank.com", "Subscription root"),
    ("Neeraj Prem Verma", "neeraj.pv@slicebank.com", "Subscription root"),
    ("Slice Azure", "slice.azure@slicepay.in", "Subscription root"),
    ("Aditi Kalra", "aditi.kalra@slicepay.in", "Subscription root"),
    ("Rakshan Shetty", "rakshan.shetty@slicebank.com", "Subscription root"),
    ("Srinivas Anand", "srinivas.anand@slicebank.com", "Subscription root"),
    ("Pranay Devasani", "pranay.devasani@slicebank.com", "RG slice_ml_ds (ml-ds-india project)"),
]
owners_sub2 = [
    ("Hardikkumar Patel", "hardik.patel@slicebank.com", "Subscription root"),
    ("Dev Kudtharkar", "dev.k@slicebank.com", "Subscription root"),
    ("Hardikkumar Patel", "hardik.patel@slicebank.com", "ML Workspace (azure_osi_ai_models)"),
    ("Rajat Verma", "rajat.verma@slicebank.com", "Subscription root"),
    ("Upendra Singh | slice", "upendra@slicebank.com", "Subscription root"),
    ("Neeraj Prem Verma", "neeraj.pv@slicebank.com", "Subscription root"),
    ("Rakshan Shetty", "rakshan.shetty@slicebank.com", "Subscription root"),
    ("Srinivas Anand", "srinivas.anand@slicebank.com", "Subscription root"),
]
rows = [(n, e, s, SUB1) for n, e, s in owners_sub1] + [(n, e, s, SUB2) for n, e, s in owners_sub2]
add_table(rows, headers=("Display Name", "Sign-in", "Scope", "Subscription"))
add_para(f"Total named Owner assignments: {len(rows)} (plus the orphaned Owner counted separately in 2.2).", italic=True)

add_heading("2.4 Contributor Role Assignments — Full Register", level=2)
contrib_rows = [
    ("Rakshan Shetty", "rakshan.shetty@slicebank.com", "Subscription root", SUB1),
    ("Amoul Singhi", "amoul.singhi@slicebank.com", "Subscription root", SUB1),
    ("Prakhar Gupta (Tech)", "prakhar.g@slicebank.com", "Subscription root", SUB1),
    ("Vaibhav Gupta", "vaibhav.gupta@slicebank.com", "Subscription root", SUB1),
    ("Tarun Aditya Kotagiri", "tarunaditya.kotagiri@slicebank.com", "RG slicegpt", SUB2),
]
add_table(contrib_rows, headers=("Display Name", "Sign-in", "Scope", "Subscription"))

add_heading("2.5 Other Notable Named Role Assignments", level=2)
add_table(
    [
        ("Rakshan Shetty", "rakshan.shetty@slicebank.com", "User Access Administrator", "Subscription root", SUB1),
        ("Santosh Kaddu", "santosh.kaddu@slicebank.com", "User Access Administrator", "Tenant root \"/\"", SUB1),
        ("Dev Kudtharkar", "dev.k@slicebank.com", "User Access Administrator", "Tenant root \"/\"", SUB1),
        ("Santosh Kaddu", "santosh.kaddu@slicebank.com", "User Access Administrator", "Tenant root \"/\"", SUB2),
        ("Dev Kudtharkar", "dev.k@slicebank.com", "User Access Administrator", "Tenant root \"/\"", SUB2),
        ("Dev Kudtharkar", "dev.k@slicebank.com", "Azure Event Hubs Data Owner", "Subscription root", SUB2),
        ("Venkat V", "venkat.v@slicebank.com", "Azure AI Administrator", "RG gipl-slice-ml-india", SUB2),
        ("ml-ds-india", "(service principal)", "Azure AI Administrator", "RG slice_ml_ds resource", SUB1),
    ],
    headers=("Display Name", "Sign-in / Type", "Role", "Scope", "Subscription"),
)
add_para(
    "Note: “User Access Administrator” at the tenant root scope (\"/\") for Santosh Kaddu and Dev "
    "Kudtharkar grants the ability to assign roles across every subscription in the tenant, not just the "
    "two in scope of this assessment — flagged for awareness even though out-of-scope subscriptions "
    "were not assessed.",
    italic=True,
)

add_heading("2.6 Service Principal Privilege Detail (named)", level=2)
add_table(
    [
        ("ml-ds-india", "Azure AI Administrator", "Cognitive Services account hardi-mp2f37l6-eastus2", SUB1),
        ("(unnamed SP)", "Contributor", "RG gipl-slice-ml-india", SUB2),
        ("azure_osi_ai_models", "Contributor", "RG gipl-slice-ml-india", SUB2),
        ("azure_osi_ai_models", "Storage File Data Privileged Contributor", "Storage account stazureosiai540118198852", SUB2),
        ("azure_osi_ai_models", "Key Vault Administrator", "Key Vault kv-azureosi540118198852", SUB2),
        ("azure_osi_ai_models", "Storage Blob Data Contributor", "Storage account stazureosiai540118198852", SUB2),
        ("azure_osi_ai_models", "Azure AI Administrator", "ML Workspace azure_osi_ai_models", SUB2),
        ("azure_osi_ai_models", "Contributor", "Cognitive Services account de-ml-openai-api", SUB2),
        ("azure_other_models", "Storage Blob Data Contributor", "Storage account stazureosiai540118198852", SUB2),
        ("azure_other_models", "Storage Table Data Contributor", "Storage account stazureosiai540118198852", SUB2),
        ("azure_other_models", "Storage Account Contributor", "Storage account stazureosiai540118198852", SUB2),
        ("azure_other_models", "Contributor", "Key Vault kv-azureosi540118198852", SUB2),
        ("azure_other_models", "Key Vault Administrator", "Key Vault kv-azureosi540118198852", SUB2),
        ("azure_other_models", "Storage File Data Privileged Contributor", "Storage account stazureosiai540118198852", SUB2),
        ("azure_other_models", "Reader", "Storage account stazureosiai540118198852", SUB2),
        ("azure_other_models", "Azure AI Administrator", "ML Workspace azure_other_models", SUB2),
    ],
    headers=("Service Principal", "Role", "Scope (resource)", "Subscription"),
)
add_para(
    "azure_osi_ai_models and azure_other_models each combine RG-level Contributor with direct "
    "Key Vault Administrator and Storage Data Contributor rights on specific resources — a concentration "
    "of privilege exceeding least-privilege norms for what are presumed to be automation/pipeline "
    "identities.",
)

add_heading("2.7 Key Vault Access Configuration (named)", level=2)
add_table(
    [
        ("kv-azureosi540118198852", "gipl-slice-ml-india", "eastus2", "Access Policies (legacy)", "Enabled", "None configured"),
    ],
    headers=("Key Vault Name", "Resource Group", "Location", "Authorization Model", "Public Network Access", "Network ACLs"),
)

add_heading("Positive Findings", level=2)
add_bullets([
    "No guest (#EXT#) external accounts hold any direct role assignment in either subscription",
    "No custom role definitions exist in either subscription",
])

add_heading("Findings Summary", level=2)
add_sev_table([
    ("2.1", "Orphaned Owner (e1cb2806-...) at subscription root on both subscriptions", "Critical"),
    ("2.2", "5 additional orphaned role assignments (3e6afd56-..., 2fdaeb76-... x4)", "High"),
    ("2.3", "20 named Owner + 5 named Contributor assignments across 16 distinct identities", "High"),
    ("2.4", "azure_osi_ai_models / azure_other_models hold broad standing Contributor + Key Vault Administrator + Storage Data rights", "High"),
    ("2.5", "Key Vault kv-azureosi540118198852: legacy Access Policies, public access enabled, no network ACLs", "Critical"),
    ("2.6", "Tenant-root User Access Administrator held by Santosh Kaddu and Dev Kudtharkar", "Medium"),
    ("2.7", "No guest accounts with direct role assignments", "Positive"),
    ("2.8", "No custom role definitions in use", "Positive"),
])

doc.add_page_break()

# ================= PHASE 3 =================
add_heading("3. Phase 3 — Security Posture Baseline", level=1)
add_para(
    "Defender for Cloud confirmed on the Free tier across all plan categories in both subscriptions — no "
    "paid plan is active. ~95 Security Benchmark checks are failing; none require a paid plan to remediate."
)

add_heading("3.1 Named Resources Failing “Foundry resources should restrict network access / use Private Link / disable key access”", level=2)
add_table(
    [
        ("da-ml-openai-api", "Cognitive Services", "gipl-slice-ml-india", SUB2),
        ("de-ml-anthropic-resource", "Cognitive Services", "gipl-slice-ml-india", SUB2),
        ("de-ml-openai-api", "Cognitive Services", "gipl-slice-ml-india", SUB2),
        ("engg-ml-openai-api", "Cognitive Services", "gipl-slice-ml-india", SUB2),
        ("slicegpt", "Cognitive Services", "slicegpt", SUB2),
        ("dev-poc-ds", "Cognitive Services", "slice_ml_ds", SUB1),
        ("fraud-ds-prod", "Cognitive Services", "slice_ml_ds", SUB1),
        ("hardi-mp2f37l6-eastus2", "Cognitive Services", "slice_ml_ds", SUB1),
        ("merchant-prod-ds", "Cognitive Services", "slice_ml_ds", SUB1),
        ("ml-ds-india", "Cognitive Services", "slice_ml_ds", SUB1),
    ],
    headers=("Resource Name", "Type", "Resource Group", "Subscription"),
)

add_heading("3.2 Named Resources Failing Key Vault Hardening Checks", level=2)
add_para(
    "kv-azureosi540118198852 (gipl-slice-ml-india, eastus2) — failing: firewall not enabled, no Private "
    "Link, RBAC not used, no deletion/purge protection configured."
)

add_heading("3.3 Named Resources Failing Storage Hardening Checks", level=2)
add_table(
    [
        ("siemstorageaccount1", "siem", SUB2, "TLS1_2", "False", "True", "Allow (no restriction)"),
        ("stazureosiai540118198852", "gipl-slice-ml-india", SUB2, "TLS1_2", "False", "True", "Allow (no restriction)"),
    ],
    headers=("Storage Account", "Resource Group", "Subscription", "Min TLS", "Allow Blob Public Access", "HTTPS Only", "Network Default Action"),
)
add_para(
    "Both storage accounts fail “use private link connection”, “restrict network access using "
    "VNet rules”, and “prevent shared key access”. Note minTls=TLS1_2 and "
    "supportsHttpsOnly=True are correctly configured (positive), and anonymous blob public access is "
    "disabled (positive) — the gap is specifically network-layer restriction and shared-key auth."
)

add_heading("3.4 Subscription Hygiene", level=2)
add_para(
    "Both subscriptions fail “Subscriptions should have a contact email address for security "
    "issues” and “Email notification for high severity alerts should be enabled.”"
)

add_heading("Findings Summary", level=2)
add_sev_table([
    ("3.1", "No Log Analytics workspace — confirmed no audit trail at the Azure resource level", "Critical"),
    ("3.2", "All Defender plans confirmed Free tier — compliant with cost constraint", "Informational"),
    ("3.3", "10 named Cognitive Services accounts: no network restriction, no Private Link, key auth not disabled", "Critical"),
    ("3.4", "No diagnostic logs on Key Vault, ML workspaces, Foundry resources, Event Hub", "Critical"),
    ("3.5", "kv-azureosi540118198852: no firewall, no Private Link, legacy access policies, no purge protection", "Critical"),
    ("3.6", "siemstorageaccount1 and stazureosiai540118198852: no Private Link/VNet rules, shared key access enabled", "High"),
    ("3.7", "No subscription security contact email / high-severity alerts configured (both subscriptions)", "Medium"),
])

doc.add_page_break()

# ================= PHASE 4 =================
add_heading("4. Phase 4 — Networking & Perimeter", level=1)
add_para(
    "No VNets, NSGs, standalone Public IPs, Private Endpoints, or Private DNS zones exist in either "
    "subscription. Every PaaS resource relies solely on its own public endpoint."
)

add_heading("4.1 Full Register of Publicly Network-Accessible Data-Plane Resources", level=2)
add_table(
    [
        ("azure_osi_ai_models", "ML Workspace", "gipl-slice-ml-india", SUB2, "Enabled"),
        ("azure_other_models", "ML Workspace", "gipl-slice-ml-india", SUB2, "Enabled"),
        ("da-ml-openai-api", "Cognitive Services", "gipl-slice-ml-india", SUB2, "Enabled"),
        ("de-ml-anthropic-resource", "Cognitive Services", "gipl-slice-ml-india", SUB2, "Enabled"),
        ("de-ml-openai-api", "Cognitive Services", "gipl-slice-ml-india", SUB2, "Enabled"),
        ("dev-poc-ds", "Cognitive Services", "slice_ml_ds", SUB1, "Enabled"),
        ("engg-ml-openai-api", "Cognitive Services", "gipl-slice-ml-india", SUB2, "Enabled"),
        ("fraud-ds-prod", "Cognitive Services", "slice_ml_ds", SUB1, "Enabled"),
        ("hardi-mp2f37l6-eastus2", "Cognitive Services", "slice_ml_ds", SUB1, "Enabled"),
        ("kv-azureosi540118198852", "Key Vault", "gipl-slice-ml-india", SUB2, "Enabled"),
        ("merchant-prod-ds", "Cognitive Services", "slice_ml_ds", SUB1, "Enabled"),
        ("ml-ds-india", "Cognitive Services", "slice_ml_ds", SUB1, "Enabled"),
        ("siemstorageaccount1", "Storage Account", "siem", SUB2, "Enabled"),
        ("slicegpt", "Cognitive Services", "slicegpt", SUB2, "Enabled"),
        ("stazureosiai540118198852", "Storage Account", "gipl-slice-ml-india", SUB2, "Enabled (confirmed via direct lookup: NetworkRuleSet.DefaultAction=Allow)"),
    ],
    headers=("Resource Name", "Type", "Resource Group", "Subscription", "Public Network Access"),
)
add_para("15 of 15 (100%) named data-plane resources are confirmed publicly network-accessible.", bold=True)

add_heading("Findings Summary", level=2)
add_sev_table([
    ("4.1", "Zero network perimeter anywhere: no VNets, NSGs, Public IPs, Private Endpoints, Private DNS zones", "Critical"),
    ("4.2", "100% (15/15) named data-plane resources confirmed publicly network-accessible — full register above", "Critical"),
])

doc.add_page_break()

# ================= PHASE 5 =================
add_heading("5. Phase 5 — Cost Optimization", level=1)
add_para(
    "Zero Cost-category Advisor recommendations in either subscription; no unattached/idle disks found. "
    "All 10 named Cognitive Services accounts are on SKU S0 (pay-as-you-go)."
)

add_heading("5.1 Named Cognitive Services Accounts — SKU/Kind Detail", level=2)
add_table(
    [
        ("da-ml-openai-api", "AIServices", "S0", "southindia", SUB2),
        ("de-ml-anthropic-resource", "AIServices", "S0", "eastus2", SUB2),
        ("de-ml-openai-api", "AIServices", "S0", "southindia", SUB2),
        ("dev-poc-ds", "OpenAI", "S0", "southindia", SUB1),
        ("engg-ml-openai-api", "AIServices", "S0", "southindia", SUB2),
        ("fraud-ds-prod", "OpenAI", "S0", "southindia", SUB1),
        ("hardi-mp2f37l6-eastus2", "AIServices", "S0", "eastus2", SUB1),
        ("merchant-prod-ds", "OpenAI", "S0", "southindia", SUB1),
        ("ml-ds-india", "AIServices", "S0", "southindia", SUB1),
        ("slicegpt", "OpenAI", "S0", "southindia", SUB2),
    ],
    headers=("Resource Name", "Kind", "SKU", "Location", "Subscription"),
)

add_heading("5.2 Named Azure Advisor Reliability Recommendations (free to act on)", level=2)
add_table(
    [
        (SUB1, "High", "Create an Azure Service Health alert"),
        (SUB1, "Medium", "Upgrade your application to use the latest API version from Azure OpenAI"),
        (SUB2, "High", "Enable zone redundancy for storage accounts to improve high availability and resiliency (x2 storage accounts)"),
        (SUB2, "High", "Create an Azure Service Health alert"),
        (SUB2, "Medium", "Upgrade your application to use the latest API version from Azure OpenAI"),
        (SUB2, "Medium", "Enable Soft Delete to protect your blob data"),
    ],
    headers=("Subscription", "Impact", "Recommendation"),
)

add_heading("Findings Summary", level=2)
add_sev_table([
    ("5.1", "Zero cost-optimization recommendations; no idle/unattached resources found", "Positive"),
    ("5.2", "Blob Soft Delete not enabled on storage (gipl-azure-subscription)", "High"),
    ("5.3", "Storage accounts not zone-redundant; Service Health alerts missing; outdated Azure OpenAI API version", "Medium"),
])

doc.add_page_break()

# ================= PHASE 6 =================
add_heading("6. Phase 6 — Governance & Compliance", level=1)

add_heading("6.1 Named Policy Assignments", level=2)
add_table(
    [
        ("sys.blockwesteurope", "Region restriction (built-in)", SUB1),
        ("SecurityCenterBuiltIn", "Defender for Cloud auto-deployed audit policy", SUB1),
        ("sys.blockwesteurope", "Region restriction (built-in)", SUB2),
        ("SecurityCenterBuiltIn", "Defender for Cloud auto-deployed audit policy", SUB2),
    ],
    headers=("Policy Assignment Name", "Purpose", "Subscription"),
)
add_para(
    "No custom governance policies exist in either subscription — nothing enforces tagging, network "
    "restriction, or naming standards."
)

add_heading("6.2 Non-Compliant Policy States", level=2)
add_para(
    "104 total non-compliant policy states recorded (41 in Azure Pass - Sponsorship, 63 in "
    "gipl-azure-subscription), all under SecurityCenterBuiltIn with audit/auditifnotexists effects "
    "(reporting only, non-blocking). Named resources repeatedly cited as non-compliant include the "
    "Cognitive Services accounts dev-poc-ds, ml-ds-india, merchant-prod-ds, fraud-ds-prod, and "
    "hardi-mp2f37l6-eastus2 (Azure Pass - Sponsorship subscription) — these largely duplicate the gaps "
    "already itemized by name in Phase 3."
)

add_heading("6.3 Resource Locks", level=2)
add_para("Zero resource locks exist anywhere in either subscription — confirmed via Get-AzResourceLock against both subscriptions.")

add_heading("Findings Summary", level=2)
add_sev_table([
    ("6.1", "No custom governance policies (tagging, network restriction, naming) in either subscription", "High"),
    ("6.2", "Zero resource locks anywhere — no deletion protection on any resource", "High"),
    ("6.3", "104 non-compliant policy states (audit-only, largely duplicate Phase 3 signal)", "Medium"),
    ("6.4", "No tagging enforcement policy — structural cause of Phase 1 tagging gaps", "Medium"),
    ("6.5", "All 10 AI accounts on standard S0 SKU — no commitment-tier or capacity waste", "Positive"),
])

doc.add_page_break()

# ================= RISK REGISTER =================
add_heading("7. Consolidated Risk Register", level=1)
register_rows = [
    ("R1", "Orphaned Owner (e1cb2806-...) at subscription root, both subs", "Identity", "Critical"),
    ("R2", "kv-azureosi540118198852: no firewall, public access, no ACLs", "Identity / Network", "Critical"),
    ("R3", "No diagnostic logging anywhere (no Log Analytics workspace)", "Security", "Critical"),
    ("R4", "15/15 named data-plane resources publicly accessible, no Private Link", "Network", "Critical"),
    ("R5", "5 further orphaned role assignments (3e6afd56-..., 2fdaeb76-...)", "Identity", "High"),
    ("R6", "20 Owner + 5 Contributor assignments across 16 named identities", "Identity", "High"),
    ("R7", "azure_osi_ai_models / azure_other_models: broad standing data-plane rights", "Identity", "High"),
    ("R8", "siemstorageaccount1, stazureosiai540118198852: no Private Link/VNet rules, shared key auth enabled", "Network / Security", "High"),
    ("R9", "azure_osi_ai_models / azure_other_models ML Workspaces: public network access not disabled", "Network", "High"),
    ("R10", "No tagging policy / no resource locks", "Governance", "High"),
    ("R11", "Blob Soft Delete disabled (gipl-azure-subscription)", "Cost / Resilience", "High"),
    ("R12", "7 named resources untagged", "Governance", "Medium"),
    ("R13", "104 non-compliant audit-only policy states", "Governance", "Medium"),
    ("R14", "No Service Health alerts; outdated OpenAI API version", "Reliability", "Medium"),
]
add_sev_table(register_rows, headers=("ID", "Risk", "Domain", "Severity"))

doc.add_page_break()

# ================= ASSET REGISTER =================
add_heading("8. Asset Register — All Named Resources", level=1)
add_para("Consolidated list of every named resource identified during this assessment, for traceability.")

add_heading("8.1 Cognitive Services / AI Accounts (10)", level=2)
add_bullets([
    "da-ml-openai-api — gipl-slice-ml-india — gipl-azure-subscription",
    "de-ml-anthropic-resource — gipl-slice-ml-india — gipl-azure-subscription",
    "de-ml-openai-api — gipl-slice-ml-india — gipl-azure-subscription",
    "engg-ml-openai-api — gipl-slice-ml-india — gipl-azure-subscription",
    "slicegpt — slicegpt — gipl-azure-subscription",
    "dev-poc-ds — slice_ml_ds — Azure Pass - Sponsorship",
    "fraud-ds-prod — slice_ml_ds — Azure Pass - Sponsorship",
    "hardi-mp2f37l6-eastus2 — slice_ml_ds — Azure Pass - Sponsorship",
    "merchant-prod-ds — slice_ml_ds — Azure Pass - Sponsorship",
    "ml-ds-india — slice_ml_ds — Azure Pass - Sponsorship",
])

add_heading("8.2 ML Workspaces (2)", level=2)
add_bullets([
    "azure_osi_ai_models — gipl-slice-ml-india — gipl-azure-subscription",
    "azure_other_models — gipl-slice-ml-india — gipl-azure-subscription",
])

add_heading("8.3 Storage Accounts (2)", level=2)
add_bullets([
    "siemstorageaccount1 — siem — gipl-azure-subscription",
    "stazureosiai540118198852 — gipl-slice-ml-india — gipl-azure-subscription",
])

add_heading("8.4 Key Vault (1)", level=2)
add_bullets(["kv-azureosi540118198852 — gipl-slice-ml-india — gipl-azure-subscription"])

add_heading("8.5 Other Resources", level=2)
add_bullets([
    "Syntex (document processor) — siem — gipl-azure-subscription",
    "Event Hub namespace (unnamed in inventory output) — gipl-azure-subscription",
    "3x Portal dashboards (unnamed in inventory output) — dashboards RG — Azure Pass - Sponsorship",
])

add_heading("8.6 Named Human Identities with Subscription-Level Privileged Access", level=2)
named_people = sorted(set(
    [n for n, _, _ in owners_sub1] + [n for n, _, _ in owners_sub2] +
    [n for n, _, _, _ in contrib_rows]
))
add_bullets(named_people)

add_heading("8.7 Named Service Principals with Privileged Access", level=2)
add_bullets(["ml-ds-india", "azure_osi_ai_models", "azure_other_models"])

doc.add_page_break()

# ================= METHODOLOGY =================
add_heading("9. Methodology & Constraints", level=1)
add_bullets([
    "All data collection was performed using read-only operations only: Azure Resource Graph (Search-AzGraph), Azure PowerShell Az module list/get cmdlets, and Azure Advisor.",
    "No paid Defender for Cloud plan, Sentinel, or Log Analytics ingestion was enabled to produce this report.",
    "No Azure resource, role assignment, policy, or configuration was created, modified, or deleted during this assessment.",
    "Tenant IDs and Subscription IDs are intentionally omitted from this report; subscriptions are referenced by name only. Object IDs are shown only for orphaned/unresolvable principals and service principals, where no display name exists.",
    "Assessment executed via Azure Cloud Shell (PowerShell), an ephemeral session without a backing storage account.",
    "Resource Graph queries were paginated where result volume could approach the 1,000-row per-call cap; no query in this assessment exceeded that cap given the estate's size (26 resources).",
])

doc.add_page_break()

# ================= REMEDIATION =================
add_heading("10. Prepared Remediation Scripts — NOT EXECUTED, Pending Approval", level=1)
add_para(
    "Each script below targets a specific named resource or principal identified in this report. None "
    "have been run. Each requires management approval, change-control sign-off, and validation in a "
    "non-production context before execution.",
    italic=True,
)

remediations = [
    ("R1/R5 — Remove orphaned role assignments",
     'Remove-AzRoleAssignment -ObjectId "e1cb2806-57c9-435e-bd98-0a4788fa8abf" -RoleDefinitionName "Owner" -Scope "/subscriptions/<sub-id>"\n'
     'Remove-AzRoleAssignment -ObjectId "3e6afd56-3e57-45dc-b795-2fef39e9ceeb" -RoleDefinitionName "Contributor" -Scope "/subscriptions/<sub-id>/resourceGroups/gipl-slice-ml-india"\n'
     '# Repeat for each 2fdaeb76-efd2-4d8a-9354-75c3c3093319 assignment listed in Section 2.2'),
    ("R2 — Restrict Key Vault network access (kv-azureosi540118198852)",
     'Update-AzKeyVaultNetworkRuleSet -VaultName "kv-azureosi540118198852" -ResourceGroupName "gipl-slice-ml-india" -DefaultAction Deny -Bypass AzureServices\n'
     'Update-AzKeyVault -VaultName "kv-azureosi540118198852" -ResourceGroupName "gipl-slice-ml-india" -EnablePurgeProtection -EnableRbacAuthorization'),
    ("R3 — Create Log Analytics workspace and wire up diagnostics",
     'New-AzOperationalInsightsWorkspace -ResourceGroupName <rg> -Name <law-name> -Location <region> -Sku PerGB2018\n'
     '# Apply Set-AzDiagnosticSetting to: kv-azureosi540118198852, siemstorageaccount1, stazureosiai540118198852,\n'
     '# all 10 named Cognitive Services accounts in Section 8.1, and both ML workspaces in Section 8.2'),
    ("R4/R9 — Disable public network access on named AI/ML resources",
     '# Apply to each of the 10 Cognitive Services accounts listed in Section 8.1:\n'
     'Update-AzCognitiveServicesAccount -ResourceGroupName <rg> -Name <account-name> -PublicNetworkAccess Disabled\n'
     '# Apply to both ML workspaces:\n'
     'Update-AzMLWorkspace -ResourceGroupName "gipl-slice-ml-india" -Name "azure_osi_ai_models" -PublicNetworkAccess Disabled\n'
     'Update-AzMLWorkspace -ResourceGroupName "gipl-slice-ml-india" -Name "azure_other_models" -PublicNetworkAccess Disabled\n'
     '# Requires Private Endpoint + Private DNS zone to be provisioned first to avoid breaking access'),
    ("R8 — Restrict storage network access and disable shared key auth",
     'Update-AzStorageAccountNetworkRuleSet -ResourceGroupName "siem" -Name "siemstorageaccount1" -DefaultAction Deny\n'
     'Set-AzStorageAccount -ResourceGroupName "siem" -Name "siemstorageaccount1" -AllowSharedKeyAccess $false\n'
     'Update-AzStorageAccountNetworkRuleSet -ResourceGroupName "gipl-slice-ml-india" -Name "stazureosiai540118198852" -DefaultAction Deny\n'
     'Set-AzStorageAccount -ResourceGroupName "gipl-slice-ml-india" -Name "stazureosiai540118198852" -AllowSharedKeyAccess $false'),
    ("R11 — Enable Blob Soft Delete (gipl-azure-subscription)",
     'Enable-AzStorageBlobDeleteRetentionPolicy -ResourceGroupName "gipl-slice-ml-india" -StorageAccountName "stazureosiai540118198852" -RetentionDays 14\n'
     'Enable-AzStorageBlobDeleteRetentionPolicy -ResourceGroupName "siem" -StorageAccountName "siemstorageaccount1" -RetentionDays 14'),
    ("R10 — Apply resource locks to named critical resources",
     'New-AzResourceLock -LockLevel CanNotDelete -LockName "PreventDelete" -ResourceGroupName "gipl-slice-ml-india" -ResourceName "kv-azureosi540118198852" -ResourceType "Microsoft.KeyVault/vaults"\n'
     'New-AzResourceLock -LockLevel CanNotDelete -LockName "PreventDelete" -ResourceGroupName "gipl-slice-ml-india" -ResourceName "stazureosiai540118198852" -ResourceType "Microsoft.Storage/storageAccounts"\n'
     'New-AzResourceLock -LockLevel CanNotDelete -LockName "PreventDelete" -ResourceGroupName "siem" -ResourceName "siemstorageaccount1" -ResourceType "Microsoft.Storage/storageAccounts"\n'
     '# Apply similarly to both ML workspaces (azure_osi_ai_models, azure_other_models)'),
    ("R7 — Scope down service principal privileges",
     '# Review azure_osi_ai_models and azure_other_models actual usage, then replace broad Contributor\n'
     '# grants with narrowly-scoped custom roles limited to the specific data actions each automation flow requires.\n'
     '# Example: remove RG-level Contributor once equivalent fine-grained roles are confirmed sufficient:\n'
     'Remove-AzRoleAssignment -ObjectId <azure_osi_ai_models-object-id> -RoleDefinitionName "Contributor" -Scope "/subscriptions/<sub-id>/resourceGroups/gipl-slice-ml-india"'),
    ("R10/R12 — Enforce tagging via Azure Policy (audit mode initially)",
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

add_para("End of report.", italic=True)

doc.save("/home/user/sysbi-extension/Azure_Posture_Assessment_Report.docx")
print("Detailed report with named objects generated successfully.")
