for u in justmates/ep5/master.m3u8 justmates/ep5/v0/index.m3u8 justmates/ep5/v0/s000.ts; do
  for k in 1 2 3; do curl -s -o /dev/null -D - -w "time %{time_total}s\n" -H "Origin: https://pinkmoonhouse.com" https://media.pinkmoonhouse.com/$u | grep -i "^http/\|cf-cache-status\|^time\|cache-control"; done; echo "--"; done
echo checked
