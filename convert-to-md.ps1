# ---------------------------------------------------
# ファイルパス設定
$sourceRoot = 'E:\実務で使う\消費者・債務整理'
$vaultRoot  = 'E:\LegalVault\消費者・債務整理'

# Pandoc のパス（必要に応じてフルパスに）
$pandoc = "$env:LOCALAPPDATA\\Pandoc\\pandoc.exe"

#-----------------------------------------------------------------------
# YAML Frontmatter Generation Function and Global Variables
#-----------------------------------------------------------------------

# Define Global Stop Words (customize as needed)
$global:stopWords = @(
    "a", "an", "the", "is", "of", "and", "to", "in", "it", "for", "with", "on", "at", "by",
    "this", "that", "these", "those", "then", "than",
    "document", "file", "item", "version", "report", "memo", "draft", "final",
    "internal", "external", "confidential", "public",
    "copy", "untitled", "new",
    "v", "ver", "rev", # Common version prefixes
    "の", "と", "について", "資料", "報告書", "マニュアル", "pdf", "docx", "temp", "image", "page", "ocr", "combined", "txt" # Japanese stop words
)

function New-DocumentFrontMatter {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [System.IO.FileInfo]$SourceFile,

        [Parameter(Mandatory = $true)]
        [string]$SourceRoot,

        [Parameter(Mandatory = $true)]
        [string]$ConversionStrategy,

        [string]$TitleOverride = "",
        [string[]]$AdditionalGlobalTags = @(), # Can be passed from script config
        [int]$MinTagLength = 2,
        [string]$DefaultCategory = "general"
    )

    # --- Determine Title ---
    $title = $TitleOverride
    if ([string]::IsNullOrWhiteSpace($title)) {
        $baseNameForTitle = [System.IO.Path]::GetFileNameWithoutExtension($SourceFile.Name)
        # Remove common bracketed prefixes (non-greedy) and trim
        $title = ($baseNameForTitle -replace "^【.*?】\\s*" -replace "^「.*?」\\s*" -replace "^\\(.*?\\)\\s*").Trim()
        # Optional: Replace underscores/hyphens with spaces for a cleaner title
        # $title = $title -replace '[_-]', ' '
    }

    # --- Generate Category ---
    $categoryPath = $SourceFile.DirectoryName
    $category = $DefaultCategory
    if ($categoryPath.StartsWith($SourceRoot, [System.StringComparison]::OrdinalIgnoreCase) -and $categoryPath.Length -gt $SourceRoot.Length) {
        $relativeDirPath = $categoryPath.Substring($SourceRoot.Length).TrimStart('\\/')
        if (-not [string]::IsNullOrWhiteSpace($relativeDirPath)) {
            $category = $relativeDirPath -replace '\\\\', '/'
        }
    }

    # --- Generate Tags ---
    $tagsList = [System.Collections.Generic.List[string]]::new()
    $tagsList.AddRange($AdditionalGlobalTags)

    # 1. From Directory Path (Category Path)
    if ($category -ne $DefaultCategory) {
        $category.Split('/') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $tagsList.Add($_) }
    }

    # 2. From Filename
    $baseNameForTags = [System.IO.Path]::GetFileNameWithoutExtension($SourceFile.Name)
    # Extract from bracketed content (non-greedy for 【】, 「」, ())
    [regex]::Matches($baseNameForTags, "(?<=\\【).*?(?=\\】)|(?<=\\「).*?(?=\\」)|(?<=\\().*?(?=\\))") |
        ForEach-Object { $_.Value.Split(' ', '_', '-') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $tagsList.Add($_) } }

    $cleanedBaseNameForTags = $baseNameForTags -replace "【.*?】" -replace "「.*?」" -replace "\\(.*?\\)"
    $cleanedBaseNameForTags -split '[_\\s-]+' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $tagsList.Add($_) }

    $processedTags = $tagsList |
        ForEach-Object { $_.Trim().ToLowerInvariant() } |
        Where-Object { (-not [string]::IsNullOrWhiteSpace($_)) -and ($_.Length -ge $MinTagLength) } |
        Where-Object { $_ -notin $global:stopWords } |
        Where-Object { $_ -notmatch '^\\d+$' } | # Exclude purely numeric tags
        Select-Object -Unique

    # --- Extract Version (Example) ---
    $fileVersion = "" # Renamed to avoid conflict with $version parameter if it existed
    $versionMatch = [regex]::Match($baseNameForTags, '(?i)[_-]?(v(?:er(?:sion)?)?[\\s._-]?\\d+(\\.\\d+)*([._-]?[a-zA-Z_0-9-]+)?)')
    if ($versionMatch.Success) {
        $fileVersion = $versionMatch.Groups[1].Value.Trim('._- ')
    }

    # --- Construct YAML Frontmatter String ---
    $yamlBuilder = [System.Text.StringBuilder]::new()
    $yamlBuilder.AppendLine("---")
    $yamlBuilder.AppendLine("source_file: ""$($SourceFile.FullName -replace '\\\\', '/')""")
    $yamlBuilder.AppendLine("source_type: ""$($SourceFile.Extension.TrimStart('.').ToUpper())""")
    $yamlBuilder.AppendLine("conversion_date: ""$(Get-Date -Format 'yyyy-MM-ddTHH:mm:sszzz')""")
    $yamlBuilder.AppendLine("conversion_strategy: ""$ConversionStrategy""")
    $yamlBuilder.AppendLine("original_modified_date: ""$($SourceFile.LastWriteTime.ToString('yyyy-MM-ddTHH:mm:sszzz'))""")
    $yamlBuilder.AppendLine("title: ""$($title -replace '""', '""""')""") # Escape double quotes
    $yamlBuilder.AppendLine("category: ""$category""")
    if ($processedTags.Count -gt 0) {
        $yamlBuilder.AppendLine("tags:")
        $processedTags | ForEach-Object { $yamlBuilder.AppendLine("  - ""$_""") }
    } else {
        $yamlBuilder.AppendLine("tags: []")
    }
    if (-not [string]::IsNullOrWhiteSpace($fileVersion)) {
        $yamlBuilder.AppendLine("version: ""$fileVersion""")
    }
    # Add other fields as needed
    $yamlBuilder.AppendLine("---")

    return $yamlBuilder.ToString()
} # End of New-DocumentFrontMatter

