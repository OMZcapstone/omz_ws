# API 통신 기본 함수
function Post-Json($url, $obj) {
    $json = $obj | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    try {
        Invoke-RestMethod -Uri $url -Method POST -ContentType "application/json; charset=utf-8" -Body $bytes
    }
    catch {
        Write-Host "오류 발생: $_" -ForegroundColor Red
    }
}

# 1. 입차 등록 함수
function Add-Plate($plate, $color="white", $type="sedan") {
    $url = "http://127.0.0.1:8000/entry"
    $body = @{ plate=$plate; color=$color; vehicle_type=$type }
    $res = Post-Json $url $body
    if ($res) { Write-Host "입차: $($res.plate)" -ForegroundColor Green }
}

# 2. 번호판 검증 함수
function Verify-Plate($ocr) {
    $url = "http://127.0.0.1:8000/verify"
    $body = @{ ocr_text=$ocr }
    $res = Post-Json $url $body
    if ($res) { 
        Write-Host "검증: $ocr -> Best: $($res.best_plate) (점수: $($res.score))" -ForegroundColor Cyan 
    }
}

# 3. 출차 처리 함수
function Exit-Plate($plate) {
    $url = "http://127.0.0.1:8000/exit/$plate"
    try {
        $res = Invoke-RestMethod -Uri $url -Method POST
        Write-Host "출차: $($res.plate) (상태: $($res.status))" -ForegroundColor Yellow
    }
    catch {
        Write-Host "출차 실패: $_" -ForegroundColor Red
    }
}

Write-Host "✅ 주차 관제 함수가 로드되었습니다!" -ForegroundColor Magenta
Write-Host "사용법: Add-Plate '번호', Verify-Plate '번호', Exit-Plate '번호'"