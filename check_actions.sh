#!/bin/bash
# GitHub Actions ログ確認スクリプト
# 使い方: GITHUB_TOKEN=ghp_xxx bash check_actions.sh

TOKEN=${GITHUB_TOKEN:-""}
OWNER="kou573"
REPO="lumen-images"

if [ -z "$TOKEN" ]; then
    echo "[ERROR] GITHUB_TOKEN が未設定です"
    echo "使い方: GITHUB_TOKEN=ghp_xxx bash check_actions.sh"
    exit 1
fi

echo "=== 最新のワークフロー実行を確認 ==="
RUN=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "https://api.github.com/repos/$OWNER/$REPO/actions/runs?per_page=1" | \
    python3 -c "import json,sys; r=json.load(sys.stdin)['workflow_runs'][0]; print(r['id'], r['status'], r['conclusion'])")

RUN_ID=$(echo $RUN | cut -d' ' -f1)
STATUS=$(echo $RUN | cut -d' ' -f2)
RESULT=$(echo $RUN | cut -d' ' -f3)
echo "Run ID: $RUN_ID / Status: $STATUS / Result: $RESULT"

echo ""
echo "=== ステップ詳細 ==="
curl -s -H "Authorization: Bearer $TOKEN" \
    "https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/jobs" | \
    python3 -c "
import json, sys
data = json.load(sys.stdin)
for job in data.get('jobs', []):
    for step in job.get('steps', []):
        icon = '✅' if step['conclusion'] == 'success' else '❌' if step['conclusion'] == 'failure' else '⏭'
        print(f'{icon} {step[\"name\"]}')
"

echo ""
echo "=== エラーログ取得 ==="
curl -s -H "Authorization: Bearer $TOKEN" \
    "https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID/logs" -L -o /tmp/actions_logs.zip 2>/dev/null && \
    unzip -p /tmp/actions_logs.zip "*/post/*.txt" 2>/dev/null | tail -50 || \
    echo "ログの取得に失敗しました（手動でGitHub画面から確認してください）"
