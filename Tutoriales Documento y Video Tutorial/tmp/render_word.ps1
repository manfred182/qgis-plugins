[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $InputPath,
    [Parameter(Mandatory = $true)]
    [string] $OutputDir,
    [ValidateRange(72, 300)]
    [int] $Dpi = 150,
    [string] $PopplerPath = 'C:\Users\Jose Castillo Ospina\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe'
)

# Internal visual QA only. The DOCX is opened read-only and is never saved.
# Word exports a unique temporary PDF, Poppler renders page-N.png, then the PDF
# is deleted in finally. Existing Word processes and documents are not closed.
$ErrorActionPreference = 'Stop'
$workspacePath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$qaRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'qa'))
$sourcePath = [System.IO.Path]::GetFullPath($InputPath)
$destinationPath = [System.IO.Path]::GetFullPath($OutputDir)
$comparison = [System.StringComparison]::OrdinalIgnoreCase

function Assert-UnderPath([string] $Candidate, [string] $Root, [string] $Label) {
    $rootPrefix = $Root.TrimEnd('\') + '\'
    if (-not $Candidate.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must stay inside $Root"
    }
}

Assert-UnderPath $sourcePath $workspacePath 'InputPath'
Assert-UnderPath $destinationPath $qaRoot 'OutputDir'
if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "DOCX not found: $sourcePath" }
if ([System.IO.Path]::GetExtension($sourcePath) -ne '.docx') { throw 'InputPath must be a DOCX.' }
if (-not (Test-Path -LiteralPath $PopplerPath -PathType Leaf)) { throw "Poppler not found: $PopplerPath" }

[void](New-Item -ItemType Directory -Path $destinationPath -Force)
if (@(Get-ChildItem -LiteralPath $destinationPath -Filter 'page-*.png' -File).Count -gt 0) {
    throw 'OutputDir already contains page images. Use a new QA directory for each render.'
}
$pdfPath = Join-Path $destinationPath ('word-qa-' + [Guid]::NewGuid().ToString('N') + '.pdf')
$imagePrefix = Join-Path $destinationPath 'page'
$word = $null
$documents = $null
$document = $null
$ownsWordProcess = $false
$pageCount = $null
$wordProcessId = $null
$pidsBefore = @(Get-Process -Name WINWORD -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)

try {
    $word = New-Object -ComObject Word.Application
    $newProcesses = @(Get-Process -Name WINWORD -ErrorAction SilentlyContinue | Where-Object { $pidsBefore -notcontains $_.Id })
    if ($newProcesses.Count -ne 1) {
        throw 'Cannot prove that Word created an independent process. Existing Word instances will not be closed.'
    }
    $wordProcessId = $newProcesses[0].Id
    $ownsWordProcess = $true
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $documents = $word.Documents
    if ($documents.Count -ne 0) { throw 'The new Word instance unexpectedly contains documents.' }
    $document = $documents.Open($sourcePath, $false, $true, $false)
    if (-not $document.ReadOnly) { throw 'Word did not open the DOCX read-only.' }
    $document.Repaginate()
    $pageCount = [int] $document.ComputeStatistics(2)
    $document.ExportAsFixedFormat($pdfPath, 17)
    if (-not (Test-Path -LiteralPath $pdfPath -PathType Leaf)) { throw 'Word did not produce the internal QA PDF.' }

    & $PopplerPath '-r' "$Dpi" '-png' $pdfPath $imagePrefix
    if ($LASTEXITCODE -ne 0) { throw "Poppler exited with code $LASTEXITCODE." }
    $pageFiles = @(Get-ChildItem -LiteralPath $destinationPath -Filter 'page-*.png' -File)
    if ($pageFiles.Count -ne $pageCount) {
        throw "Page count mismatch: Word reports $pageCount, Poppler produced $($pageFiles.Count)."
    }
    # Poppler pads page numbers. Normalize names to the DOCX skill convention.
    foreach ($pageFile in $pageFiles) {
        if ($pageFile.BaseName -match '^page-(\d+)$') {
            $pageNumber = [int] $Matches[1]
            $normalizedName = "page-$pageNumber.png"
            if ($pageFile.Name -ne $normalizedName) {
                Rename-Item -LiteralPath $pageFile.FullName -NewName $normalizedName
            }
        }
    }
    [PSCustomObject]@{
        Source = $sourcePath
        OutputDir = $destinationPath
        Pages = $pageCount
        Dpi = $Dpi
        WordProcessId = $wordProcessId
        PdfRetained = $false
    } | ConvertTo-Json
}
finally {
    if ($null -ne $document) {
        try { $document.Close(0) } catch { Write-Warning "Could not close the QA document: $_" }
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)
    }
    if ($null -ne $documents) {
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($documents)
    }
    if ($null -ne $word) {
        if ($ownsWordProcess) {
            try { $word.Quit(0) } catch { Write-Warning "Could not quit the independent QA Word instance: $_" }
        }
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
    if (Test-Path -LiteralPath $pdfPath -PathType Leaf) {
        Assert-UnderPath ([System.IO.Path]::GetFullPath($pdfPath)) $qaRoot 'Temporary PDF'
        Remove-Item -LiteralPath $pdfPath -Force
    }
}
