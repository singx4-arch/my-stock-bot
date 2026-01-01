name: Market Divergence 알람

on:
  schedule:
    - cron: '*/5 * * * *'  # 5분마다 실행이다
  workflow_dispatch:      # 수동 실행 버튼이다

permissions:
  contents: write         # 파일 저장 권한이다

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'  # 3.9에서 3.10으로 올렸다이다

      - name: Install dependencies
        run: |
          pip install yfinance pandas requests numpy

      - name: Run Divergence Bot
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python diver.py  # 파일명이 diver.py인 것을 확인했다이다

      - name: Commit and Push changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add last_alerts.json
          git commit -m "Update last alerts state [skip ci]" || exit 0
          git push
