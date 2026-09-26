# Static Windows speech adapter. User text arrives as JSON data, never as code.
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$speaker = $null
$recognizer = $null
$stream = $null
try {
    $request = [Console]::In.ReadToEnd() | ConvertFrom-Json
    switch ($request.action) {
        'inventory' {
            $voiceItems = @()
            $recognizerItems = @()
            $warnings = @()
            try {
                $speaker = New-Object -ComObject SAPI.SpVoice
                $tokens = $speaker.GetVoices()
                for ($i = 0; $i -lt $tokens.Count; $i++) {
                    $token = $tokens.Item($i)
                    $culture = [Globalization.CultureInfo]::GetCultureInfo([Convert]::ToInt32(($token.GetAttribute('Language') -split ';')[0], 16)).Name
                    $voiceItems += @{id=$token.Id; name=$token.GetDescription(); culture=$culture; gender=$token.GetAttribute('Gender')}
                }
            } catch { $warnings += 'Voices unavailable. Check Windows speech components.' }
            try {
                Add-Type -AssemblyName System.Speech
                foreach ($item in [System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers()) {
                    $recognizerItems += @{id=$item.Id; name=$item.Name; culture=$item.Culture.Name}
                }
            } catch { $warnings += 'Recognition unavailable. Install a compatible Windows speech language.' }
            $response = @{ok=$true; voices=$voiceItems; recognizers=$recognizerItems; warnings=$warnings}
        }
        { $_ -in 'speak', 'render' } {
            $speaker = New-Object -ComObject SAPI.SpVoice
            $tokens = $speaker.GetVoices()
            $found = $false
            for ($i = 0; $i -lt $tokens.Count; $i++) {
                if ($tokens.Item($i).Id -eq $request.voice) { $speaker.Voice = $tokens.Item($i); $found = $true; break }
            }
            if (-not $found) { throw 'The selected voice is unavailable. Refresh voices.' }
            $speaker.Rate = [Math]::Max(-4, [Math]::Min(4, [int]$request.rate))
            $speaker.Volume = [Math]::Max(0, [Math]::Min(100, [int]$request.volume))
            if ($request.action -eq 'render') {
                $stream = New-Object -ComObject SAPI.SpFileStream
                $stream.Open([string]$request.path, 3, $false)
                $speaker.AudioOutputStream = $stream
            }
            # SPF_IS_NOT_XML (16): angle brackets and SSML are always literal text.
            $null = $speaker.Speak([string]$request.text, 16)
            $response = @{ok=$true}
        }
        { $_ -in 'listen', 'wake' } {
            Add-Type -AssemblyName System.Speech
            $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine([string]$request.recognizer)
            if ($request.action -eq 'wake') {
                $builder = New-Object System.Speech.Recognition.GrammarBuilder
                $builder.Culture = $recognizer.RecognizerInfo.Culture
                $builder.Append('Hey Jarvis')
                $grammar = New-Object System.Speech.Recognition.Grammar($builder)
                $recognizer.LoadGrammar($grammar)
            } else {
                $recognizer.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
            }
            $recognizer.InitialSilenceTimeout = [TimeSpan]::FromSeconds(7)
            $recognizer.BabbleTimeout = [TimeSpan]::FromSeconds(8)
            $recognizer.EndSilenceTimeout = [TimeSpan]::FromMilliseconds(750)
            $recognizer.SetInputToDefaultAudioDevice()
            $result = $recognizer.Recognize([TimeSpan]::FromSeconds(7))
            if ($null -eq $result) { $response = @{ok=$true; text=''; confidence=0} }
            else { $response = @{ok=$true; text=$result.Text; confidence=$result.Confidence} }
        }
        default { throw 'Unknown speech action.' }
    }
    $response | ConvertTo-Json -Depth 5 -Compress
} catch {
    @{ok=$false; error=$_.Exception.Message} | ConvertTo-Json -Compress
} finally {
    if ($null -ne $recognizer) { $recognizer.Dispose() }
    if ($null -ne $stream) { $stream.Close() }
    if ($null -ne $speaker) { $null = [Runtime.InteropServices.Marshal]::ReleaseComObject($speaker) }
}
