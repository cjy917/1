<#
.SYNOPSIS
一键安装电影系统的所有依赖（后端 Python + 前端 Vue）
#>

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "电影系统依赖安装脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 安装后端 Python 依赖
Write-Host "`n[1/2] 安装后端 Python 依赖..." -ForegroundColor Yellow
try {
    pip install -r backend/requirements.txt
    Write-Host "✅ 后端依赖安装成功" -ForegroundColor Green
} catch {
    Write-Host "❌ 后端依赖安装失败: $_" -ForegroundColor Red
    exit 1
}

# 2. 安装前端 Vue 依赖
Write-Host "`n[2/2] 安装前端 Vue 依赖..." -ForegroundColor Yellow
try {
    Set-Location frontend
    npm install --legacy-peer-deps
    Set-Location ..
    Write-Host "✅ 前端依赖安装成功" -ForegroundColor Green
} catch {
    Write-Host "❌ 前端依赖安装失败: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "所有依赖安装完成！" -ForegroundColor Green
Write-Host "`n启动服务：" -ForegroundColor Yellow
Write-Host "  后端: cd backend && python app.py" -ForegroundColor White
Write-Host "  前端: cd frontend && npm run dev" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
