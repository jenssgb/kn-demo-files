# Send-MockupCustomerMails.ps1
# Sends 5 realistic mockup customer inquiries FROM kn-demo@M365CPI98544940.onmicrosoft.com
# TO admin@M365CPI98544940.onmicrosoft.com (the K+N service rep inbox).
# Used as setup for DEMO-06B (Cowork Inbox Triage) in the KN Executive AI Showcase.
#
# Topology rule for the showcase:
#   Senden von:                 kn-demo@... (customer persona)
#   Senden an:                  admin@...   (K+N service rep)
#   Approvals in:               admin
#   Customer-facing Outcomes in: kn-demo (the agent replies back to the customer)
#
# Each mail looks like it comes from a different KN customer. Cowork reads the body
# (including the signature block) to identify the customer, the shipment/invoice
# reference, and the requested action.
#
# Run this ONCE on the day of the demo, 2-3 minutes before stage. Re-run will
# duplicate mails - that's fine (just delete the older batch from the inbox).

[CmdletBinding()]
param(
    [string]$TenantId       = '31ed2089-187f-4a44-bc78-04e4569ab25b',
    [string]$ClientId       = '82e36ff4-c78b-4327-b6f0-dcc11b212a78',
    [string]$CertThumbprint = '3065D8C303D949AEFA2F5495F9603E84A5015CAC',
    [string]$From           = 'kn-demo@M365CPI98544940.onmicrosoft.com',
    [string]$To             = 'admin@M365CPI98544940.onmicrosoft.com',
    [switch]$Interactive
)

$ErrorActionPreference = 'Stop'

# --- Connect Graph ----------------------------------------------------------
if (-not (Get-Module Microsoft.Graph.Authentication -ListAvailable)) {
    throw "Microsoft.Graph.Authentication module is missing. Install with: Install-Module Microsoft.Graph -Scope CurrentUser"
}
Import-Module Microsoft.Graph.Authentication -ErrorAction Stop
Import-Module Microsoft.Graph.Users.Actions  -ErrorAction Stop

$certInStore = Get-ChildItem Cert:\CurrentUser\My -ErrorAction SilentlyContinue | Where-Object { $_.Thumbprint -eq $CertThumbprint }
if (-not $Interactive -and $certInStore) {
    Write-Host "Connecting to Graph as app $ClientId (cert auth) ..." -ForegroundColor Cyan
    Connect-MgGraph -TenantId $TenantId -ClientId $ClientId -CertificateThumbprint $CertThumbprint -NoWelcome | Out-Null
} else {
    Write-Host "Cert not in store - falling back to interactive auth. Sign in as $From." -ForegroundColor Yellow
    Connect-MgGraph -TenantId $TenantId -Scopes 'Mail.Send','Mail.Send.Shared' -NoWelcome | Out-Null
    $ctx = Get-MgContext
    if ($ctx.Account -and ($ctx.Account -notlike "$From*")) {
        Write-Host "  Note: signed in as $($ctx.Account) (not $From). Sending will use the signed-in mailbox as From." -ForegroundColor Yellow
        $From = $ctx.Account
    }
}

