#requires -Version 7.0
<#
.SYNOPSIS
Configure the running, local StoryWalk QwenPaw instance without model calls.
.DESCRIPTION
Default: import repository Skills, mount missing copies, preserve edited copies.
Use -UpdateExistingSkills to back up and refresh existing project SKILL.md files.
Use -VerifyOnly for read-only verification, including repository content parity.
Backups stay under the discovered QwenPaw directory, never in this repository.
#>
[CmdletBinding()]
param(
    [string] $BaseUrl = $env:QWENPAW_BASE_URL,
    [switch] $UpdateExistingSkills,
    [switch] $VerifyOnly,
    [hashtable] $Headers = @{}
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$BaseUrl = if ($BaseUrl) { $BaseUrl.Trim().TrimEnd('/') } else { 'http://127.0.0.1:8088' }
$endpoint = [uri] $BaseUrl
if (-not $endpoint.IsAbsoluteUri -or -not $endpoint.IsLoopback -or
    $endpoint.Scheme -notin @('http', 'https') -or $endpoint.AbsolutePath -ne '/' -or
    $endpoint.UserInfo -or $endpoint.Query -or $endpoint.Fragment) {
    throw 'BaseUrl must be a local QwenPaw origin, for example http://127.0.0.1:8088.'
}
if ($VerifyOnly -and $UpdateExistingSkills) {
    throw 'Use either -VerifyOnly or -UpdateExistingSkills, not both.'
}

function Invoke-QwenPawApi {
    param([string] $Path, [string] $Method = 'Get', $Body, [string] $AgentId)
    $requestHeaders = @{} + $Headers
    if ($AgentId) { $requestHeaders['X-Agent-Id'] = $AgentId }
    $request = @{
        Uri = "$BaseUrl/api/$Path"; Method = $Method; Headers = $requestHeaders
        TimeoutSec = 60; MaximumRedirection = 0; Verbose = $false; Debug = $false
    }
    if ($null -ne $Body) {
        $request.ContentType = 'application/json; charset=utf-8'
        $request.Body = [Text.Encoding]::UTF8.GetBytes(($Body | ConvertTo-Json -Depth 50))
    }
    try {
        $response = Invoke-RestMethod @request
        return $response
    }
    catch {
        # Never echo response bodies, request bodies, tool credentials, or provider secrets.
        $status = if ($_.Exception.Response) { [int] $_.Exception.Response.StatusCode } else { 'unreachable' }
        throw "QwenPaw $Method /api/$Path failed ($status). Check the running service and authentication."
    }
}

function Assert-LocalPath {
    param([string] $Path)
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($runtimeRoot + [IO.Path]::DirectorySeparatorChar,
            [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Refusing a workspace path outside the discovered QwenPaw directory.'
    }
    $cursor = $full
    while ($cursor -and $cursor -ne $runtimeRoot) {
        if ((Test-Path -LiteralPath $cursor) -and
            ((Get-Item -LiteralPath $cursor).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'Refusing to modify a linked QwenPaw path.'
        }
        $cursor = Split-Path $cursor -Parent
    }
    return $full
}

function Backup-File {
    param([string] $Path)
    $full = Assert-LocalPath $Path
    if (-not (Test-Path -LiteralPath $full -PathType Leaf) -or $backedUp.Contains($full)) { return }
    if (-not $script:backupRoot) {
        $script:backupRoot = Join-Path $runtimeRoot ('backups/storywalk/' +
            (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
        $null = Assert-LocalPath $script:backupRoot
        Write-Host "Backup directory: $script:backupRoot"
    }
    $relative = [IO.Path]::GetRelativePath($runtimeRoot, $full)
    $target = Join-Path $script:backupRoot $relative
    $null = New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force
    Copy-Item -LiteralPath $full -Destination $target
    $null = $backedUp.Add($full)
}

function Test-SameFile {
    param([string] $Source, [string] $Destination)
    return ((Test-Path -LiteralPath $Destination -PathType Leaf) -and
        (Get-FileHash -LiteralPath $Source).Hash -eq (Get-FileHash -LiteralPath $Destination).Hash)
}

function Sync-File {
    param([string] $Source, [string] $Destination)
    $Destination = Assert-LocalPath $Destination
    if (Test-SameFile $Source $Destination) { return }
    Backup-File $Destination
    $null = New-Item -ItemType Directory -Path (Split-Path $Destination -Parent) -Force
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

function Remove-RedundantPrompt {
    param([string] $Directory)
    $path = Assert-LocalPath (Join-Path $Directory 'prompt.md')
    if (Test-Path -LiteralPath $path) {
        Backup-File $path
        Remove-Item -LiteralPath $path
    }
}

function Get-SkillDirectory {
    param([string] $Workspace)
    $preferred = Join-Path $Workspace 'skills'
    $legacy = Join-Path $Workspace 'skill'
    if (-not (Test-Path -LiteralPath $preferred) -and (Test-Path -LiteralPath $legacy)) { return $legacy }
    return $preferred
}

function Set-MarkedBlock {
    param([string] $Text, [string] $Name, [string[]] $Lines)
    $start = "<!-- ${Name}_START -->"
    $end = "<!-- ${Name}_END -->"
    $startCount = [regex]::Matches($Text, [regex]::Escape($start)).Count
    $endCount = [regex]::Matches($Text, [regex]::Escape($end)).Count
    if ($startCount -gt 1 -or $endCount -gt 1 -or $startCount -ne $endCount -or
        ($startCount -eq 1 -and $Text.IndexOf($end) -lt $Text.IndexOf($start))) {
        throw "Malformed $Name markers; repair them before configuring QwenPaw."
    }
    $block = (@($start) + $Lines + @($end)) -join "`n"
    if ($startCount -eq 0) { return $Text.TrimEnd() + "`n`n" + $block + "`n" }
    $first = $Text.IndexOf($start)
    $last = $Text.IndexOf($end) + $end.Length
    return $Text.Substring(0, $first) + $block + $Text.Substring($last)
}

function Test-VisionModel {
    param($Model)
    if (-not $Model) { return $false }
    $provider = @($providers | Where-Object id -eq $Model.provider_id)
    if ($provider.Count -ne 1) { return $false }
    $models = @($provider[0].models) + @($provider[0].extra_models)
    return @($models | Where-Object { $_.id -eq $Model.model -and $_.supports_multimodal -eq $true }).Count -gt 0
}

function Get-AgentTool {
    param([string] $AgentId, [string] $Name)
    $tools = @(Invoke-QwenPawApi 'tools' -AgentId $AgentId)
    $tool = @($tools | Where-Object name -eq $Name)
    if ($tool.Count -ne 1) { throw "Missing tool: $AgentId/$Name" }
    return $tool[0]
}

function Set-ToolEnabled {
    param([string] $AgentId, [string] $Name, [bool] $Enabled)
    $tool = Get-AgentTool $AgentId $Name
    if ($tool.enabled -ne $Enabled) {
        $null = Invoke-QwenPawApi "tools/$Name/toggle" -Method Patch -AgentId $AgentId
    }
}

$agentSpecs = @(
    @{ id = 'route'; name = '路线微调'; skills = @('route-adjust') },
    @{ id = 'intent'; name = '需求理解'; skills = @('requirement-understand', 'fairness-gate') },
    @{ id = 'pref-guide'; name = '偏好多轮引导'; skills = @('preference-guide') },
    @{ id = 'guide'; name = '文化讲解'; skills = @('macau-guide', 'source-attribution', 'anti-sycophancy') },
    @{ id = 'photo'; name = '拍照识别'; skills = @('photo-recognize', 'source-attribution') },
    @{ id = 'scene'; name = '明信片场景'; skills = @('gc-minimal-zine-poster') },
    @{ id = 'scene-photo'; name = '明信片照片编辑'; skills = @('qwen-image-postcard', 'photo-abstract-editorial') },
    @{ id = 'reviewer'; name = '独立审核'; skills = @('content-safety-review') }
)
$projectIds = @('default') + @($agentSpecs.id)
$ethicsSkills = @('fairness-gate', 'source-attribution', 'anti-sycophancy', 'content-safety-review')
$oldSceneSkills = @('postcard-scene', 'qwen-image-postcard', 'photo-abstract-editorial')
$sources = [ordered]@{}
foreach ($name in @('route-adjust', 'requirement-understand', 'preference-guide', 'macau-guide',
        'photo-recognize', 'gc-minimal-zine-poster', 'postcard-scene', 'qwen-image-postcard',
        'photo-abstract-editorial') + $ethicsSkills) {
    $parent = if ($name -in $ethicsSkills) { 'ethics/qwenpaw-skills' } else { 'skills' }
    $sources[$name] = Join-Path $repoRoot "$parent/$name/SKILL.md"
    if (-not (Test-Path -LiteralPath $sources[$name] -PathType Leaf)) { throw "Missing repository Skill: $name" }
}
$ethicsLines = [IO.File]::ReadAllLines((Join-Path $repoRoot 'ethics/prompts/_ethics_base.md'))
if ($ethicsLines.Count -lt 42) { throw 'Ethics baseline must contain lines 9-42.' }
$blocks = [ordered]@{
    MACAU_ETHICS_BASE = $ethicsLines[8..41]
    MACAU_GUIDE_TTS = @(
        'For a request beginning TTS_RENDER_REQUEST: call synthesize_speech_qwen exactly once with the supplied text and language.',
        'Do not rewrite, translate, summarize, expand, or disclose the approved narration; respond only after the tool completes.'
    )
    MACAU_SCENE_PRESET = @(
        'For a no-photo request that names gc-minimal-zine-poster, load that skill first and treat it as the highest-priority visual contract.',
        'Call generate_image_qwen exactly once; do not use postcard-scene SVG, photo-abstract-editorial, or a generic landmark fallback.',
        'If generation fails, report the tool failure instead of fabricating or returning a placeholder image.'
    )
    MACAU_SCENE_PHOTO = @(
        'Handle only authorized, privacy-scrubbed user photo edits.',
        'Use edit_image_qwen exactly once and never generate a no-photo scenic image.',
        'Preserve blurred faces and do not reconstruct identity details.'
    )
}
$extraBlocks = @{ guide = 'MACAU_GUIDE_TTS'; scene = 'MACAU_SCENE_PRESET'; 'scene-photo' = 'MACAU_SCENE_PHOTO' }
$descriptions = @{
    scene = '仅使用 gc-minimal-zine-poster 和 generate_image_qwen 生成无照片澳门场景图。'
    'scene-photo' = '仅处理已获授权并完成隐私清理的用户照片编辑，不生成无照片场景。'
}

Write-Host "Checking local QwenPaw at $BaseUrl (no model calls)."
$version = Invoke-QwenPawApi 'version'
$agents = @((Invoke-QwenPawApi 'agents').agents)
$defaultAgent = @($agents | Where-Object id -eq 'default')
if ($defaultAgent.Count -ne 1) { throw 'Run qwenpaw init first: the default Agent is missing.' }
$runtimeRoot = [IO.Path]::GetFullPath((Split-Path (Split-Path $defaultAgent[0].workspace_dir -Parent) -Parent))
if (-not (Test-Path -LiteralPath (Join-Path $runtimeRoot 'config.json'))) {
    throw 'Cannot discover the local QwenPaw root from the default workspace.'
}
$poolRoot = Assert-LocalPath (Join-Path $runtimeRoot 'skill_pool')
$activeModel = (Invoke-QwenPawApi 'models/active').active_llm
if (-not $activeModel.provider_id -or -not $activeModel.model) { throw 'Configure an active QwenPaw model first.' }
$providers = @(Invoke-QwenPawApi 'models')
$backedUp = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
$backupRoot = $null
$reloadIds = [Collections.Generic.HashSet[string]]::new()

# Complete path/marker/model preflight before touching any existing workspace.
$plannedModels = @{}
$visionCandidates = @($agents | Where-Object id -eq 'photo' | ForEach-Object active_model) + @($activeModel)
foreach ($id in $projectIds) {
    $agent = $agents | Where-Object id -eq $id
    if ($agent) {
        $file = Assert-LocalPath (Join-Path $agent.workspace_dir 'AGENTS.md')
        $text = [IO.File]::ReadAllText($file).Replace("`r`n", "`n")
        $updated = Set-MarkedBlock $text 'MACAU_ETHICS_BASE' $blocks.MACAU_ETHICS_BASE
        if ($extraBlocks.ContainsKey($id)) { $updated = Set-MarkedBlock $updated $extraBlocks[$id] $blocks[$extraBlocks[$id]] }
        # Calling Set-MarkedBlock validates every marker before any mutation.
    } elseif ($VerifyOnly) { throw "Missing Agent: $id" }
    if ($id -in @('photo', 'scene', 'scene-photo')) {
        $model = if ($agent -and $agent.active_model) { $agent.active_model } else { $activeModel }
        if (-not (Test-VisionModel $model)) {
            if ($VerifyOnly) { throw "Vision capability is not declared for $id's model." }
            $model = $visionCandidates | Where-Object { Test-VisionModel $_ } | Select-Object -First 1
            if (-not $model) { throw "Configure a vision-capable photo or active model before creating $id." }
            Write-Host "Vision model for ${id}: $($model.provider_id)/$($model.model)"
        }
        $plannedModels[$id] = $model
    }
}

if (-not $VerifyOnly) {
    Backup-File (Join-Path $runtimeRoot 'config.json')
    Backup-File (Join-Path $poolRoot 'skill.json')
    foreach ($agent in $agents | Where-Object id -in $projectIds) {
        foreach ($name in @('agent.json', 'skill.json', 'AGENTS.md')) { Backup-File (Join-Path $agent.workspace_dir $name) }
    }
    foreach ($name in $sources.Keys) {
        $directory = Join-Path $poolRoot $name
        Sync-File $sources[$name] (Join-Path $directory 'SKILL.md')
        if ($name -in $ethicsSkills) { Remove-RedundantPrompt $directory }
    }
    $null = Invoke-QwenPawApi 'skills/pool/refresh' -Method Post
    Write-Host "Imported $($sources.Count) repository Skills into the pool."
    foreach ($spec in $agentSpecs) {
        if ($spec.id -notin $agents.id) {
            $model = if ($plannedModels.ContainsKey($spec.id)) { $plannedModels[$spec.id] } else { $activeModel }
            $null = Invoke-QwenPawApi 'agents' -Method Post -Body @{
                id = $spec.id; name = $spec.name; language = 'zh'; active_model = $model; skill_names = $spec.skills
            }
            Write-Host "Created Agent: $($spec.id)"
        }
    }
    $agents = @((Invoke-QwenPawApi 'agents').agents)
    foreach ($spec in $agentSpecs) {
        $agent = $agents | Where-Object id -eq $spec.id
        $skillRoot = Assert-LocalPath (Get-SkillDirectory $agent.workspace_dir)
        $mounted = @(Invoke-QwenPawApi 'skills' -AgentId $spec.id)
        # Also refresh repository Skills previously mounted on this project Agent.
        $names = @(@($spec.skills) + @($mounted.name | Where-Object { $sources.Contains($_) }) | Select-Object -Unique)
        foreach ($name in $names) {
            $target = Assert-LocalPath (Join-Path $skillRoot "$name/SKILL.md")
            if (-not (Test-Path -LiteralPath $target)) {
                $null = Invoke-QwenPawApi 'skills/pool/download' -Method Post -Body @{
                    skill_name = $name; targets = @(@{ workspace_id = $spec.id }); overwrite = $false
                }
                $null = $reloadIds.Add($spec.id)
            } elseif (-not (Test-SameFile $sources[$name] $target)) {
                if ($UpdateExistingSkills) {
                    Sync-File $sources[$name] $target
                    $null = $reloadIds.Add($spec.id)
                    Write-Host "Updated Skill: $($spec.id)/$name"
                } else { Write-Warning "Preserved different Skill: $($spec.id)/$name; use -UpdateExistingSkills to refresh it with a backup." }
            }
            if ($name -in $ethicsSkills) { Remove-RedundantPrompt (Split-Path $target -Parent) }
        }
        $mounted = @(Invoke-QwenPawApi 'skills/refresh' -Method Post -AgentId $spec.id)
        foreach ($name in $spec.skills) {
            if (-not @($mounted | Where-Object { $_.name -eq $name -and $_.enabled }).Count) {
                $null = Invoke-QwenPawApi "skills/$name/enable" -Method Post -AgentId $spec.id
            }
        }
        if ($spec.id -eq 'scene') {
            foreach ($name in $oldSceneSkills) {
                if (@($mounted | Where-Object { $_.name -eq $name -and $_.enabled }).Count) {
                    $null = Invoke-QwenPawApi "skills/$name/disable" -Method Post -AgentId 'scene'
                }
            }
        }
    }
    foreach ($agent in $agents | Where-Object id -in $projectIds) {
        $id = $agent.id
        $file = Assert-LocalPath (Join-Path $agent.workspace_dir 'AGENTS.md')
        $original = [IO.File]::ReadAllText($file)
        $updated = Set-MarkedBlock $original.Replace("`r`n", "`n") 'MACAU_ETHICS_BASE' $blocks.MACAU_ETHICS_BASE
        if ($extraBlocks.ContainsKey($id)) { $updated = Set-MarkedBlock $updated $extraBlocks[$id] $blocks[$extraBlocks[$id]] }
        if ($original.Replace("`r`n", "`n") -cne $updated) {
            Backup-File $file
            [IO.File]::WriteAllText($file, $updated, [Text.UTF8Encoding]::new($false))
            $null = $reloadIds.Add($id)
        }
        $config = Invoke-QwenPawApi "agents/$id"
        if ($descriptions.ContainsKey($id) -and $config.description -cne $descriptions[$id]) {
            $config.description = $descriptions[$id]; $null = $reloadIds.Add($id)
        }
        if ($plannedModels.ContainsKey($id) -and ($config.active_model | ConvertTo-Json -Compress) -cne
            ($plannedModels[$id] | ConvertTo-Json -Compress)) {
            $config.active_model = $plannedModels[$id]; $null = $reloadIds.Add($id)
        }
        if ($reloadIds.Contains($id)) { $null = Invoke-QwenPawApi "agents/$id" -Method Put -Body $config }
    }

    foreach ($pluginName in @('qwen-image', 'qwen-tts')) {
        $source = Join-Path $repoRoot "backend/app/tools/$pluginName"
        $manifest = Get-Content -LiteralPath (Join-Path $source 'plugin.json') -Raw | ConvertFrom-Json
        $destination = Assert-LocalPath (Join-Path $runtimeRoot "plugins/$($manifest.id)")
        $pluginFiles = @(Get-ChildItem -LiteralPath $source -File | Where-Object Extension -in @('.py', '.json', '.txt', '.md'))
        $different = @($pluginFiles | Where-Object { -not (Test-SameFile $_.FullName (Join-Path $destination $_.Name)) })
        $loaded = @(Invoke-QwenPawApi 'plugins' | Where-Object { $_.id -eq $manifest.id -and $_.loaded })
        if ($different.Count -gt 0 -or $loaded.Count -eq 0) {
            if (Test-Path -LiteralPath $destination) {
                Get-ChildItem -LiteralPath $destination -File | ForEach-Object { Backup-File $_.FullName }
            }
            $null = Invoke-QwenPawApi 'plugins/install' -Method Post -Body @{ source = $source; force = $true }
            Write-Host "Installed and hot-loaded Plugin: $($manifest.id)"
        }
    }

    # Read only the allowlisted settings; never evaluate .env as shell code.
    $settings = @{}
    $settingNames = @('QWEN_IMAGE_API_KEY', 'QWEN_IMAGE_ENDPOINT', 'QWEN_IMAGE_MODEL', 'DASHSCOPE_API_KEY')
    $envFile = Join-Path $repoRoot '.env'
    if (Test-Path -LiteralPath $envFile) {
        foreach ($line in [IO.File]::ReadAllLines($envFile)) {
            if ($line -match '^\s*([A-Z][A-Z0-9_]*)\s*=(.*)$' -and $Matches[1] -in $settingNames) {
                $settings[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'")
            }
        }
    }
    foreach ($name in $settingNames) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ($value) { $settings[$name] = $value.Trim().Trim('"').Trim("'") }
    }
    $imageEndpoint = if ($settings.QWEN_IMAGE_ENDPOINT) { $settings.QWEN_IMAGE_ENDPOINT.TrimEnd('/') } else { 'https://dashscope.aliyuncs.com/api/v1' }
    $imageEndpoint = $imageEndpoint -replace '/compatible-mode/v1$', '/api/v1'
    $imageModel = if ($settings.QWEN_IMAGE_MODEL) { $settings.QWEN_IMAGE_MODEL } else { 'qwen-image-2.0-pro' }
    $toolSpecs = @(
        @{ agent = 'scene'; name = 'generate_image_qwen'; config = @{ api_key = $settings.QWEN_IMAGE_API_KEY; endpoint = $imageEndpoint; model = $imageModel; timeout = 180 } },
        @{ agent = 'scene-photo'; name = 'edit_image_qwen'; config = @{ api_key = $settings.QWEN_IMAGE_API_KEY; endpoint = $imageEndpoint; model = $imageModel; timeout = 180 } },
        @{ agent = 'guide'; name = 'synthesize_speech_qwen'; config = @{ api_key = $settings.DASHSCOPE_API_KEY; model = 'qwen3-tts-flash'; timeout = 60 } }
    )
    foreach ($spec in $toolSpecs) {
        if ($spec.config.api_key) {
            # Agent GET is local and unmasked; compare in memory, never print it.
            $config = Invoke-QwenPawApi "agents/$($spec.agent)"
            $existing = $config.tools.builtin_tools.($spec.name).config
            $changed = @($spec.config.Keys | Where-Object { "$($existing.$_)" -cne "$($spec.config[$_])" })
            if ($changed.Count -gt 0) {
                $null = Invoke-QwenPawApi "tools/$($spec.name)/config" -Method Post -AgentId $spec.agent -Body @{ config = $spec.config }
            }
            Set-ToolEnabled $spec.agent $spec.name $true
        } else {
            Set-ToolEnabled $spec.agent $spec.name $false
            Write-Warning "No key supplied for $($spec.agent)/$($spec.name); tool disabled, existing credentials preserved."
        }
    }
    Set-ToolEnabled 'scene' 'edit_image_qwen' $false
    Set-ToolEnabled 'scene-photo' 'generate_image_qwen' $false
    foreach ($id in @('photo', 'scene', 'scene-photo')) { Set-ToolEnabled $id 'view_image' $true }
    Remove-Variable settings, toolSpecs, config, existing -ErrorAction SilentlyContinue
}

# Local postconditions: no doctor, chat/completion, image, TTS, or provider probes.
$agents = @((Invoke-QwenPawApi 'agents').agents)
$drift = [Collections.Generic.List[string]]::new()
foreach ($name in $sources.Keys) {
    if (-not (Test-SameFile $sources[$name] (Join-Path $poolRoot "$name/SKILL.md"))) { throw "Pool Skill differs: $name" }
    if ($name -in $ethicsSkills -and (Test-Path -LiteralPath (Join-Path $poolRoot "$name/prompt.md"))) { throw "Redundant pool prompt: $name" }
}
foreach ($agent in $agents | Where-Object id -in $projectIds) {
    if (-not $agent.enabled) { throw "Project Agent is disabled: $($agent.id)" }
    $text = [IO.File]::ReadAllText((Join-Path $agent.workspace_dir 'AGENTS.md')).Replace("`r`n", "`n")
    foreach ($name in @('MACAU_ETHICS_BASE') + @($extraBlocks[$agent.id] | Where-Object { $_ })) {
        if ((Set-MarkedBlock $text $name $blocks[$name]) -cne $text) { throw "Missing or outdated $name on $($agent.id)" }
    }
}
foreach ($spec in $agentSpecs) {
    $agent = $agents | Where-Object id -eq $spec.id
    if (-not $agent) { throw "Missing Agent: $($spec.id)" }
    $mounted = @(Invoke-QwenPawApi 'skills' -AgentId $spec.id)
    foreach ($name in $spec.skills) {
        if (-not @($mounted | Where-Object { $_.name -eq $name -and $_.enabled }).Count) { throw "Skill not enabled: $($spec.id)/$name" }
    }
    foreach ($name in @($mounted.name | Where-Object { $sources.Contains($_) })) {
        $path = Join-Path (Get-SkillDirectory $agent.workspace_dir) "$name/SKILL.md"
        if (-not (Test-SameFile $sources[$name] $path)) { $drift.Add("$($spec.id)/$name") }
    }
    foreach ($name in $ethicsSkills) {
        if (Test-Path -LiteralPath (Join-Path (Get-SkillDirectory $agent.workspace_dir) "$name/prompt.md")) { throw "Redundant ethics prompt: $($spec.id)/$name" }
    }
    if ($spec.id -eq 'scene' -and @($mounted | Where-Object { $_.name -in $oldSceneSkills -and $_.enabled }).Count) { throw 'Legacy scene Skills are still enabled.' }
    Write-Host "Verified Agent/Skills: $($spec.id)"
}
foreach ($id in @('photo', 'scene', 'scene-photo')) {
    $agent = $agents | Where-Object id -eq $id
    $model = if ($agent.active_model) { $agent.active_model } else { $activeModel }
    if (-not (Test-VisionModel $model) -or -not (Get-AgentTool $id 'view_image').enabled) { throw "Vision configuration incomplete: $id" }
}
foreach ($pair in @(@('scene', 'edit_image_qwen'), @('scene-photo', 'generate_image_qwen'))) {
    if ((Get-AgentTool $pair[0] $pair[1]).enabled) { throw "Wrong image tool enabled: $($pair -join '/')" }
}
foreach ($pair in @(@('scene', 'generate_image_qwen'), @('scene-photo', 'edit_image_qwen'), @('guide', 'synthesize_speech_qwen'))) {
    $tool = Get-AgentTool $pair[0] $pair[1]
    $required = @('api_key', 'model', 'timeout')
    if ($pair[1] -ne 'synthesize_speech_qwen') { $required += 'endpoint' }
    if ($tool.enabled -and @($required | Where-Object { -not $tool.config_values.$_ }).Count) { throw "Tool configuration incomplete: $($pair -join '/')" }
    Write-Host "Verified tool: $($pair -join '/') (enabled=$($tool.enabled))"
}
$plugins = @(Invoke-QwenPawApi 'plugins')
foreach ($id in @('qwen-image-tool', 'qwen-tts-tool')) {
    if (-not @($plugins | Where-Object { $_.id -eq $id -and $_.loaded -and $_.enabled }).Count) { throw "Plugin not loaded: $id" }
    $source = Join-Path $repoRoot ('backend/app/tools/' + $id.Replace('-tool', ''))
    foreach ($file in Get-ChildItem -LiteralPath $source -File | Where-Object Extension -in @('.py', '.json', '.txt', '.md')) {
        if (-not (Test-SameFile $file.FullName (Join-Path $runtimeRoot "plugins/$id/$($file.Name)"))) {
            throw "Plugin file differs from repository: $id/$($file.Name)"
        }
    }
}
if ($drift.Count -gt 0) {
    if ($VerifyOnly -or $UpdateExistingSkills) { throw "Workspace Skills differ from the repository: $($drift -join ', ')" }
    Write-Warning "$($drift.Count) workspace copies were preserved; configuration exists but Skills are not fully synchronized."
}
Write-Host "QwenPaw $($version.version): verified 9 project Agents, 13 pool Skills and local tool configuration. No online model tests were run."