#-----------------------------------------------------------------------
# Pandoc Invocation Helper Function
#-----------------------------------------------------------------------
function Invoke-PandocToVariable {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [System.Collections.Generic.List[string]]$LogList
    )

    # Access the $pandoc variable defined at the script scope
    $pandocExeToUse = $script:pandoc

    if (-not (Test-Path $pandocExeToUse -PathType Leaf)) {
        $LogList.Add("  CRITICAL ERROR: Pandoc executable not found or is not a file at '$pandocExeToUse'. Please check the `$pandoc variable at the top of the script.")
        Write-Error "Pandoc executable not found at '$pandocExeToUse'. Cannot proceed with Pandoc conversion."
        throw "Pandoc executable not found at '$pandocExeToUse'."
    }

    $joinedArgsForLog = $Arguments -join " "
    # Ensure the executable path is quoted if it contains spaces.
    $commandToLog = """$pandocExeToUse"" $joinedArgsForLog" 
    $LogList.Add("  Executing Pandoc: $commandToLog")

    $processOutput = ""
    $processError = ""
    $exitCode = -1 
    
    $tempOutputFile = $null
    $tempErrorFile = $null

    try {
        $tempOutputFile = New-TemporaryFile
        $tempErrorFile = New-TemporaryFile
        
        # Arguments should be an array of strings. Quoting for arguments with spaces should be handled
        # when $Arguments array is constructed by the caller.
        $process = Start-Process -FilePath $pandocExeToUse -ArgumentList $Arguments -PassThru -Wait -NoNewWindow -RedirectStandardOutput $tempOutputFile.FullName -RedirectStandardError $tempErrorFile.FullName -ErrorAction Stop
        
        $exitCode = $process.ExitCode
        
        $processOutput = Get-Content -Path $tempOutputFile.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        $processError = Get-Content -Path $tempErrorFile.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    }
    catch {
        $LogList.Add("  Pandoc execution with Start-Process failed: $($_.Exception.ToString())")
        Write-Warning "    Pandoc execution with Start-Process failed: $($_.Exception.Message)"
        if ($tempOutputFile -and (Test-Path $tempOutputFile.FullName -ErrorAction SilentlyContinue)) {
             $outputContentForLog = Get-Content -Path $tempOutputFile.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
             if(-not [string]::IsNullOrWhiteSpace($outputContentForLog)) {$LogList.Add("  Partial Stdout (Start-Process exception): $outputContentForLog")}
        }
        if ($tempErrorFile -and (Test-Path $tempErrorFile.FullName -ErrorAction SilentlyContinue)) {
            $errorContentForLog = Get-Content -Path $tempErrorFile.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
            if(-not [string]::IsNullOrWhiteSpace($errorContentForLog)) {$LogList.Add("  Partial Stderr (Start-Process exception): $errorContentForLog")}
        }
        throw # Re-throw the exception so the caller's try-catch can handle it.
    } 
    finally { 
        if ($tempOutputFile -and (Test-Path $tempOutputFile.FullName -ErrorAction SilentlyContinue)) { Remove-Item $tempOutputFile.FullName -Force -ErrorAction SilentlyContinue }
        if ($tempErrorFile -and (Test-Path $tempErrorFile.FullName -ErrorAction SilentlyContinue)) { Remove-Item $tempErrorFile.FullName -Force -ErrorAction SilentlyContinue }
    }

    if ($exitCode -ne 0) {
        $LogList.Add("  Pandoc exited with code $exitCode.")
        if (-not [string]::IsNullOrWhiteSpace($processError)) {
            $LogList.Add("  Pandoc Stderr: $processError")
        } 
        if (-not [string]::IsNullOrWhiteSpace($processOutput)) {
            # Log stdout even on error, as it might contain clues
            $LogList.Add("  Pandoc Stdout (on error exit code $exitCode): $processOutput")
        }
        return "" # Return empty string for non-zero exit code
    }

    # Log stderr even on success, as Pandoc might output warnings
    if (-not [string]::IsNullOrWhiteSpace($processError)) {
        $LogList.Add("  Pandoc Stderr (warnings/info on success): $processError")
    }
    
    return $processOutput
}

#-----------------------------------------------------------------------
# Main File Processing Loop
#-----------------------------------------------------------------------
Get-ChildItem -Path $sourceRoot -Recurse -File |
    Where-Object { $_.Extension -in '.docx','.pdf' } |
    ForEach-Object {
        $currentFile = $_ 
        $srcFile = $currentFile.FullName
        $relPath = $srcFile.Substring($sourceRoot.Length).TrimStart('\\')
        $outDir  = Join-Path $vaultRoot (Split-Path $relPath -Parent)
        $outFile = Join-Path $outDir ([IO.Path]::GetFileNameWithoutExtension($relPath) + '.md')

        if (!(Test-Path $outDir)) {
            New-Item -ItemType Directory -Path $outDir -Force | Out-Null
        }

        $markdownBodyContent = ""
        $bodyGeneratedSuccessfully = $false 
        $currentConversionStrategy = "" 
        $conversionLogs = [System.Collections.Generic.List[string]]::new() 
        $conversionLogs.Add("Processing file: $($currentFile.FullName)")

        switch ($currentFile.Extension.ToLower()) {
            '.docx' {
                Write-Host "Processing DOCX: $($currentFile.Name)"
                $conversionLogs.Add("Attempting DOCX to Markdown conversion (DirectPandoc-DOCX)")
                $currentConversionStrategy = "DirectPandoc-DOCX"
                
                $mediaDir = Join-Path $outDir 'media' 
                if (!(Test-Path $mediaDir)) {
                    New-Item -ItemType Directory -Path $mediaDir -Force | Out-Null
                }
                try {
                    $pandocArgsDocx = @(
                        "`"$srcFile`"",
                        "-t", "markdown",
                        "--wrap=preserve",
                        "--extract-media=`"$mediaDir`""
                    )
                    $markdownBodyContent = Invoke-PandocToVariable -Arguments $pandocArgsDocx -LogList $conversionLogs
                    
                    if (-not [string]::IsNullOrWhiteSpace($markdownBodyContent)) {
                        $conversionLogs.Add("DOCX to Markdown conversion successful.")
                        Write-Host "  DOCX to Markdown conversion successful."
                        $bodyGeneratedSuccessfully = $true
                    } else {
                        $conversionLogs.Add("Pandoc conversion for DOCX '$($currentFile.Name)' resulted in empty content or failed (check logs from Invoke-PandocToVariable).")
                        Write-Warning "  Pandoc conversion for DOCX '$($currentFile.Name)' resulted in empty content or failed."
                    }
                } catch {
                    $conversionLogs.Add("Error during Pandoc conversion for DOCX '$($currentFile.Name)': $($_.Exception.Message)")
                    Write-Warning "  Error during Pandoc conversion for DOCX '$($currentFile.Name)': $($_.Exception.Message)"
                }
            } # End .docx
            
            '.pdf' {
                Write-Host "Processing PDF: $($currentFile.Name)"
                $conversionLogs.Add("Starting PDF processing attempts for '$($currentFile.Name)'.")

                # --- Attempt 1: Pandoc direct PDF to Markdown ---
                Write-Host "  [Attempt 1/3] Trying Pandoc direct PDF to Markdown..."
                $conversionLogs.Add("[PDF Attempt 1/3] Trying Pandoc direct PDF to Markdown...")
                $tempStrategy1 = "PandocDirect-PDF"
                try {
                    $pandocArgsPdfDirect = @(
                        "`"$srcFile`"",
                        "-t", "markdown",
                        "--wrap=preserve"
                    )
                    $tempBody1 = Invoke-PandocToVariable -Arguments $pandocArgsPdfDirect -LogList $conversionLogs
                    
                    if (-not [string]::IsNullOrWhiteSpace($tempBody1)) {
                        $conversionLogs.Add("  Pandoc direct PDF conversion successful.")
                        Write-Host "    Pandoc direct PDF conversion successful."
                        $markdownBodyContent = $tempBody1
                        $currentConversionStrategy = $tempStrategy1
                        $bodyGeneratedSuccessfully = $true
                    } else {
                        $conversionLogs.Add("  Pandoc direct PDF conversion failed or produced empty content (check logs from Invoke-PandocToVariable for details).")
                        Write-Warning "    Pandoc direct PDF conversion failed or produced empty content for '$($currentFile.Name)'."
                    }
                } catch {
                    $conversionLogs.Add("  Pandoc direct PDF conversion failed with exception: $($_.Exception.Message)")
                    Write-Warning "    Pandoc direct PDF conversion failed for '$($currentFile.Name)': $($_.Exception.Message)"
                }

                Write-Host "DEBUG: PDF - After Attempt 1. bodyGeneratedSuccessfully = $bodyGeneratedSuccessfully" # <-- ADDED THIS LINE

                # --- Attempt 2: pdftotext + Pandoc ---
                if (-not $bodyGeneratedSuccessfully) {
                    Write-Host "  [Attempt 2/3] Trying pdftotext + Pandoc..."
                    $conversionLogs.Add("[PDF Attempt 2/3] Trying pdftotext + Pandoc...")
                    $tempStrategy2 = "PdfToText-Pandoc-PDF"
                    $tempTextFileFromPdfToText = Join-Path $env:TEMP ($currentFile.BaseName + '_pdftotext_' + (New-Guid).ToString().Substring(0,8) + '.txt')
                    
                    $pdfToTextCmdSuccess = $false
                    try {
                        $cmdPdftotext = "pdftotext -layout -enc UTF-8 `"$srcFile`" `"$tempTextFileFromPdfToText`""
                        $conversionLogs.Add("  Executing pdftotext: $cmdPdftotext")
                        Invoke-Expression $cmdPdftotext -ErrorVariable pdfToTextErrVar -OutVariable pdfToTextOutVar | Out-Null
                        
                        if ($pdfToTextErrVar) {
                            $conversionLogs.Add("  pdftotext command reported an error: $($pdfToTextErrVar | Out-String)")
                            throw ($pdfToTextErrVar | Out-String) 
                        }
                        # Check $? for non-terminating errors from external commands
                        if (-not $?) {
                            $conversionLogs.Add("  pdftotext command failed (exit code might be non-zero or other issue). Output: $pdfToTextOutVar")
                            # Consider throwing an error here if $? is false and $pdfToTextErrVar was not populated
                            # For now, we'll rely on the Test-Path and file length check below.
                        }

                        if (Test-Path $tempTextFileFromPdfToText -PathType Leaf) {
                            if ((Get-Item $tempTextFileFromPdfToText).Length -gt 0) {
                                $conversionLogs.Add("  pdftotext extraction successful. File: $tempTextFileFromPdfToText")
                                Write-Host "    pdftotext extraction successful."
                                $pdfToTextCmdSuccess = $true
                            } else {
                                $conversionLogs.Add("  pdftotext extracted an empty text file: $tempTextFileFromPdfToText")
                                Write-Warning "    pdftotext extracted an empty text file for '$($currentFile.Name)'."
                            }
                        } else {
                            $conversionLogs.Add("  pdftotext did not produce an output file. Expected: $tempTextFileFromPdfToText. pdftotext stdout: $pdfToTextOutVar")
                            Write-Warning "    pdftotext did not produce an output file for '$($currentFile.Name)'."
                        }
                    } catch {
                        $conversionLogs.Add("  pdftotext execution failed with exception: $($_.Exception.Message)")
                        Write-Warning "    pdftotext execution failed for '$($currentFile.Name)': $($_.Exception.Message)"
                    } finally { # This finally is for the try block of pdftotext execution
                        if (Test-Path $tempTextFileFromPdfToText) { Remove-Item $tempTextFileFromPdfToText -Force -ErrorAction SilentlyContinue }
                    }

                    if ($pdfToTextCmdSuccess) {
                        $conversionLogs.Add("    Converting text from pdftotext to Markdown using Pandoc...")
                        $pandocArgsFromText = @(
                            "`"$tempTextFileFromPdfToText`"",
                            "-f", "plain_text",
                            "-t", "markdown",
                            "--wrap=preserve"
                        )
                        $tempBody2 = Invoke-PandocToVariable -Arguments $pandocArgsFromText -LogList $conversionLogs
                        if (-not [string]::IsNullOrWhiteSpace($tempBody2)) {
                            $conversionLogs.Add("  Pandoc conversion from pdftotext output successful.")
                            Write-Host "    pdftotext + Pandoc conversion successful."
                            $markdownBodyContent = $tempBody2
                            $currentConversionStrategy = $tempStrategy2
                            $bodyGeneratedSuccessfully = $true
                        } else {
                            $conversionLogs.Add("  Pandoc conversion from pdftotext output failed or produced empty file (check logs from Invoke-PandocToVariable for details).")
                            Write-Warning "    Pandoc conversion from pdftotext output failed or produced empty content for '$($currentFile.Name)'."
                        }
                    }
                } # End of "if (-not $bodyGeneratedSuccessfully)" for Attempt 2

                Write-Host "DEBUG: PDF - After Attempt 2. bodyGeneratedSuccessfully = $bodyGeneratedSuccessfully" # <-- ADDED THIS LINE

                # --- Attempt 3: pdftoppm + Tesseract OCR + Pandoc ---
                if (-not $bodyGeneratedSuccessfully) {
                    Write-Host "  [Attempt 3/3] Trying pdftoppm + Tesseract OCR + Pandoc..."
                    $conversionLogs.Add("[PDF Attempt 3/3] Trying OCR (pdftoppm + Tesseract + Pandoc)...")
                    $tempStrategy3 = "OCR-Tesseract-Pandoc-PDF"
                    
                    $tempSubDirName = "temp_images_" + $currentFile.BaseName + "_" + (New-Guid).ToString().Substring(0,8)
                    $tempImageDir = Join-Path $env:TEMP $tempSubDirName 
                    $combinedOcrTextFile = Join-Path $env:TEMP ($currentFile.BaseName + '_ocr_combined_' + (New-Guid).ToString().Substring(0,8) + '.txt')

                    $ocrPipelineSuccessForCleanup = $false 
                    try {
                        if (Test-Path $tempImageDir) { Remove-Item $tempImageDir -Recurse -Force -ErrorAction SilentlyContinue }
                        New-Item -ItemType Directory -Path $tempImageDir -Force -ErrorAction SilentlyContinue | Out-Null
                        if (Test-Path $combinedOcrTextFile) { Remove-Item $combinedOcrTextFile -Force -ErrorAction SilentlyContinue }

                        $imageFileBaseNameForPpm = "page" 
                        $imageFilePrefixForPpm = Join-Path $tempImageDir $imageFileBaseNameForPpm
                        
                        $conversionLogs.Add("  [OCR 1/3] Converting PDF to images (pdftoppm)...")
                        Write-Host "    [OCR 1/3] Converting PDF to images (pdftoppm)..."
                        
                        $ppmStdOut = ''
                        $ppmStdErr = ''
                        $ppmProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
                        $ppmProcessInfo.FileName = "pdftoppm" 
                        $ppmProcessInfo.Arguments = "-png -r 300 `"$srcFile`" `"$imageFilePrefixForPpm`""
                        $ppmProcessInfo.RedirectStandardOutput = $true
                        $ppmProcessInfo.RedirectStandardError = $true
                        $ppmProcessInfo.UseShellExecute = $false
                        $ppmProcessInfo.CreateNoWindow = $true
                        $ppmProcessInfo.StandardOutputEncoding = [System.Text.Encoding]::UTF8 
                        $ppmProcessInfo.StandardErrorEncoding = [System.Text.Encoding]::UTF8

                        $conversionLogs.Add("    Executing pdftoppm: $($ppmProcessInfo.FileName) $($ppmProcessInfo.Arguments)")
                        $ppmProcess = New-Object System.Diagnostics.Process
                        $ppmProcess.StartInfo = $ppmProcessInfo
                        $ppmProcess.Start() | Out-Null
                        $ppmStdOut = $ppmProcess.StandardOutput.ReadToEnd()
                        $ppmStdErr = $ppmProcess.StandardError.ReadToEnd()
                        $ppmProcess.WaitForExit()

                        if (-not [string]::IsNullOrWhiteSpace($ppmStdErr)) {
                            $conversionLogs.Add("    pdftoppm stderr: $ppmStdErr")
                            if ($ppmStdErr -match "Syntax Error|Cannot find font|Error opening|Failed to load|No display font") {
                                $conversionLogs.Add("    WARNING: pdftoppm reported critical errors that might compromise images: $ppmStdErr")
                                Write-Warning "  CAUTION: pdftoppm for '$($currentFile.Name)' reported critical errors. Images might be unusable for OCR."
                            }
                        }
                        if (-not [string]::IsNullOrWhiteSpace($ppmStdOut)) { $conversionLogs.Add("    pdftoppm stdout: $ppmStdOut") }

                        if ($ppmProcess.ExitCode -ne 0) {
                            throw "pdftoppm exited with code $($ppmProcess.ExitCode). Review logs for stderr details." 
                        }
                        $generatedImageFiles = Get-ChildItem -Path $tempImageDir -Filter "*.png" -ErrorAction SilentlyContinue
                        if ($generatedImageFiles.Count -eq 0) {
                            throw "pdftoppm ran (ExitCode 0) but no images were generated. Review logs for stderr details." 
                        }
                        $conversionLogs.Add("    pdftoppm conversion to images successful. Found $($generatedImageFiles.Count) images.")
                        Write-Host "      pdftoppm conversion to images successful."

                        $conversionLogs.Add("  [OCR 2/3] Running OCR on images (Tesseract)...")
                        Write-Host "    [OCR 2/3] Running OCR on images (Tesseract)..."
                        
                        $imageFiles = $generatedImageFiles |
                            Select-Object *, @{Name='PageNumber';Expression={
                                $numStr = ''
                                if ($_.BaseName -match "^${imageFileBaseNameForPpm}[-_.](\\d+)$") { $numStr = $matches[1] }
                                elseif ($_.BaseName -match "^${imageFileBaseNameForPpm}(\\d+)$") { $numStr = $matches[1] } 
                                elseif ($_.BaseName -match "(\\d+)$") { $numStr = $matches[1] }
                                if (-not [string]::IsNullOrWhiteSpace($numStr)) { try { [int]$numStr } catch { $script:conversionLogs.Add("    WARNING: Unparseable page number string '$numStr' from file '$($_.BaseName)'. Assigning -1."); -1 } }
                                else { $script:conversionLogs.Add("    WARNING: Could not extract page number from file '$($_.BaseName)'. Assigning -1."); -1 }
                            }} | Where-Object {$_.PageNumber -ne -1} | Sort-Object PageNumber
                        
                        if ($imageFiles.Count -eq 0) { throw "No images with parseable page numbers found for OCR after pdftoppm. Check image filenames and parsing logic." }
                        $conversionLogs.Add("    Found $($imageFiles.Count) images with parseable page numbers for OCR.")

                        foreach ($imageFileObj in $imageFiles) {
                            $imageFullPath = $imageFileObj.FullName
                            $tesseractCmd = "tesseract `"$imageFullPath`" stdout -l jpn" 
                            $conversionLogs.Add("    Executing Tesseract for $($imageFileObj.Name) (Page: $($imageFileObj.PageNumber)): $tesseractCmd")
                            $ocrPageText = ""; $tessErr = ""
                            try {
                                $ocrPageText = Invoke-Expression $tesseractCmd -ErrorVariable mTessErr -ErrorAction SilentlyContinue 
                                if ($mTessErr) { $tessErr = ($mTessErr | Out-String).Trim() }
                                if ($LASTEXITCODE -ne 0 -and [string]::IsNullOrWhiteSpace($tessErr)) { $tessErr = "Tesseract exited with code $LASTEXITCODE."}
                                if (-not $?) { # Double check $? if Invoke-Expression was used for an external command
                                    if ([string]::IsNullOrWhiteSpace($tessErr)) { $tessErr = "Tesseract command failed (checked via `$?)." }
                                    else { $tessErr += " (Also, Tesseract command failed via `$?.)"} # Corrected: removed extra ')' from string
                                }
                            } catch { $tessErr = "Exception during Tesseract for $($imageFileObj.Name): $($_.Exception.Message)"}
                            if (-not [string]::IsNullOrWhiteSpace($tessErr)) { $conversionLogs.Add("    Tesseract error for $($imageFileObj.Name): $tessErr") }
                            if (-not [string]::IsNullOrWhiteSpace($ocrPageText)) { Add-Content -Path $combinedOcrTextFile -Value $ocrPageText.Trim(); Add-Content -Path $combinedOcrTextFile -Value ([System.Environment]::NewLine) }
                            else { $conversionLogs.Add("    Tesseract produced no text output for $($imageFileObj.Name).") }
                        } 
                        $conversionLogs.Add("    Tesseract OCR processing complete.")
                        Write-Host "      Tesseract OCR processing complete."


                        $conversionLogs.Add("  [OCR 3/3] Converting combined OCR text to Markdown (Pandoc)...")
                        Write-Host "    [OCR 3/3] Converting combined OCR text to Markdown (Pandoc)..."
                        if (Test-Path $combinedOcrTextFile -PathType Leaf) {
                            if ((Get-Item $combinedOcrTextFile).Length -gt 0) {
                                $pandocArgsOcr = @(
                                    "`"$combinedOcrTextFile`"",
                                    "-f", "plain_text", 
                                    "-t", "markdown",
                                    "--wrap=preserve"
                                )
                                $tempBody3 = Invoke-PandocToVariable -Arguments $pandocArgsOcr -LogList $conversionLogs
                                if (-not [string]::IsNullOrWhiteSpace($tempBody3)) {
                                    $conversionLogs.Add("  Pandoc from OCR text successful.")
                                    Write-Host "      pdftoppm + OCR + Pandoc conversion successful."
                                    $markdownBodyContent = $tempBody3
                                    $currentConversionStrategy = $tempStrategy3
                                    $bodyGeneratedSuccessfully = $true
                                    $ocrPipelineSuccessForCleanup = $true 
                                } else {
                                    $conversionLogs.Add("  Pandoc from OCR text failed or produced empty file (check logs from Invoke-PandocToVariable for details).")
                                    Write-Warning "      Pandoc from OCR text failed or produced empty content for '$($currentFile.Name)'."
                                }
                            } else {
                                $conversionLogs.Add("  Combined OCR text file is empty. Skipping Pandoc.")
                                Write-Warning "      Combined OCR text file is empty for '$($currentFile.Name)'. Skipping Pandoc."
                            }
                        } else {
                            $conversionLogs.Add("  Combined OCR text file not found. Skipping Pandoc.")
                            Write-Warning "      Combined OCR text file not found for '$($currentFile.Name)'. Skipping Pandoc."
                        }
                    } catch {
                        $conversionLogs.Add("  OCR Pipeline failed for '$($currentFile.Name)': $($_.Exception.Message)")
                        Write-Warning "    pdftoppm + OCR + Pandoc overall process failed for '$($currentFile.Name)': $($_.Exception.Message)"
                        if ($ppmStdErr) { $conversionLogs.Add("    pdftoppm stderr during OCR pipeline failure: $ppmStdErr") } 
                    } finally {
                        if (Test-Path $tempImageDir) { Remove-Item $tempImageDir -Recurse -Force -ErrorAction SilentlyContinue }
                        if (Test-Path $combinedOcrTextFile) {
                             if ($ocrPipelineSuccessForCleanup -or (Get-Item $combinedOcrTextFile -ErrorAction SilentlyContinue).Length -eq 0) {
                                Remove-Item $combinedOcrTextFile -Force -ErrorAction SilentlyContinue
                            } else {
                                $conversionLogs.Add("  Keeping non-empty combined OCR text file for review: $combinedOcrTextFile")
                                Write-Warning "    Keeping non-empty combined OCR text file for review: $combinedOcrTextFile"
                            }
                        }
                    }
                } # End Attempt 3

                if (-not $bodyGeneratedSuccessfully) {
                    $conversionLogs.Add("Failed to convert PDF '$($currentFile.Name)' to Markdown after all attempts.")
                    Write-Error "  Failed to convert PDF '$($currentFile.Name)' to Markdown after all attempts. Check conversion logs for details."
                }
            } # End .pdf
            Default {
                $conversionLogs.Add("Skipping file with unhandled extension: $($currentFile.Name)")
                Write-Warning "Skipping file with unhandled extension: $($currentFile.Name)"
            }
        } # End switch

        # --- Finalize and Write Output ---
        if ($bodyGeneratedSuccessfully -and (-not [string]::IsNullOrWhiteSpace($markdownBodyContent))) {
            try {
                $frontMatter = New-DocumentFrontMatter -SourceFile $currentFile -SourceRoot $sourceRoot -ConversionStrategy $currentConversionStrategy
                $finalMarkdownOutput = $frontMatter + [System.Environment]::NewLine + $markdownBodyContent
                
                Set-Content -Path $outFile -Value $finalMarkdownOutput -Encoding UTF8
                $conversionLogs.Add("Successfully Converted and Saved: $($currentFile.Name) -> $outFile (Strategy: $currentConversionStrategy)")
                Write-Host "Successfully Converted and Saved: $($currentFile.Name) -> $outFile (Strategy: $currentConversionStrategy)"
            } catch {
                $conversionLogs.Add("Error generating frontmatter or writing final file for '$($currentFile.Name)': $($_.Exception.Message)")
                Write-Error "Error generating frontmatter or writing final file for $($currentFile.Name): $($_.Exception.Message)"
                if (Test-Path $outFile) { Remove-Item $outFile -Force -ErrorAction SilentlyContinue } 
            }
        } elseif ($bodyGeneratedSuccessfully -and [string]::IsNullOrWhiteSpace($markdownBodyContent)) {
            $conversionLogs.Add("Conversion for '$($currentFile.Name)' reported success (Strategy: $currentConversionStrategy), but Markdown body is empty. Output file not created.")
            Write-Warning "Conversion for '$($currentFile.Name)' reported success (Strategy: $currentConversionStrategy), but Markdown body is empty. Output file not created."
            if (Test-Path $outFile) { Remove-Item $outFile -Force -ErrorAction SilentlyContinue }
        } elseif (-not $bodyGeneratedSuccessfully) {
            # $conversionLogs already contains details of failures from attempts.
            Write-Warning "Failed to convert '$($currentFile.Name)' (Last attempted strategy: $currentConversionStrategy). Output file not created. Check logs for details."
            if (Test-Path $outFile) { Remove-Item $outFile -Force -ErrorAction SilentlyContinue } 
        }

        # Optional: Persist $conversionLogs to a file per processed document
        # $logFilePerDocument = Join-Path $outDir ($currentFile.BaseName + "_conversion_log.txt")
        # try {
        #     Set-Content -Path $logFilePerDocument -Value ($conversionLogs -join [System.Environment]::NewLine) -Encoding UTF8
        # } catch {
        #     Write-Warning "Failed to write detailed log for $($currentFile.Name) to $logFilePerDocument: $($_.Exception.Message)"
        # }

    } # End ForEach-Object

# ... (rest of the script, e.g., PATH update logic if any)