# --- 5 mockup customer mails ------------------------------------------------
$mails = @(
    @{
        Subject = 'Status update needed — KN-ROAD-20260520-0091 to Hamburg DC'
        Body    = @'
Hi Kuehne+Nagel team,

quick status request on KN-ROAD-20260520-0091 (PO 4500988104, three pallets industrial fasteners, picked up Rotterdam on the 20th).

Could you confirm the current location and the expected delivery window for our Hamburg DC? Our receiving team wants to lock the inbound dock slot for tomorrow morning.

No urgency, just need the latest.

Thanks,
Marta Vogel
Logistics Coordinator
Contoso Industries AG
+49 40 5589 1240
'@
    },
    @{
        Subject = 'Delay on KN-OCEAN-20260512-3344 — what is the new ETA Hamburg?'
        Body    = @'
Hello,

shipment KN-OCEAN-20260512-3344 (40' HC, electronic components, Shanghai -> Hamburg via CMA-CGM) was supposed to arrive on 28 May. Vessel tracking shows it has been sitting outside Rotterdam since the weekend due to port congestion.

This is the second delay this quarter on the China-EU lane. Per our master service agreement (MSA 2025-LITWARE, clause 4.3) we expect proactive ETA updates within 24 hours of a deviation > 48 hours.

I need:
1. confirmed new ETA Hamburg DC
2. root cause statement
3. mitigation for the next two shipments in our pipeline (KN-OCEAN-20260518-3401 and -3402)

Please get back to me today.

Best regards,
Ralf Berger
Head of Supply Chain
Litware Electronics GmbH
+49 89 4477 8821
'@
    },
    @{
        Subject = 'Invoice 2026-INV-44721 — disputed line item (handling fee)'
        Body    = @'
Hi,

we received your invoice 2026-INV-44721 (period: April 2026, total EUR 38,420 net).

Line 14 shows a "special handling surcharge" of EUR 1,180 against shipment KN-AIR-20260418-0876. We never agreed to this in writing and there is no surcharge in our rate card.

Could you either remove the line and reissue the invoice, or send me the written approval / e-mail thread where we agreed to it? Our payment terms are 30 days, so the clock is ticking on the rest of the invoice.

If this needs to go to your finance team, please loop them in directly.

Thanks,
Sandra Östergaard
Accounts Payable Manager
Fabrikam Pharma AB
+46 8 5599 2410
'@
    },
    @{
        Subject = '3 damaged pallets on delivery KN-ROAD-20260522-0214 — photos attached'
        Body    = @'
Hi Kuehne+Nagel team,

we received KN-ROAD-20260522-0214 yesterday morning at our Munich DC. Three of the eight pallets arrived with visible water damage and crushing on the lower layers. Our receiving team documented everything with the driver (delivery note signed under reserve). Photos are attached.

Approximate value of damaged goods: EUR 4,800 net. The two top boxes on pallet 7 are a total loss. We will need either replacement stock or a credit note - whichever is faster.

Could someone from your claims team get in touch today? We have a customer commitment for end of next week.

Thanks,
Lina Bauer
DC Manager Munich
Tailspin Toys Europe GmbH
+49 89 2298 0066
'@
    },
    @{
        Subject = 'Quote request — new lane Singapore -> Dubai (weekly air, 2 t)'
        Body    = @'
Hello Kuehne+Nagel,

we are setting up a new distribution flow into the Middle East and need a quotation for a recurring weekly air shipment from Singapore (SIN) to Dubai (DXB).

Volume:
- ~2,000 kg gross per week, 8 europallets
- mixed consumer electronics (no DGR)
- pickup Singapore Tuesday morning, delivery DXB Free Zone Wednesday EOD
- target start: 22 June 2026, initial 12-week commitment

What we'd like in the quote:
- per-shipment all-in price (pickup, origin handling, airfreight, destination handling, customs, last-mile to FZ)
- transit time SLA and on-time performance commitment
- volume rebate if we extend to 24 weeks
- proposed account manager + escalation path

If you need additional info to price this, just ask. Decision is expected by end of next week.

Best regards,
David Chen
Global Logistics Lead
Wide World Importers Pte Ltd
+65 6589 7720
'@
    }
)

# --- Send each mail ---------------------------------------------------------
$sent = 0
foreach ($m in $mails) {
    $payload = @{
        Message = @{
            Subject      = $m.Subject
            Body         = @{ ContentType = 'Text'; Content = $m.Body }
            ToRecipients = @(@{ EmailAddress = @{ Address = $To } })
        }
        SaveToSentItems = $false
    }
    try {
        Send-MgUserMail -UserId $From -BodyParameter $payload -ErrorAction Stop
        Write-Host "  ✓ sent: $($m.Subject)" -ForegroundColor Green
        $sent++
    } catch {
        Write-Host "  ✗ FAILED: $($m.Subject)" -ForegroundColor Red
        Write-Host "    $($_.Exception.Message)" -ForegroundColor DarkRed
    }
}

Write-Host ""
Write-Host "Done. $sent of $($mails.Count) mockup customer mails delivered to $To." -ForegroundColor Cyan
Write-Host "Open kn-demo's Outlook on KN-Demo-VM to confirm. Then switch to Cowork and run the DEMO-06B prompt." -ForegroundColor Cyan
Disconnect-MgGraph | Out-Null
