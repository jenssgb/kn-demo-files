# KN Demo Files

Public mirror of Demo-Files for the KN Executive AI Showcase briefing.
Auto-published by `Scripts/Update-KNBriefing.ps1` in the allinone-demo-workspace.

## One-line deploy on any demo VM (paste into PowerShell)

```powershell
$d=[Environment]::GetFolderPath('Desktop');$z="$env:TEMP\knd.zip";iwr 'https://github.com/jenssgb/kn-demo-files/archive/refs/heads/main.zip' -OutFile $z;ri "$d\Demo-Files" -r -fo -ea 0;Expand-Archive $z "$env:TEMP\knd" -Force;mv "$env:TEMP\knd\kn-demo-files-main" "$d\Demo-Files";ri $z,"$env:TEMP\knd" -r -fo
```

Result: `%USERPROFILE%\Desktop\Demo-Files\` (overwrites any previous copy).

