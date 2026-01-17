#!/bin/bash

# Rapor Üretici - Çift Tıkla Çalıştır
# =====================================

# Klasöre git
cd "$(dirname "$0")"

# API Anahtarı - Kendi anahtarınızı buraya girin veya .env dosyasında tanımlayın
# export ANTHROPIC_API_KEY='your-api-key-here'

# Terminal başlığı
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              RAPOR ÜRETİCİ v3.0 PRO                          ║"
echo "║         Claude Opus 4.5 Destekli Uzman Sistem                ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  ✓ Uzman Seviye Araştırma (Claude Opus 4.5)                  ║"
echo "║  ✓ RAG Sistemi (Döküman İndeksleme)                          ║"
echo "║  ✓ Finansal Doğrulama & Mantık Kontrolü                      ║"
echo "║  ✓ Self-Reflection İçerik İyileştirme                        ║"
echo "║  ✓ Otomatik Grafik Üretimi                                   ║"
echo "║  ✓ Türkiye Veri Kaynakları (TÜİK, TCMB)                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo "HATA: Python3 yüklü değil!"
    echo "Lütfen Python3 yükleyin: https://www.python.org/downloads/"
    read -p "Çıkmak için Enter'a basın..."
    exit 1
fi

# Programı çalıştır
python3 main.py

# Bitince bekle
echo ""
echo "════════════════════════════════════════════════════════════════"
read -p "Çıkmak için Enter'a basın..."
